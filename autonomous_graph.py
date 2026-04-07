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

  PRESENTATION PATH (new)
    ppt_planner_node  : Groq → splits text into slides (layout + data + narration)
    ppt_renderer_node : slide_generator → 1920x1080 PNG per slide
    ppt_tts_node      : tts_generator → MP3 per slide
    ppt_video_node    : ffmpeg → clip per slide → final MP4 (+ optional avatar)
    ppt_upload_node   : S3 upload
"""

import os
import glob
import subprocess
import importlib
from typing import TypedDict, List, Optional, Any

from langgraph.graph import StateGraph, END
import config
from healer_agent import run_healer


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def _manim() -> str:
    """Resolve manim binary — works in venv, Docker, and system installs."""
    import shutil
    # 1. same venv as running Python
    venv_manim = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "bin", "manim")
    if os.path.exists(venv_manim):
        return venv_manim
    # 2. system PATH (Docker container installs manim globally)
    system_manim = shutil.which("manim")
    if system_manim:
        return system_manim
    raise RuntimeError("manim binary not found — install with: pip install manim")


# ── State ─────────────────────────────────────────────────────────────────────

class TonyState(TypedDict):
    # ── Input ──────────────────────────────────────────
    raw_input:   str
    topic:       str

    # ── After director_node ────────────────────────────
    parsed_facts:  Optional[dict]
    render_mode:   Optional[str]
    scenes:        Optional[list]

    # ── After vision_node ──────────────────────────────
    image_path:  Optional[str]

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

    # ── Control ────────────────────────────────────────
    rendering_errors: Optional[str]
    attempt_count:    int
    with_avatar:      Optional[bool]   # presentation only — show avatar on slides


# ── Node 1: Director ──────────────────────────────────────────────────────────

def director_node(state: TonyState) -> TonyState:
    """Parse Tony AI HTML and run Claude director to produce scenes."""
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
    print(f"   Render mode: {director_output.render_mode} | Scenes: {len(scenes)}")
    return state


# ── Node 2: Vision ────────────────────────────────────────────────────────────

def vision_node(state: TonyState) -> TonyState:
    """Generate concept diagram using Gemini Imagen 3."""
    print(f"🎨 [Vision] Generating concept image for: {state['topic']}")

    # Only generate image for manim mode — presentation uses slide backgrounds
    if state.get("render_mode") != "manim":
        print("   Skipping image generation (presentation mode)")
        state["image_path"] = None
        return state

    from image_generator import generate_concept_image

    subject    = state["parsed_facts"].get("subject", "default")
    output_dir = os.path.join("output", f"job_{state['topic'].lower().replace(' ', '_')}")

    # Use pre-generated image if it already exists
    pre_path = os.path.join(output_dir, "tony_diagram.png")
    if os.path.exists(pre_path):
        print("   Using pre-generated concept image.")
        state["image_path"] = pre_path
        return state

    try:
        path = generate_concept_image(
            topic=state["topic"],
            subject=subject,
            output_dir=output_dir,
        )
        state["image_path"] = path
    except Exception as e:
        # Non-fatal — template renderer will use a dark background fallback
        print(f"   ⚠️  Image generation failed: {e}. Continuing with fallback.")
        state["image_path"] = None

    return state


# ── Node 3: Architect ─────────────────────────────────────────────────────────

def architect_node(state: TonyState) -> TonyState:
    """Convert scenes into a Manim script (deterministic templates). Manim path only."""
    print(f"📐 [Architect] Building Manim script for: {state['topic']}")

    job_dir = os.path.join("output", f"job_{state['topic'].lower().replace(' ', '_')}")
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
            scene["visual_data"]["duration"] = round(clip.duration, 2)
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
    print(f"🔍 [Supervisor] Rendering — attempt {state['attempt_count'] + 1}")

    job_dir     = os.path.dirname(state["manim_script_path"])
    script_path = state["manim_script_path"]
    topic_safe  = state["topic"].replace(" ", "").replace("-", "")

    # ── 1. Render Manim ───────────────────────────────
    print("   Rendering Manim animation...")
    render_result = subprocess.run(
        [_manim(), "-ql", script_path, "EaseToLearnScene", "--media_dir", job_dir],
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
    combined.write_audiofile(combined_audio_path, logger=None)
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
    state["video_url"] = _upload_to_s3(final_output, state["topic"])

    return state


def healer_node(state: TonyState) -> TonyState:
    """Ask Healer Agent to fix scripts based on errors."""
    print(f"🩹 [Healer] Fixing render errors — attempt {state['attempt_count'] + 1}")

    with open(state["manim_script_path"], "r") as f:
        script_content = f.read()

    fixed_script = run_healer(script_content, state["rendering_errors"])

    with open(state["manim_script_path"], "w") as f:
        f.write(fixed_script)

    state["attempt_count"] += 1  # increment here only — supervisor never increments
    state["rendering_errors"] = None
    return state


# ── S3 Upload ─────────────────────────────────────────────────────────────────

def _upload_to_s3(local_path: str, topic: str) -> str:
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
    s3_key = f"videos/{topic.lower().replace(' ', '_')}/{os.path.basename(local_path)}"

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

Return valid JSON only:
{{"slides": [{{"layout": "...", "data": {{...}}, "narration": "..."}}]}}"""


_PPT_CRITIC_PROMPT = """You are a ruthless quality critic for educational presentation videos.

Review this slide plan and decide: APPROVE or REJECT.

REJECT if ANY of these are true:
1. Any narration starts with generic phrases like "let's explore", "in this slide", "today we", "welcome to"
2. Any chaos_chapter subtitle is generic (e.g. "Introduction", "Overview", "Getting Started")
3. Same layout used 4+ times
4. Any bullet point is vague (no specific names, numbers, or dates)
5. Any slide could appear in a video about a DIFFERENT topic without changing
6. The big_statement contains no specific fact (no number, name, or date)
7. The key_highlight fact is vague or not memorable

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
    """Groq: review slide plan quality. Reject if generic or repetitive."""
    print(f"🔍 [PPT Critic] Reviewing slide plan...")

    from groq import Groq
    import json

    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    slides_summary = json.dumps([
        {"slide": i+1, "layout": s.get("layout"), "data": s.get("data"), "narration": s.get("narration")}
        for i, s in enumerate(state["slides"])
    ], indent=2)

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system",  "content": _PPT_CRITIC_PROMPT},
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
    import sys
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from ppt_engine.slide_generator import generate_slide_image

    job_dir = os.path.join("output", f"job_{state['topic'].lower().replace(' ', '_')}")
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

    job_dir = os.path.join("output", f"job_{state['topic'].lower().replace(' ', '_')}")
    audio_files = []

    for i, slide in enumerate(state["slides"]):
        narration = slide.get("narration", "")
        path = generate_audio(narration, i, output_dir=job_dir)
        audio_files.append(path)

    state["audio_files"] = audio_files
    return state


def ppt_video_node(state: TonyState) -> TonyState:
    """Combine slides + audio into clips, optionally add avatar, concat to MP4."""
    print(f"🎬 [PPT Video] Building video from {len(state['slide_paths'])} slides...")

    from ppt_engine.ppt_pipeline import _image_to_video, _concat_clips

    job_dir    = os.path.join("output", f"job_{state['topic'].lower().replace(' ', '_')}")
    with_avatar = state.get("with_avatar", False)
    clip_paths  = []

    for i, (slide_img, audio_path) in enumerate(zip(state["slide_paths"], state["audio_files"])):
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
            composite.write_videofile(clip_path, fps=24, codec="libx264", logger=None)
            # Close ALL MoviePy clips to prevent file-handle leaks
            composite.close(); base_clip.close(); raw_avatar.close(); avatar_clip.close()
        else:
            # Non-avatar path uses pure ffmpeg subprocess — no MoviePy objects to leak
            _image_to_video(slide_img, audio_path, clip_path)

        if os.path.exists(clip_path):
            clip_paths.append(clip_path)
            print(f"   ✅ Clip {i+1}/{len(state['slide_paths'])}")

    state["clip_paths"] = clip_paths

    safe_topic  = state["topic"].lower().replace(" ", "_").replace("/", "_")
    final_output = os.path.join(job_dir, f"{safe_topic}_presentation.mp4")
    _concat_clips(clip_paths, final_output)

    state["output_path"]      = os.path.abspath(final_output)
    state["rendering_errors"] = None
    print(f"   ✅ PPT video: {final_output}")
    return state


def ppt_upload_node(state: TonyState) -> TonyState:
    """Upload PPT video to S3."""
    print(f"☁️  [PPT Upload] Uploading to S3...")
    state["video_url"] = _upload_to_s3(state["output_path"], state["topic"])
    return state


# ── Router ────────────────────────────────────────────────────────────────────

def route_by_mode(state: TonyState) -> str:
    """After vision — branch to manim or ppt path."""
    if state.get("render_mode") == "presentation":
        return "ppt_planner"
    return "architect"


def critic_should_continue(state: TonyState) -> str:
    """After critic — retry planner if rejected (max 2 retries), else proceed to renderer."""
    if state.get("critic_feedback") and state.get("ppt_attempt_count", 0) < 2:
        print(f"   ↩️  Sending back to planner (attempt {state['ppt_attempt_count']})")
        return "ppt_planner"
    return "ppt_renderer"


def should_continue(state: TonyState) -> str:
    """Route to healer on failure, up to 3 times. Manim only."""
    if state.get("rendering_errors") and state["attempt_count"] < 3:
        print(f"⚠️  Render error — routing to healer (attempt {state['attempt_count']})")
        return "healer"
    return END


# ── Graph ─────────────────────────────────────────────────────────────────────

workflow = StateGraph(TonyState)

# ── Shared nodes ───────────────────────────────────────────────────────────────
workflow.add_node("director",    director_node)
workflow.add_node("vision",      vision_node)

# ── Manim path ─────────────────────────────────────────────────────────────────
workflow.add_node("architect",   architect_node)
workflow.add_node("supervisor",  supervisor_node)
workflow.add_node("healer",      healer_node)

# ── PPT path ───────────────────────────────────────────────────────────────────
workflow.add_node("ppt_planner",  ppt_planner_node)
workflow.add_node("ppt_critic",   ppt_critic_node)
workflow.add_node("ppt_renderer", ppt_renderer_node)
workflow.add_node("ppt_tts",      ppt_tts_node)
workflow.add_node("ppt_video",    ppt_video_node)
workflow.add_node("ppt_upload",   ppt_upload_node)

# ── Edges ──────────────────────────────────────────────────────────────────────
workflow.set_entry_point("director")
workflow.add_edge("director", "vision")

# Branch after vision
workflow.add_conditional_edges("vision", route_by_mode, {
    "architect":   "architect",
    "ppt_planner": "ppt_planner",
})

# Manim path (unchanged)
workflow.add_edge("architect",  "supervisor")
workflow.add_edge("healer",     "supervisor")
workflow.add_conditional_edges("supervisor", should_continue)

# PPT path — planner → critic → (retry? → planner | approved → renderer)
workflow.add_edge("ppt_planner",  "ppt_critic")
workflow.add_conditional_edges("ppt_critic", critic_should_continue, {
    "ppt_planner": "ppt_planner",
    "ppt_renderer": "ppt_renderer",
})
workflow.add_edge("ppt_renderer", "ppt_tts")
workflow.add_edge("ppt_tts",      "ppt_video")
workflow.add_edge("ppt_video",    "ppt_upload")
workflow.add_edge("ppt_upload",   END)

app = workflow.compile()


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    html_file = sys.argv[1] if len(sys.argv) > 1 else "bpf_source.html"
    topic     = sys.argv[2] if len(sys.argv) > 2 else "Bronchopleural Fistula"

    with open(html_file) as f:
        html = f.read()

    print(f"🚀 Starting pipeline for: {topic}")
    final = app.invoke({
        "raw_input":          html,
        "topic":              topic,
        "attempt_count":      0,
        "ppt_attempt_count":  0,
        "parsed_facts":       None, "render_mode": None, "scenes": None,
        "image_path":         None, "audio_files": None, "manim_script_path": None,
        "output_path":        None, "video_url":   None, "rendering_errors":  None,
        "with_avatar":        False,
        "slides":             None, "slide_paths": None, "clip_paths": None,
        "critic_feedback":    None,
    })

    print(f"\n🏆 Done!")
    print(f"   Video URL : {final.get('video_url')}")
    print(f"   Local path: {final.get('output_path')}")
