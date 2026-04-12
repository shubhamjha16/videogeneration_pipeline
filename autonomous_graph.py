"""
Autonomous LangGraph Pipeline — Team Tony
Orchestrates the full video generation flow:

  SHARED
    director_node   : parse Tony AI HTML → Claude director → scenes + render_mode
    vision_node     : Gemini Imagen → concept diagram PNG

  MANIM PATH (unchanged)
    architect_node  : template_renderer → deterministic Manim script
    supervisor_node : render Manim → stitch audio → S3 upload
    healer_node     : Claude fixes broken Manim scripts (max 3 retries)

  PRESENTATION PATH (existing)
    ppt_planner_node  : Groq → splits text into slides (layout + data + narration)
    ppt_renderer_node : slide_generator → 1920x1080 PNG per slide
    ppt_tts_node      : tts_generator → MP3 per slide
    ppt_video_node    : ffmpeg → clip per slide → final MP4 (+ optional avatar)
    ppt_upload_node   : S3 upload

  EXPLAINER PATH (new)
    explainer_node    : explainer_generator → Stitches narration with B-roll metaphors (Higgsfield style)

  USER GENERATED PATH (new)
    heygen_node       : heygen_generator → High-fidelity talking head
    subtitle_node     : subtitle_generator → Insta Reels style kinetic subtitles
    fusion_node       : Final assembly (HeyGen + Subtitles)
"""

import os
import sys
import glob
import subprocess
import importlib
from typing import TypedDict, List, Optional, Any

from langgraph.graph import StateGraph, END
import config
from healer_agent import run_healer


# ── Industrial Helpers ───────────────────────────────────────────────────────

def _ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


_api_bridge_refs = None

def _log_progress(state: "TonyState", node_name: str, msg: str, log_type: str = "info"):
    """Industrial Sentinel: Universal progress logger with circular memory capping."""
    job_id = state.get("job_id")
    if not job_id: return
    
    global _api_bridge_refs
    if _api_bridge_refs is None:
        try:
            import api_bridge
            _api_bridge_refs = api_bridge
        except ImportError: pass
        
    if _api_bridge_refs:
        with _api_bridge_refs._jobs_lock:
            if job_id in _api_bridge_refs.jobs:
                logs = _api_bridge_refs.jobs[job_id]["logs"]
                logs.append({"node": node_name, "msg": msg, "type": log_type})
                if len(logs) > 50:
                    _api_bridge_refs.jobs[job_id]["logs"] = logs[-50:]
                print(f"📡 Telemetry [{node_name}]: {msg}")
        _api_bridge_refs._save_jobs()

def get_job_dir(state: "TonyState") -> str:
    """Isolated sandbox for the current job."""
    job_id = state.get("job_id", "fallback")
    path = os.path.join("output", f"job_{job_id}")
    os.makedirs(path, exist_ok=True)
    return path

def get_topic_safe(state: "TonyState") -> str:
    """Returns a filename-friendly topic string truncated to 100 characters."""
    topic = state.get("topic", "video")
    safe = topic.lower().replace(" ", "_").replace("/", "_")
    return safe[:100]

def _manim() -> str:
    """Resolve manim binary — works in venv, Docker, and system installs."""
    import shutil
    system_manim = shutil.which("manim")
    if system_manim: return system_manim
    raise RuntimeError("manim binary not found")


# ── State ─────────────────────────────────────────────────────────────────────

class TonyState(TypedDict):
    # ── Input ──────────────────────────────────────────
    job_id:      Optional[str]
    topic:       str
    raw_input:   str

    # ── After director_node ────────────────────────────
    parsed_facts:  Optional[dict]
    render_mode:   Optional[str]
    scenes:        Optional[list]

    # ── After vision_node ──────────────────────────────
    image_path:  Optional[str]
    image_paths: Optional[dict[str, str]] # Map of scene_id or asset_id to local path

    # ── After architect_node ───────────────────────────
    manim_script_path: Optional[str]
    audio_files:       Optional[list]   # per-scene mp3 paths (generated before Manim)

    # ── After supervisor_node ─────────────────────────
    output_path:  Optional[str]
    video_url:    Optional[str]

    # ── PPT-specific (presentation path) ──────────────
    slides:           Optional[list]   # [{layout, data, narration}] from Groq
    slide_paths:      Optional[list]   # PNG paths per slide
    clip_paths:       Optional[list]   # clip MP4 paths per slide
    critic_feedback:  Optional[str]    # feedback from ppt_critic → fed back to planner
    ppt_attempt_count: int             # how many times planner has been retried by critic

    # ── Explainer/HeyGen-specific ─────────────────────
    visual_prompts:   Optional[list]   # B-roll prompts for Explainer mode
    heygen_video_path: Optional[str]   # Path to downloaded HeyGen video
    subtitle_style:   Optional[str]    # "insta_reels" | "classic"

    # ── Control ────────────────────────────────────────
    rendering_errors: Optional[str]
    attempt_count:    int
    with_avatar:      Optional[bool]   # presentation only — show avatar on slides
    video_type:       Optional[str]    # "marketing" | "educational" | None (default: educational)
    no_vision:        bool


# ── Node 1: Director ──────────────────────────────────────────────────────────

def director_node(state: TonyState) -> TonyState:
    """Parse Tony AI HTML and run Claude director to produce scenes."""
    _log_progress(state, "DIRECTOR", f"Analyzing curriculum and selecting render path for: {state['topic']}...")
    print(f"🎬 [Director] Parsing HTML and writing scene script for: {state['topic']}")

    from html_parser import parse_tony_html
    from director_agent import run_director

    parsed = parse_tony_html(state["raw_input"], topic_hint=state["topic"])
    state["parsed_facts"] = parsed

    print(f"   Subject: {parsed['subject']} | Type: {parsed['content_type']}")

    director_output = run_director(parsed)
    # Respect user-specified render_mode — only use Claude's decision as fallback
    state["render_mode"] = state.get("render_mode") or director_output.render_mode
    scenes = [s.model_dump() for s in director_output.scenes]

    # ── MCQ correction: override LLM answer with ground truth from HTML ───────
    # LLMs hallucinate wrong answers — parsed_facts has the real correct answer
    if parsed.get("content_type") == "mcq" and parsed.get("correct_answer"):
        correct_letter = parsed["correct_answer"]
        correct_name   = parsed.get("correct_answer_name", "")
        for scene in scenes:
            if scene["visual_type"] == "answer_reveal":
                scene["visual_data"]["letter"] = correct_letter
                scene["visual_data"]["name"]   = correct_name
            elif scene["visual_type"] == "cross_out":
                # only cross out if it's actually wrong
                if scene["visual_data"].get("letter") == correct_letter:
                    scene["visual_data"]["letter"] = ""  # skip crossing correct answer
        print(f"   Correct answer locked: {correct_letter}. {correct_name}")

    state["scenes"] = scenes
    print(f"   Render mode: {state['render_mode'].upper()} | Scenes: {len(scenes)}")
    print(f"   💡 Reasoning: {director_output.decision_reasoning}")
    return state


def vision_node(state: TonyState) -> TonyState:
    """Generate concept diagrams and multimodal metaphors using Gemini Imagen 3."""
    _log_progress(state, "VISION", "AI Vision Engine: Initializing high-fidelity asset generation...")
    print(f"🎨 [Vision] Generating assets for: {state['topic']}")

    if state.get("no_vision"):
        print("   Skipping image generation (user-requested)")
        state["image_path"] = None
        state["image_paths"] = {}
        return state

    from image_generator import generate_concept_image

    job_prefix = f"job_{state.get('job_id', state['topic'].lower().replace(' ', '_'))}"
    output_dir = os.path.join("output", job_prefix)
    os.makedirs(output_dir, exist_ok=True)

    subject = state.get("parsed_facts", {}).get("subject", "default")

    # ── PATH 1: Manim (Single Diagram) ────────────────
    if state.get("render_mode") == "manim":
        pre_path = os.path.join(output_dir, "tony_diagram.png")
        if os.path.exists(pre_path):
            state["image_path"] = pre_path
        else:
            try:
                state["image_path"] = generate_concept_image(state["topic"], subject, output_dir=output_dir, filename="tony_diagram.png")
            except Exception:
                state["image_path"] = None

    # ── PATH 2: Explainer (Multi-Asset) ───────────────
    elif state.get("render_mode") == "explainer":
        image_paths = {}
        scenes = state["scenes"] or []
        
        for i, scene in enumerate(scenes):
            v_type = scene["visual_type"]
            v_data = scene["visual_data"]
            
            if v_type == "counting_metaphor":
                item = v_data.get("item_name", "item")
                asset_id = f"counting_{i}_{item}"
                print(f"   Generating counting item: {item}...")
                try:
                    path = generate_concept_image(item, subject="counting_item", output_dir=output_dir, filename=f"{asset_id}.png")
                    image_paths[asset_id] = path
                except Exception as e:
                    print(f"   ⚠️  Counting asset failed: {e}")
                
                # BACKGROUND for counting scene
                bg_prompt = v_data.get("background_prompt")
                if bg_prompt:
                    bg_id = f"counting_bg_{i}"
                    print(f"   Generating thematic background for counting scene {i}: {bg_prompt}...")
                    try:
                        bg_path = generate_concept_image(bg_prompt, subject="explainer_background", output_dir=output_dir, filename=f"{bg_id}.png")
                        image_paths[bg_id] = bg_path
                    except Exception as e:
                        print(f"   ⚠️  Counting background failed: {e}")

            elif v_type == "b_roll_clip" or v_type == "generative_video":
                prompt = v_data.get("prompt", "Educational visual")
                asset_id = f"metaphor_{i}"
                print(f"   Generating cinematic metaphor for scene {i}...")
                try:
                    path = generate_concept_image(prompt, subject="explainer_metaphor", output_dir=output_dir, filename=f"{asset_id}.png")
                    image_paths[asset_id] = path
                except Exception as e:
                    print(f"   ⚠️  Metaphor asset failed: {e}")

        state["image_paths"] = image_paths

    return state


# ── Node 3: Architect ─────────────────────────────────────────────────────────

def architect_node(state: TonyState) -> TonyState:
    """Convert scenes into a Manim script (deterministic templates). Manim path only."""
    _log_progress(state, "ARCHITECT", "Orchestration: Building mathematical animation blueprint...")
    print(f"📐 [Architect] Building Manim script for: {state['topic']}")

    job_prefix = f"job_{state.get('job_id', state['topic'].lower().replace(' ', '_'))}"
    job_dir = os.path.join("output", job_prefix)
    os.makedirs(job_dir, exist_ok=True)

    # manim mode — generate TTS first to get real durations, then build Manim script
    from tts_generator import generate_audio
    from moviepy.editor import AudioFileClip
    from template_renderer import build_manim_script

    scenes = state["scenes"]

    # 1. Generate TTS per scene and measure actual duration
    print("   Generating TTS audio for sync...")
    audio_files = []
    for i, scene in enumerate(scenes):
        path = generate_audio(scene["narration_text"], i, output_dir=job_dir)
        audio_files.append(path)

    # 2. Inject real duration into each scene's visual_data
    for i, (scene, audio_path) in enumerate(zip(scenes, audio_files)):
        try:
            clip = AudioFileClip(audio_path)
            try:
                scene["visual_data"]["duration"] = round(clip.duration, 2)
            finally:
                clip.close()
        except Exception:
            scene["visual_data"]["duration"] = 3.0  # safe fallback

    state["audio_files"] = audio_files
    state["scenes"]      = scenes

    # 3. Build Manim script with synced durations
    script_path = os.path.join(job_dir, "scene_script.py")
    build_manim_script(
        scenes=scenes,
        image_path=state.get("image_path"),
        topic=state["topic"],
        output_path=script_path,
    )
    state["manim_script_path"] = script_path
    print(f"   Script written with synced durations: {script_path}")
    return state


# ── Node 4: Supervisor ────────────────────────────────────────────────────────

def supervisor_node(state: TonyState) -> TonyState:
    """Render Manim → stitch audio → S3 upload. Manim path only."""
    _log_progress(state, "SUPERVISOR", "Production: Rendering Manim mathematics animation...")
    print(f"🔍 [Supervisor] Rendering — attempt {state['attempt_count'] + 1}")

    job_dir     = os.path.dirname(state["manim_script_path"])
    script_path = state["manim_script_path"]
    topic_safe  = state["topic"].replace(" ", "").replace("-", "")

    # ── 1. Render Manim (Industrial Hardening: Sandbox-Local Cache) ──
    print("   Rendering Manim animation with cache isolation...")
    render_result = subprocess.run(
        [_manim(), "-ql", script_path, "EaseToLearnScene", 
         "--media_dir", os.path.join(job_dir, "manim_media")],
        capture_output=True, text=True
    )

    if render_result.returncode != 0:
        print(f"   ❌ Manim render failed.")
        state["rendering_errors"] = render_result.stderr[-2000:]
        return state

    # Find rendered video
    renders = glob.glob(f"{job_dir}/**/EaseToLearnScene.mp4", recursive=True)
    if not renders:
        state["rendering_errors"] = "Manim output file not found after render"
        return state

    manim_video = renders[0]
    print(f"   ✅ Manim video: {manim_video}")

    # ── 2. Concatenate pre-generated TTS audio ────────
    print("   Concatenating narration audio...")
    from moviepy.editor import AudioFileClip, concatenate_audioclips

    audio_files = state["audio_files"]
    combined_audio_path = os.path.join(job_dir, "narration_combined.mp3")
    clips = [AudioFileClip(f) for f in audio_files]
    combined = concatenate_audioclips(clips)
    try:
        combined.write_audiofile(combined_audio_path, logger=None)
    finally:
        combined.close()
        for c in clips:
            c.close()

    # ── 3. Stitch video + audio via ffmpeg ────────────
    print("   Stitching video + audio...")
    final_output = os.path.join(job_dir, f"{topic_safe}_masterclass.mp4")

    stitch_result = subprocess.run([
        _ffmpeg(), "-y",
        "-i", manim_video,
        "-i", combined_audio_path,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-map", "0:v:0", "-map", "1:a:0",
        "-movflags", "+faststart",
        "-shortest",
        final_output,
    ], capture_output=True, text=True)

    if stitch_result.returncode != 0:
        state["rendering_errors"] = stitch_result.stderr
        return state

    print(f"   ✅ Final video: {final_output}")
    state["output_path"]       = os.path.abspath(final_output)
    state["rendering_errors"]  = None

    # ── 4. Upload to S3 ───────────────────────────────
    state["video_url"] = _upload_to_s3(final_output, state["topic"], state.get("job_id"))

    return state


def healer_node(state: TonyState) -> TonyState:
    """Ask Healer Agent to fix scripts based on errors."""
    print(f"🩹 [Healer] Fixing render errors — attempt {state['attempt_count'] + 1}")

    with open(state["manim_script_path"], "r") as f:
        script_content = f.read()

    fixed_script = run_healer(script_content, state["rendering_errors"])

    with open(state["manim_script_path"], "w") as f:
        f.write(fixed_script)

    state["attempt_count"] += 1
    state["rendering_errors"] = None  # Reset error state for the fresh attempt
    return state


# ── S3 Upload ─────────────────────────────────────────────────────────────────

def _upload_to_s3(local_path: str, topic: str, job_id: Optional[str] = None) -> str:
    """
    Upload finished video to S3 and return public URL.
    Reads AWS config from environment variables set by ECS task definition.
    """
    bucket   = os.environ.get("S3_BUCKET")
    region   = os.environ.get("AWS_REGION", "ap-south-1")

    if not bucket:
        # Local dev: just return local path
        print("   ℹ️  S3_BUCKET not set — skipping upload, returning local path")
        return f"file://{local_path}"

    import boto3
    # Inclusion of job_id in S3 key prevents URL collision for identical topics
    unique_prefix = job_id or os.environ.get("JOB_ID_FALLBACK", "factory")
    s3_key = f"videos/{unique_prefix}_{topic.lower().replace(' ', '_')}/{os.path.basename(local_path)}"

    print(f"   ☁️  Uploading to s3://{bucket}/{s3_key} ...")
    s3 = boto3.client("s3", region_name=region)
    s3.upload_file(
        local_path,
        bucket,
        s3_key,
        ExtraArgs={"ContentType": "video/mp4"},
    )

    url = f"https://{bucket}.s3.{region}.amazonaws.com/{s3_key}"
    print(f"   ✅ S3 URL: {url}")
    return url


# ── PPT Nodes (presentation path) ─────────────────────────────────────────────

_PPT_PLANNER_PROMPT = """You are a creative presentation director for an educational video platform.

STEP 1 — Deeply understand the content before anything else:
- What is the SINGLE most dramatic or surprising fact in this content?
- What is the emotional arc? (shock → understanding → clarity? mystery → reveal? problem → solution?)
- What makes THIS topic unique — what would ONLY appear in a video about this specific topic?
- Who is the student? What do they already know? What will surprise them?

STEP 2 — Design a presentation that could ONLY be about this topic:
- Every slide must be uniquely tied to this specific content
- No generic slides that could apply to any topic
- The narration must sound like a teacher who genuinely finds this fascinating
- Use contrast, surprise, and specific numbers/names/dates — not vague generalities

STEP 3 — Layout rules:
- 6 to 9 slides total
- MANDATORY: Start each major chapter with chaos_chapter (use 2-3 times with incrementing numbers)
- NO layout should appear more than 3 times
- chaos_chapter subtitles must be specific to the content — never generic like "Introduction"
- big_statement must quote a specific dramatic fact, not a vague claim
- bullets must list SPECIFIC items (names, dates, numbers) — not vague categories
- key_highlight must show ONE specific number/date/name that defines this topic
- Narration must be 1-3 sentences, conversational, adds insight beyond the slide text

{feedback_section}

AVAILABLE LAYOUTS:
"chaos_chapter" — data: {{"number": "1", "title": str, "subtitle": str}}
"title_card"    — data: {{"title": str, "subtitle": str}}
"bullets"       — data: {{"heading": str, "bullets": [str]}}
"big_statement" — data: {{"statement": str, "context": str}}
"steps"         — data: {{"heading": str, "steps": [str]}}
"two_column"    — data: {{"heading": str, "left_title": str, "left_points": [str], "right_title": str, "right_points": [str]}}
"key_highlight" — data: {{"label": str, "fact": str, "detail": str}}
"summary"       — data: {{"heading": "Key Takeaways", "points": [str]}}
"timeline"      — data: {{"heading": str, "events": [{{"date": str, "description": str}}]}}
"quote_card"    — data: {{"quote": str, "attribution": str}}
"stats_dashboard" — data: {{"heading": str, "stats": [{{"value": str, "label": str}}]}}
"definition_card" — data: {{"term": str, "definition": str, "example": str}}
"before_after"  — data: {{"heading": str, "before_title": str, "before_points": [str], "after_title": str, "after_points": [str]}}
"callout_box"   — data: {{"type": "tip"|"warning"|"note"|"important", "heading": str, "body": str}}
"ranking_list"  — data: {{"heading": str, "items": [{{"label": str, "detail": str}}]}}
"image_hero"    — data: {{"title": str, "tagline": str, "context": str}}

CRITICAL JSON RULES — Groq must follow these exactly:
- Arrays use square brackets with double-quoted strings: ["item one", "item two"]
- Objects use curly braces: {{"key": "value"}}
- NO Python list syntax. NO trailing commas. NO single quotes.
- All string values must be on a single line (no embedded newlines inside strings)

Return valid JSON only:
{{"slides": [{{"layout": "...", "data": {{...}}, "narration": "..."}}]}}"""


# ── Shared variety rules (injected into ALL critic modes) ─────────────────────
_VARIETY_RULES = """
VISUAL VARIETY — MANDATORY REJECTION RULES:
V1. Same layout used for more than 30%% of slides → REJECT (e.g. 3+ bullets out of 8 slides)
V2. Three identical layouts in a row → REJECT (e.g. bullets→bullets→bullets)
V3. No "key_highlight" or "big_statement" used at all → REJECT (every video needs at least one dramatic moment)
V4. All chaos_chapter subtitles follow the same sentence pattern → REJECT (vary the phrasing)
V5. Any slide could appear in a video about a DIFFERENT topic without changing → REJECT
"""

_PPT_CRITIC_EDUCATIONAL = """You are a ruthless quality critic for EDUCATIONAL presentation videos.
You are judging whether a student will LEARN from this presentation.

Review this slide plan and decide: APPROVE or REJECT.

EDUCATIONAL QUALITY RULES:
E1. Any narration starts with generic phrases like "let's explore", "in this slide", "today we", "welcome to" → REJECT
E2. Any chaos_chapter subtitle is generic (e.g. "Introduction", "Overview", "Getting Started") → REJECT
E3. Any bullet point is vague (no specific names, numbers, or dates) → REJECT
E4. A complex term is introduced without being defined or explained → REJECT
E5. The narration just restates the bullet points instead of adding insight → REJECT
E6. The big_statement contains no specific fact (no number, name, or date) → REJECT
E7. The key_highlight fact is vague or not memorable → REJECT

{variety_rules}

BE SPECIFIC in your feedback — name which slide number has which problem.

Return JSON only:
{{"approved": true/false, "feedback": "specific issues or empty string if approved", "score": 1-10}}"""

_PPT_CRITIC_MARKETING = """You are a ruthless quality critic for MARKETING presentation videos.
You are judging whether a VIEWER will be hooked, excited, and convinced to take action.

Review this slide plan and decide: APPROVE or REJECT.

MARKETING IMPACT RULES:
M1. The first slide does not have a dramatic hook or bold claim → REJECT
M2. Any narration sounds like a textbook instead of a pitch → REJECT
M3. No slide creates urgency or emotional response → REJECT
M4. Any chaos_chapter subtitle is generic (e.g. "Introduction", "Overview") → REJECT
M5. The narration uses passive voice or weak verbs → REJECT (use "Transforms", "Unlocks", "Eliminates")
M6. No clear call-to-action or memorable takeaway in the final slides → REJECT
M7. More than 2 bullet-heavy slides — too much text kills marketing impact → REJECT

{variety_rules}

BE SPECIFIC in your feedback — name which slide number has which problem.

Return JSON only:
{{"approved": true/false, "feedback": "specific issues or empty string if approved", "score": 1-10}}"""


def ppt_planner_node(state: TonyState) -> TonyState:
    """Groq: plan slides with deep content analysis. Accepts critic feedback on retry."""
    attempt = state.get("ppt_attempt_count", 0)
    feedback = state.get("critic_feedback", "")

    print(f"📋 [PPT Planner] Planning slides for: {state['topic']} (attempt {attempt + 1})")

    from groq import Groq
    import json

    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    text = " ".join(s["narration_text"] for s in state["scenes"])

    # Inject critic feedback on retry
    feedback_section = ""
    if feedback:
        feedback_section = f"\n⚠️ PREVIOUS ATTEMPT WAS REJECTED. Fix these specific issues:\n{feedback}\nDo NOT repeat the same mistakes.\n"

    prompt = _PPT_PLANNER_PROMPT.format(feedback_section=feedback_section)

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user",   "content": f"TOPIC: {state['topic']}\n\nCONTENT:\n{text}"}
            ],
            response_format={"type": "json_object"}
        )
        data   = json.loads(response.choices[0].message.content)
        slides = data.get("slides", [])
        print(f"   Planned {len(slides)} slides:")
        for i, s in enumerate(slides):
            print(f"     {i+1}. [{s.get('layout','?')}] {s.get('data',{}).get('title') or s.get('data',{}).get('heading') or s.get('data',{}).get('statement','')[:40]}")
    except Exception as e:
        print(f"   ⚠️  Groq failed: {e} — using fallback")
        from ppt_engine.ppt_pipeline import _fallback_split
        slides = _fallback_split(state["topic"], text)

    state["slides"]          = slides
    state["critic_feedback"] = None   # clear feedback after use
    return state


def ppt_critic_node(state: TonyState) -> TonyState:
    """Groq: review slide plan quality. Reject if generic, repetitive, or wrong tone."""
    video_type = state.get("video_type") or "educational"
    print(f"🔍 [PPT Critic] Reviewing slide plan (mode: {video_type})...")

    from groq import Groq
    import json

    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    # Select the right "soul" based on video_type
    if video_type == "marketing":
        critic_prompt = _PPT_CRITIC_MARKETING.format(variety_rules=_VARIETY_RULES)
    else:
        critic_prompt = _PPT_CRITIC_EDUCATIONAL.format(variety_rules=_VARIETY_RULES)

    slides_summary = json.dumps([
        {"slide": i+1, "layout": s.get("layout"), "data": s.get("data"), "narration": s.get("narration")}
        for i, s in enumerate(state["slides"])
    ], indent=2)

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system",  "content": critic_prompt},
                {"role": "user",    "content": f"TOPIC: {state['topic']}\n\nSLIDE PLAN:\n{slides_summary}"}
            ],
            response_format={"type": "json_object"}
        )
        result   = json.loads(response.choices[0].message.content)
        approved = result.get("approved", True)
        feedback = result.get("feedback", "")
        score    = result.get("score", 7)

        print(f"   Score: {score}/10 | {'✅ Approved' if approved else '❌ Rejected'}")
        if not approved:
            print(f"   Feedback: {feedback}")

        state["critic_feedback"]   = None if approved else feedback
        state["ppt_attempt_count"] = state.get("ppt_attempt_count", 0) + (0 if approved else 1)

    except Exception as e:
        print(f"   ⚠️  Critic failed: {e} — auto-approving")
        state["critic_feedback"] = None

    return state


def ppt_renderer_node(state: TonyState) -> TonyState:
    """Render each slide as a 1920x1080 PNG."""
    print(f"🖼️  [PPT Renderer] Rendering {len(state['slides'])} slides...")

    _root = os.path.dirname(os.path.abspath(__file__))
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from ppt_engine.slide_generator import generate_slide_image

    job_prefix = f"job_{state.get('job_id', state['topic'].lower().replace(' ', '_'))}"
    job_dir = os.path.join("output", job_prefix)
    os.makedirs(job_dir, exist_ok=True)

    slide_paths = []
    for i, slide in enumerate(state["slides"]):
        layout      = slide.get("layout", "bullets")
        layout_data = slide.get("data", {})
        narration   = slide.get("narration", "")
        slide_text  = layout_data.get("heading") or layout_data.get("title") or layout_data.get("statement") or state["topic"]

        path = generate_slide_image(
            slide_text, i, output_dir=job_dir,
            narration=narration,
            layout=layout,
            layout_data=layout_data,
        )
        slide_paths.append(path)

    state["slide_paths"] = slide_paths
    return state


def ppt_tts_node(state: TonyState) -> TonyState:
    """Generate TTS audio for each slide's narration."""
    print(f"🔊 [PPT TTS] Generating audio for {len(state['slides'])} slides...")

    from tts_generator import generate_audio

    job_prefix = f"job_{state.get('job_id', state['topic'].lower().replace(' ', '_'))}"
    job_dir = os.path.join("output", job_prefix)
    audio_files = []

    for i, slide in enumerate(state["slides"]):
        narration = slide.get("narration", "")
        try:
            path = generate_audio(narration, i, output_dir=job_dir)
        except Exception as e:
            print(f"   ⚠️ TTS failed for slide {i}: {e}")
            path = None
        audio_files.append(path)

    state["audio_files"] = audio_files
    return state


def ppt_video_node(state: TonyState) -> TonyState:
    """Combine slides + audio into clips, optionally add avatar, concat to MP4."""
    print(f"🎬 [PPT Video] Building video from {len(state['slide_paths'])} slides...")

    from ppt_engine.ppt_pipeline import _image_to_video, _concat_clips

    job_prefix = f"job_{state.get('job_id', state['topic'].lower().replace(' ', '_'))}"
    job_dir    = os.path.join("output", job_prefix)
    with_avatar = state.get("with_avatar", False)
    clip_paths  = []

    for i, (slide_img, audio_path) in enumerate(zip(state["slide_paths"], state["audio_files"])):
        if audio_path is None:
            print(f"   ⚠️ Skipping clip {i} because audio is missing")
            continue

        clip_path = os.path.join(job_dir, f"clip_{i:02d}.mp4")

        if with_avatar:
            from avatar_generator import generate_avatar_video
            from moviepy.editor import VideoFileClip, CompositeVideoClip
            from moviepy.video.fx.all import loop as fx_loop

            base_path = os.path.join(job_dir, f"base_{i:02d}.mp4")
            _image_to_video(slide_img, audio_path, base_path)
            avatar_path = generate_avatar_video(
                state["slides"][i].get("narration", ""), audio_path, i,
                output_dir=job_dir, avatar_type="human"
            )
            base_clip   = VideoFileClip(base_path)
            raw_avatar  = VideoFileClip(avatar_path).without_audio()
            avatar_clip = fx_loop(raw_avatar, duration=base_clip.duration)
            av_resized  = avatar_clip.resize(width=320)
            W, H = base_clip.size
            composite = CompositeVideoClip([
                base_clip,
                av_resized.set_position((W - 340, H - 260)),
            ]).set_audio(base_clip.audio)
            try:
                composite.write_videofile(clip_path, fps=24, codec="libx264", logger=None)
            finally:
                # Close ALL MoviePy clips to prevent file-handle leaks (child first)
                if 'av_resized' in locals(): av_resized.close()
                if 'avatar_clip' in locals(): avatar_clip.close()
                if 'raw_avatar' in locals(): raw_avatar.close()
                if 'composite' in locals(): composite.close()
                if 'base_clip' in locals(): base_clip.close()
        else:
            # Non-avatar path uses pure ffmpeg subprocess — no MoviePy objects to leak
            _image_to_video(slide_img, audio_path, clip_path)

        if os.path.exists(clip_path):
            clip_paths.append(clip_path)
            print(f"   ✅ Clip {i+1}/{len(state['slide_paths'])}")

    state["clip_paths"] = clip_paths

    if not clip_paths:
        state["rendering_errors"] = "No slide clips were successfully rendered (likely TTS failures)."
        return state

    safe_topic  = state["topic"].lower().replace(" ", "_").replace("/", "_")
    final_output = os.path.join(job_dir, f"{safe_topic}_presentation.mp4")
    
    os.makedirs(job_dir, exist_ok=True) # Final safety check
    
    try:
        concat_success = _concat_clips(clip_paths, final_output)
    finally:
        for cpath in clip_paths:
            if os.path.exists(cpath):
                try: os.remove(cpath)
                except: pass
                
    if not concat_success:
        state["rendering_errors"] = "PPT concat failed"
        return state

    state["output_path"]      = os.path.abspath(final_output)
    state["rendering_errors"] = None
    print(f"   ✅ PPT video: {final_output}")
    return state


def _upload_to_s3_node(state: TonyState) -> TonyState:
    """Final node: upload the generated video to S3."""
    _log_progress(state, "DEPLOY", "Uploading final video to production CDN...")
    job_id = state.get("job_id")
    video_url = _upload_to_s3(state["output_path"], state["topic"], job_id)
    state["video_url"] = video_url
    
    # Industrial Disk Hygiene: Purge local job folder after cloud sync
    if video_url and os.environ.get("AUTO_DELETE_JOB_DIR", "false").lower() == "true":
        job_dir = os.path.join("output", f"job_{job_id}")
        if os.path.exists(job_dir):
            import shutil
            try:
                shutil.rmtree(job_dir)
                print(f"🧹 [Hygiene] Job Dir {job_id} purged after cloud sync.")
            except Exception as e:
                print(f"⚠️  Disk Hygiene Failure for {job_id}: {e}")
                
    return state


def explainer_node(state: TonyState) -> TonyState:
    """Stitch narration with B-roll metaphors (Higgsfield style)."""
    _log_progress(state, "EXPLAINER", "Production: Starting kinetic layered composition...")
    print(f"🎬 [Explainer Node] Generating narrative explainer for: {state['topic']}")
    
    from tts_generator import generate_audio
    from moviepy.editor import AudioFileClip, VideoFileClip, concatenate_videoclips
    from explainer_generator import generate_explainer_video

    job_prefix = f"job_{state.get('job_id', state['topic'].lower().replace(' ', '_'))}"
    job_dir = os.path.join("output", job_prefix)
    os.makedirs(job_dir, exist_ok=True)

    # 1. Call explainer generator (B-roll stitching)
    try:
        video_path = generate_explainer_video(
            state["scenes"], 
            state.get("image_paths", {}), 
            job_dir, 
            state["topic"]
        )
        state["output_path"] = os.path.abspath(video_path)
        # Note: Handed off to deploy_node for S3 sync and Disk Hygiene
    except Exception as e:
        print(f"   ❌ Explainer failed: {e}")
        state["rendering_errors"] = str(e)

    return state


def heygen_node(state: TonyState) -> TonyState:
    """Render high-fidelity talking head via HeyGen."""
    print(f"🚀 [HeyGen Node] Generating avatar for: {state['topic']}")
    
    from tts_generator import generate_audio
    from heygen_generator import generate_heygen_avatar

    job_prefix = f"job_{state.get('job_id', state['topic'].lower().replace(' ', '_'))}"
    job_dir = os.path.join("output", job_prefix)
    os.makedirs(job_dir, exist_ok=True)

    # 1. Generate audio for HeyGen to lip-sync to
    full_text = " ".join(s["narration_text"] for s in state["scenes"])
    audio_path = generate_audio(full_text, 0, output_dir=job_dir)
    state["audio_files"] = [audio_path]

    # 2. Call HeyGen
    output_path = os.path.join(job_dir, "heygen_avatar.mp4")
    heygen_video = generate_heygen_avatar(full_text, audio_path, output_path)
    state["heygen_video_path"] = heygen_video
    
    return state


def subtitle_node(state: TonyState) -> TonyState:
    """Generate kinetic Insta-style subtitles and overlay them."""
    print(f"🎞️  [Subtitle Node] Adding kinetic subtitles...")
    
    from subtitle_generator import generate_kinetic_subtitles
    from moviepy.editor import VideoFileClip, AudioFileClip

    video_path = state["heygen_video_path"]
    if not video_path or not os.path.exists(video_path):
        print("   ⚠️  HeyGen video not found — skipping subtitles.")
        # FALLBACK: ensure output_path is set to avoid fusion_node crash
        if video_path:
            state["output_path"] = os.path.abspath(video_path)
        return state

    video_clip = VideoFileClip(video_path)
    try:
        audio_path = state["audio_files"][0]
        
        tmp_aud = AudioFileClip(audio_path)
        try:
            audio_dur = tmp_aud.duration
        finally:
            tmp_aud.close()
            
        full_text  = " ".join(s["narration_text"] for s in state["scenes"])

        # Apply kinetic styling (Insta Reels style)
        final_clip = generate_kinetic_subtitles(video_clip, full_text, audio_dur, style="insta_reels")
        
        try:
            output_path = video_path.replace(".mp4", "_subtitled.mp4")
            final_clip.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
            state["output_path"] = os.path.abspath(output_path)
        finally:
            final_clip.close()
    finally:
        video_clip.close()

    return state


def fusion_node(state: TonyState) -> TonyState:
    """Final assembly sentinel."""
    print(f"🔗 [Fusion Node] Finalizing assembly...")
    
    if not state.get("output_path") or not os.path.exists(state["output_path"]):
        print("   ⚠️ No output_path found. Final generation failed.")
        state["rendering_errors"] = "Final production failed — check logs."
        
    return state

def deploy_node(state: TonyState) -> TonyState:
    """Industrial Deployment Sentinel: Unified S3 Sync + Post-Deploy Disk Hygiene."""
    _log_progress(state, "DEPLOY", "Synchronizing final assets with Production CDN...")
    
    job_id = state.get("job_id")
    output_path = state.get("output_path")
    topic = state.get("topic")
    
    if not output_path or not os.path.exists(output_path):
        _log_progress(state, "DEPLOY", "Handover Failure: Final video asset not found.", "warning")
        return state
        
    video_url = _upload_to_s3(output_path, topic, job_id)
    state["video_url"] = video_url
    
    # Industrial Disk Hygiene: Purge local job sandbox after successful cloud handover.
    if video_url and os.environ.get("AUTO_DELETE_JOB_DIR", "false").lower() == "true":
        job_dir = os.path.join("output", f"job_{job_id}")
        if os.path.exists(job_dir):
            import shutil
            try:
                shutil.rmtree(job_dir)
                _log_progress(state, "SYSTEM", f"Zenith Hygiene: Local sandbox {job_id} purged.")
            except Exception as e:
                print(f"⚠️ Hygiene Error: {e}")

    return state

# ── Router ────────────────────────────────────────────────────────────────────

def route_by_mode(state: TonyState) -> str:
    """After vision — branch to one of the 4 paths."""
    mode = state.get("render_mode")
    if mode == "presentation":
        return "ppt_planner"
    elif mode == "explainer":
        return "explainer"
    elif mode == "user_generated_video":
        return "heygen"
    return "architect"

def critic_should_continue(state: TonyState) -> str:
    """After critic — retry planner if rejected (max 2 retries), else proceed to renderer."""
    if state.get("critic_feedback") and state.get("ppt_attempt_count", 0) < 2:
        print(f"   ↩️  Sending back to planner (attempt {state['ppt_attempt_count']})")
        return "ppt_planner"
    return "ppt_renderer"

def should_continue(state: TonyState) -> str:
    """Route to healer on failure, up to 3 times. Otherwise deploy."""
    if state.get("rendering_errors") and state["attempt_count"] < 3:
        print(f"⚠️  Render error — routing to healer (attempt {state['attempt_count'] + 1}/3)")
        return "healer"
    return "deploy"


# ── Graph Configuration ───────────────────────────────────────────────────────

workflow = StateGraph(TonyState)

# Universal Node Definitions
workflow.add_node("director",      director_node)
workflow.add_node("vision",        vision_node)
workflow.add_node("architect",     architect_node)
workflow.add_node("supervisor",    supervisor_node)
workflow.add_node("healer",        healer_node)

workflow.add_node("ppt_planner",   ppt_planner_node)
workflow.add_node("ppt_critic",    ppt_critic_node)
workflow.add_node("ppt_renderer",  ppt_renderer_node)
workflow.add_node("ppt_tts",       ppt_tts_node)
workflow.add_node("ppt_video",     ppt_video_node)
workflow.add_node("explainer",     explainer_node)
workflow.add_node("heygen",        heygen_node)
workflow.add_node("subtitles",     subtitle_node)
workflow.add_node("fusion",        fusion_node)
workflow.add_node("deploy",        deploy_node)  # ← Unified Deployment Sentinel

# Execution Flow
workflow.set_entry_point("director")

workflow.add_edge("director", "vision")

workflow.add_conditional_edges("vision", route_by_mode, {
    "architect":   "architect",
    "ppt_planner": "ppt_planner",
    "explainer":   "explainer",
    "heygen":      "heygen",
})

# Path 1: Scientific/Math (Manim)
workflow.add_edge("architect",  "supervisor")
workflow.add_edge("healer",     "supervisor")
workflow.add_conditional_edges("supervisor", should_continue, {
    "healer": "healer",
    "deploy": "deploy"
})

# Path 2: Educational Presentations (PPT)
workflow.add_edge("ppt_planner",   "ppt_critic")
workflow.add_conditional_edges("ppt_critic", critic_should_continue, {
    "ppt_planner": "ppt_planner",
    "ppt_renderer": "ppt_renderer",
})
workflow.add_edge("ppt_renderer",  "ppt_tts")
workflow.add_edge("ppt_tts",       "ppt_video")
workflow.add_edge("ppt_video",     "deploy")

# Path 3: Narrative Explainers (B-roll)
workflow.add_edge("explainer",     "deploy")

# Path 4: Personalized Human Avatars (Deep-Fake)
workflow.add_edge("heygen",        "subtitles")
workflow.add_edge("subtitles",     "fusion")
workflow.add_edge("fusion",        "deploy")

# Terminal Deployment Node
workflow.add_edge("deploy",        END)

app = workflow.compile()


# ── Production CLI Engine ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    from dotenv import load_dotenv
    load_dotenv()

    parser = argparse.ArgumentParser(description="EaseToLearn Autonomous Factory")
    parser.add_argument("input",  nargs="?", default="bpf_source.html", help="HTML Source")
    parser.add_argument("topic",  nargs="?", default="Bronchopleural Fistula", help="Topic")
    parser.add_argument("--marketing", action="store_true", help="Marketing Critic Path")
    parser.add_argument("--no-vision", action="store_true", help="Skip Gemini Vision")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ Error: File {args.input} not found.")
        sys.exit(1)

    with open(args.input) as f:
        content = f.read()

    print(f"🚀 Starting Industrial Render: {args.topic}")
    final = app.invoke({
        "raw_input":          content,
        "topic":              args.topic,
        "visual_prompts":     None,
        "attempt_count":      0,
        "ppt_attempt_count":  0,
        "no_vision":          args.no_vision,
        "job_id":             "cli_test_" + str(os.getpid()),
        "parsed_facts":       None, "render_mode": None, "scenes": None,
        "image_path":         None, "audio_files": None, "manim_script_path": None,
        "output_path":        None, "video_url":   None, "rendering_errors":  None,
        "with_avatar":        False,
        "slides":             None, "slide_paths": None, "clip_paths": None,
        "critic_feedback":    None,
        "video_type":         "marketing" if args.marketing else "curriculum",
        "image_paths":        None,
        "visual_prompts":     None,
        "heygen_video_path":  None,
        "subtitle_style":     None,
    })

    print(f"\n🏆 Curtain Call: {args.topic}")
    print(f"   Industrial Video URL: {final.get('video_url')}")
    print(f"   Local Cache Snapshot: {final.get('output_path')}")

