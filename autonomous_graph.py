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
import time
import subprocess
import importlib
import json
import re
from typing import TypedDict, List, Optional, Any, Dict

from langgraph.graph import StateGraph, END
import config
from healer_agent import run_healer
from knowledge_vector_store import retrieve_related_research


# ── Industrial Helpers ───────────────────────────────────────────────────────

def _ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


_api_bridge_refs = None
_MAX_ERROR_LEN = 2000
_S3_UPLOAD_MAX_ATTEMPTS = 3
_S3_RETRY_SLEEP_SECONDS = 1
_MANIM_TIMEOUT_SECONDS = 600
_FFMPEG_TIMEOUT_SECONDS = 600
_GROQ_MAX_ATTEMPTS = 2

def _run_command_with_group_cleanup(args: list, timeout: int, env: dict = None) -> subprocess.CompletedProcess:
    """Industrial Sentinel: Run a command in a process group and kill the entire group on timeout."""
    import signal
    import os
    
    env = env or os.environ
    # start_new_session=True makes this the leader of a new process group.
    # This ensures that killing the group kills all descendants (LaTeX, etc.)
    proc = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
        text=True, env=env, start_new_session=True
    )
    
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return subprocess.CompletedProcess(args, proc.returncode, stdout, stderr)
    except subprocess.TimeoutExpired:
        # Kill the entire process group
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception as e:
            print(f"   ⚠️ Cleanup failed for timed-out process group {proc.pid}: {e}")
        
        # Collect whatever output we had
        proc.wait()
        raise subprocess.TimeoutExpired(args, timeout, output=None, stderr=None)
    except Exception as e:
        # Ensure we don't leave lingering processes on other errors
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except: pass
        raise e

def _kill_process_group(proc, timeout_occured=False):
    """Industrial Sentinel: Force-kill an entire process group (including LaTeX/FFmpeg children)."""
    import signal
    try:
        if proc.poll() is None:  # Still running
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            if timeout_occured:
                print(f"   ⚠️ Process Group {proc.pid} killed due to timeout.")
    except Exception as e:
        print(f"   ⚠️ Failed to kill process group {proc.pid}: {e}")

def _log_progress(state: "TonyState", node_name: str, msg: str, log_type: str = "info", duration: float = None):
    """Industrial Sentinel: Universal structured telemetry logger with circular memory capping."""
    job_id = state.get("job_id")
    if not job_id: return
    
    from datetime import datetime
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    log_entry = {
        "timestamp": timestamp,
        "node": node_name.upper(),
        "type": log_type.upper(),
        "msg": msg
    }
    if duration is not None:
        log_entry["duration_sec"] = round(duration, 2)

    # Print human-readable version to terminal
    print(f"📡 [{timestamp}] [{node_name.upper()}] {msg}" + (f" ({duration:.1f}s)" if duration else ""))

    global _api_bridge_refs
    if _api_bridge_refs is None:
        try:
            import api_bridge
            _api_bridge_refs = api_bridge
        except ImportError: pass
        
    from llm_factory import LLMFactory, clean_llm_json

    if _api_bridge_refs:
        with _api_bridge_refs._jobs_lock:
            if job_id in _api_bridge_refs.jobs:
                job = _api_bridge_refs.jobs[job_id]
                if "logs" not in job: job["logs"] = []
                job["logs"].append(log_entry)
                if len(job["logs"]) > 100:
                    job["logs"] = job["logs"][-100:]
                
                job["updated_at"] = timestamp

                # Progress mapping: nodes to completion percentage
                progress_map = {
                    "DIRECTOR":     15,
                    "VISION":       25,
                    "ARCHITECT":    35,
                    "PPT_PLANNER":  35,
                    "PPT_CRITIC":   45,
                    "PPT_RENDERER": 55,
                    "PPT_TTS":      65,
                    "PPT_VIDEO":    80,
                    "SUPERVISOR":   75,
                    "HEALER":       60,
                    "EXPLAINER":    75,
                    "HEYGEN":       65,
                    "SUBTITLE":     80,
                    "FUSION":       88,
                    "DEPLOY":       95,
                }
                job["progress"] = progress_map.get(node_name.upper(), job.get("progress", 10))
                
                # INDUSTRIAL LEDGER: Sync grounded costs to API (Stateful update)
                job["ledger"] = state.get("ledger", {})
                # For metrics compatibility
                metrics = job.get("metrics") or {}
                metrics.update(job["ledger"])
                job["metrics"] = metrics
        
        _api_bridge_refs._save_jobs()

def _record_error(state: "TonyState", node_name: str, error: str) -> None:
    """Set consistent error message and push it to job telemetry."""
    compact_error = (error or "Unknown pipeline error").strip()
    compact_error = compact_error[-_MAX_ERROR_LEN:]
    state["rendering_errors"] = compact_error
    _log_progress(state, node_name, compact_error, "error")

def _log_fallback(state: "TonyState", node_name: str, fallback: str, reason: str, error_class: str = "RuntimeError") -> None:
    """Emit structured warning telemetry for non-fatal fallback paths."""
    payload = {
        "event": "fallback",
        "node": node_name,
        "fallback": fallback,
        "reason": reason[:400],
        "error_class": error_class,
        "job_id": state.get("job_id"),
    }
    _log_progress(state, node_name, json.dumps(payload, ensure_ascii=False), "warning")

def _llm_json_with_retry(*, messages: list[dict], node_name: str, state: "TonyState", system_prompt: Optional[str] = None) -> dict:
    """Retry LLM JSON call for transient failures, then raise."""
    from llm_factory import LLMFactory, clean_llm_json
    last_exc = None
    for attempt in range(1, _GROQ_MAX_ATTEMPTS + 1):
        try:
            content, usage = LLMFactory.get_completion(
                messages=messages,
                system_prompt=system_prompt,
                json_mode=True,
                include_usage=True,
                job_id=state.get("job_id")
            )
            # Accumulate Ledger
            state["ledger"] = state.get("ledger", {})
            state["ledger"]["prompt_tokens"] = state["ledger"].get("prompt_tokens", 0) + usage.get("prompt_tokens", 0)
            state["ledger"]["completion_tokens"] = state["ledger"].get("completion_tokens", 0) + usage.get("completion_tokens", 0)
            
            return clean_llm_json(content)
        except Exception as e:
            if isinstance(e, (json.JSONDecodeError, KeyError, TypeError, ValueError)):
                raise RuntimeError(f"LLM response was non-retryable for {node_name}: {e}") from e
            last_exc = e
            if attempt < _GROQ_MAX_ATTEMPTS:
                _log_fallback(
                    state,
                    node_name,
                    fallback="llm_retry",
                    reason=f"attempt {attempt}/{_GROQ_MAX_ATTEMPTS} failed: {e}",
                    error_class=type(e).__name__,
                )
                time.sleep(attempt)
    raise RuntimeError(f"LLM call failed after {_GROQ_MAX_ATTEMPTS} attempts: {last_exc}")

def get_job_dir(state: "TonyState") -> str:
    """Isolated sandbox for the current job."""
    job_id = state.get("job_id", "fallback")
    path = os.path.join("output", f"job_{job_id}")
    os.makedirs(path, exist_ok=True)
    return path

def get_topic_safe(state: "TonyState") -> str:
    """Returns a filesystem-safe topic string truncated to 50 characters."""
    import re
    topic = state.get("topic", "video")
    # Strip everything except alphanumeric, underscore, dash
    safe = re.sub(r'[^a-zA-Z0-9_\-]', '_', topic.lower().strip())
    # Collapse multiple underscores
    safe = re.sub(r'_+', '_', safe)
    return safe[:50]


def _manim() -> str:
    """Resolve manim binary — works in venv, Docker, and system installs."""
    import os
    import sys
    import shutil

    # Industrial Path Injection: Ensure Homebrew, MacTeX, and standard Linux standard paths are visible to the engine
    extra_paths = ["/usr/bin", "/usr/local/bin", "/opt/homebrew/bin", "/Library/TeX/texbin"]
    os.environ["PATH"] = ":".join(extra_paths) + ":" + os.environ.get("PATH", "")

    # 1. Check local venv first (highest priority)
    _root = os.path.dirname(os.path.abspath(__file__))
    venv_manim = os.path.join(_root, "venv", "bin", "manim")
    if os.path.exists(venv_manim): return venv_manim

    # 2. Check system PATH (now includes industrial injections)
    system_manim = shutil.which("manim")
    if system_manim: return system_manim

    raise RuntimeError("manim binary not found. Please ensure it is installed in the venv.")


# ── State ─────────────────────────────────────────────────────────────────────

class TonyState(TypedDict):
    # Core state
    topic: str
    video_type: str        # 'educational' | 'marketing' | 'social'
    render_mode: str       # 'manim' | 'presentation' | 'heygen' | 'explainer' (auto)
    with_avatar: bool      # Toggles HeyGen node
    
    # Financial & Audit (Phase 6)
    ledger: Dict[str, Any] # Grounded usage tracking (tokens, chars, sec)
    
    # Storyboard & Script
    script_segments: List[Dict[str, Any]] 

    # ── Input ──────────────────────────────────────────
    job_id:      Optional[str]
    topic:       str
    raw_input:   str
    source_type: Optional[str] # 'html' | 'json' | 'markdown'
    use_elevenlabs: bool # Cost control switch
    avatar_type: Optional[str] # 'logo' | 'human' | 'pro' | 'user' | 'heygen'
    avatar_id:   Optional[str] # Specific HeyGen avatar ID
    overrides:   Optional[dict] # Manual toggles (from RenderOverrides model)

    # ── After director_node ────────────────────────────
    parsed_facts:  Optional[dict]
    render_mode:   Optional[str]
    scenes:        Optional[list]

    # ── After vision_node ──────────────────────────────
    image_path:  Optional[str]
    image_paths: Optional[dict[str, str]] # Map of scene_id or asset_id to local path
    landmark_coords: Optional[dict]       # Map of scene_id -> {label: [x, y]}

    # ── After architect_node ───────────────────────────
    manim_script_path: Optional[str]
    audio_files:       Optional[list]   # per-scene mp3 paths (generated before Manim)

    # ── After supervisor_node ─────────────────────────
    output_path:  Optional[str]
    video_url:    Optional[str]
    thumbnail_url: Optional[str]

    # ── PPT-specific (presentation path) ──────────────
    slides:           Optional[list]   # [{layout, data, narration}] from Groq
    slide_paths:      Optional[list]   # PNG paths per slide
    clip_paths:       Optional[list]   # clip MP4 paths per slide
    critic_feedback:  Optional[str]    # feedback from ppt_critic → fed back to planner
    ppt_attempt_count: int             # how many times planner has been retried by critic
    search_queries:   Optional[list[str]] # queries requested by Director
    search_results:   Optional[list[dict]] # snippets returned by SearXNG
    knowledge_base:   Optional[dict]      # verified facts from factory_knowledge/

    # ── Explainer/HeyGen-specific ─────────────────────
    heygen_video_path: Optional[str]   # Path to downloaded HeyGen video

    subtitle_style:   Optional[str]    # "insta_reels" | "classic"

    # ── Control ────────────────────────────────────────
    rendering_errors:  Optional[str]
    attempt_count:     int
    no_vision:         bool
    research_count:    int # Phase 8: Loop Guard
    
    # ── Industrial Resilience (New Architecture) ──────
    rejected_attempts: List[Dict[str, Any]]  # Stores [{"plan": ..., "critique": ...}] for revision
    media_manifest:    List[Dict[str, Any]]  # Assets requested by Architect/Planner


# ── Node 1: Director ──────────────────────────────────────────────────────────

def director_node(state: TonyState) -> TonyState:
    """The Factory Manager: Analyzes topic, chooses render mode, and plans scenes."""
    import copy
    import time
    import re
    start_t = time.time()
    state = copy.deepcopy(state)
    
    # Initializing Ledger (Phase 6)
    if "ledger" not in state or state["ledger"] is None:
        state["ledger"] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "elevenlabs_chars": 0,
            "heygen_seconds": 0
        }
    
    # Initialize Industrial Memory & Manifest
    state["rejected_attempts"] = state.get("rejected_attempts") or []
    state["media_manifest"]    = state.get("media_manifest") or []
    
    if "research_count" not in state:
        state["research_count"] = 0
    
    _log_progress(state, "DIRECTOR", f"Analyzing curriculum and selecting render path for: {state['topic']}...")
    print(f"🎬 [Director] Parsing HTML and writing scene script for: {state['topic']}")

    from html_parser import parse_tony_html
    from director_agent import run_director
    from knowledge_manager import get_knowledge

    # ━━━ 1. Knowledge Retrieval ━━━
    # If we have existing knowledge, use it to anchor the LLM and prevent hallucinations.
    kb_facts = get_knowledge(state["topic"])
    if kb_facts:
        print(f"   📚 Knowledge Cache Hit: Using verified facts for {state['topic']}")
        state["knowledge_base"] = kb_facts
        _log_progress(state, "KNOWLEDGE", f"📚 KB Hit: Using verified facts for {state['topic']}")
    
    parsed = None
    raw_input = state["raw_input"]
    
    # If composite list, we skip the direct JSON-to-Dict path and go to html_parser
    if isinstance(raw_input, str):
        input_str = raw_input.strip()
        if input_str.startswith("{") or input_str.startswith("["):
            try:
                import json
                raw_data = json.loads(input_str)
                if isinstance(raw_data, list) and len(raw_data) > 0:
                    raw_data = raw_data[0]
                
                # Standardize for DirectorAgent
                parsed = {
                    "topic": state["topic"],
                    "subject": raw_data.get("subject", "unknown"),
                    "content_type": raw_data.get("content_type", "concept"),
                    "concept": "",
                    "key_points": [],
                    "options": {},
                    "sections": {}
                }
                
                # Map json_data to concept string
                if "json_data" in raw_data:
                    parts = []
                    for item in raw_data["json_data"]:
                        t = item.get("title", "")
                        d = item.get("description", "")
                        parts.append(f"### {t}\n{d}")
                    parsed["concept"] = "\n\n".join(parts)
                    if any("=" in p for p in parts):
                        parsed["content_type"] = "numerical"
                
                print(f"   📦 JSON Ingestion: Successfully mapped structured data for {state['topic']}")
            except Exception as e:
                print(f"   ⚠️ JSON Parse Error: {e}. Falling back to HTML.")

    if not parsed:
        parsed = parse_tony_html(state["raw_input"], topic_hint=state["topic"])
    
    state["parsed_facts"] = parsed
    source_label = (state.get("source_type") or "HTML").upper()
    _log_progress(state, "KNOWLEDGE", f"📚 {source_label} Source: Successfully ingested input curriculum.")

    print(f"   Subject: {parsed['subject']} | Type: {parsed['content_type']}")

    director_output, usage = run_director(
        parsed, 
        search_results=state.get("search_results"),
        knowledge_base=state.get("knowledge_base"),
        job_id=state.get("job_id"),
        overrides=state.get("overrides")
    )
    # INDUSTRIAL LEDGER: Capture tokens
    state["ledger"] = state.get("ledger", {})
    state["ledger"]["prompt_tokens"] = state["ledger"].get("prompt_tokens", 0) + usage.get("prompt_tokens", 0)
    state["ledger"]["completion_tokens"] = state["ledger"].get("completion_tokens", 0) + usage.get("completion_tokens", 0)
    
    # ── RENDER MODE ENFORCEMENT ──
    # Priority: 1. Manual Overrides | 2. Top-level request | 3. Autonomous Director
    overrides = state.get("overrides") or {}
    forced_mode = overrides.get("render_mode")
    user_mode = (state.get("render_mode") or "auto").lower().strip()
    
    if forced_mode:
        print(f"   🎯 Manual Override: Forcing render_mode = {forced_mode}")
        state["render_mode"] = forced_mode
    elif user_mode not in ["auto", ""]:
        state["render_mode"] = user_mode
    else:
        state["render_mode"] = director_output.render_mode

    # Industrial Hardening: Pydantic v1/v2 compatibility
    scenes = [
        (s.model_dump() if hasattr(s, "model_dump") else s.dict()) 
        for s in director_output.scenes
    ]

    # ── MATHEMATICAL SANITY CHECK ─────────────────────────────────────────────
    # Prevent the LLM from hallucinating bad arithmetic in derivation steps.
    from math_validator import check_numerical_sanity
    for scene in scenes:
        if scene["visual_type"] == "formula_derivation":
            steps = scene.get("visual_data", {}).get("steps", [])
            if not check_numerical_sanity(steps):
                _record_error(state, "DIRECTOR", "Mathematical Hallucination Detected in formula_derivation.")
                raise RuntimeError("Mathematical Sanity Check Failed: The LLM generated invalid arithmetic.")


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
                # INDUSTRIAL OVERRIDE: Always cross out ALL wrong options to ensure a clean reveal.
                # Even if the LLM provided a partial list, we force extraction of all incorrect letters.
                all_wrong = [l for l in ("A", "B", "C", "D") if l != correct_letter]
                
                # Check which of these options actually exist in the parsed curriculum
                existing_wrong = [l for l in all_wrong if l in (state.get("parsed_facts", {}).get("options") or {})]
                
                # Use existing wrong options if found, otherwise fall back to all standard wrong letters
                scene["visual_data"]["letters"] = existing_wrong if existing_wrong else all_wrong
                scene["visual_data"].pop("letter", None)
        print(f"   Correct answer locked: {correct_letter}. {correct_name}")

    # 3. INDUSTRIAL PLACEHOLDER HUNTER: Ensure real content from the lesson is used
    html_text = state.get("parsed_facts", {}).get("html_content", "")
    for scene in scenes:
        v_data = scene.get("visual_data", {})
        v_type = scene.get("visual_type")
        
        # Recover bullets/steps if lazy
        if v_type in ["concept_bullets", "step_by_step"]:
            for i, p in enumerate(v_data.get("bullets", []) + v_data.get("steps", [])):
                if "Key point" in str(p) or "Step " in str(p):
                     # Force extraction of first 3 sentences from HTML if lazy
                     real_facts = re.findall(r'<li>(.*?)</li>', html_text)
                     if real_facts:
                         v_data["bullets" if v_type == "concept_bullets" else "steps"] = real_facts[:3]
                         print(f"   🎯 Placeholder Hunter: Replaced lazy text with real lesson data.")
                         break

        # High-Contrast Image Labels
        if v_type == "concept_image":
            # Ensure label doesn't wash out
            if v_data.get("label") == "Maintenance Therapy in Schizophrenia" or not v_data.get("label"):
                 v_data["label"] = state.get("topic", "Key Medical Concept")

        # MCQ String Scrubber (fixes Gemma's literal JSON bug)
        if v_type == "mcq_layout":
            raw_options = v_data.get("options", {})
            fixed_options = {}
            
            # Universal Handler for Dict or List
            if isinstance(raw_options, list):
                # Convert list of dicts to flat dict
                for item in raw_options:
                    if isinstance(item, dict):
                        l = item.get("letter", "A")
                        t = item.get("text") or item.get("name") or str(item)
                        fixed_options[l] = t
            elif isinstance(raw_options, dict):
                fixed_options = raw_options
            
            # Now scrub each string
            for l, t in fixed_options.items():
                if isinstance(t, str):
                    # Aggressive regex to extract content from Hallucinated JSON strings
                    # Handles: {'text': '...'}, {'content': '...'}, {'name': '...'}
                    for key in ["text", "content", "name", "body"]:
                        match = re.search(rf"['\"]{key}['\"]:\s*['\"](.*?)['\"]", t)
                        if match:
                            t = match.group(1)
                            break
                    # Final cleanup: remove any leftover braces if the whole string was a JSON literal
                    t = re.sub(r"^\{.*\}|\{.*\}$", "", t).strip("'\" ")
                fixed_options[l] = t
            v_data["options"] = fixed_options

    # MINIMUM SCENE GUARD: If Gemma gets lazy and plans < 3 scenes for a full lesson
    if len(scenes) < 3 and state.get("render_mode") == "manim":
        print(f"   ⚠️  Laziness Alert: Gemma planned only {len(scenes)} scenes. FORCING INDUSTRIAL FALLBACK...")
        # INDUSTRIAL RECOVERY: Build a subject-aware masterclass if the AI fails
        facts = state.get("parsed_facts", {})
        topic = state.get("topic", "Masterclass")
        subject = facts.get("subject", "unknown")
        
        if subject in ["maths", "physics"] or facts.get("content_type") == "numerical":
            # ── Mathematical Recovery ──
            steps = facts.get("steps", [])
            if not steps:
                steps = ["Identify the given parameters.", "Apply the relevant formula.", "Solve for the unknown variable."]
            
            fallback_scenes = [
                {
                    "visual_type": "title_card",
                    "visual_data": {"title": topic, "subtitle": "Mathematical Derivation"},
                    "narration_text": f"Today we are exploring the mathematical foundations of {topic}. Let's break down the derivation step-by-step."
                },
                {
                    "visual_type": "formula_derivation",
                    "visual_data": {"heading": "Derivation Process", "steps": steps[:5]},
                    "narration_text": "Observe how the equation transforms as we apply each step of the logic."
                }
            ]
            if len(steps) > 5:
                fallback_scenes.append({
                    "visual_type": "formula_derivation",
                    "visual_data": {"heading": "Conclusion", "steps": steps[5:10]},
                    "narration_text": "Continuing the process, we reach the final result."
                })
            fallback_scenes.append({
                "visual_type": "summary",
                "visual_data": {"heading": "Key Takeaway", "points": [f"Final result for {topic} derived successfully."]},
                "narration_text": "This concludes our derivation. Mastery of these steps is key for your exams."
            })
        else:
            # ── Medical/General Recovery ──
            mcq_options = facts.get("options", {})
            if not mcq_options:
                mcq_options = {
                    "A": "Increase in Cardiac Output",
                    "B": "Decrease in Left Ventricular Pressure",
                    "C": "Pulmonary Venous Congestion",
                    "D": "Systemic Hypertension"
                }
                print(f"   ⚠️  Recovery: No MCQ found in source. Injecting high-yield placeholders.")

            correct_letter = facts.get("correct_answer", "C")
            correct_name = mcq_options.get(correct_letter, {}).get("name") if isinstance(mcq_options.get(correct_letter), dict) else mcq_options.get(correct_letter, "Pulmonary Venous Congestion")
            explanation = mcq_options.get(correct_letter, {}).get("explanation") if isinstance(mcq_options.get(correct_letter), dict) else "This reflects the underlying pathophysiology discussed in the lesson."

            fallback_scenes = [
                {
                    "visual_type": "title_card",
                    "visual_data": {"title": topic, "subtitle": "Comprehensive Review"},
                    "narration_text": f"Welcome back. Today we are performing a deep dive into {topic}. This is essential material for your boards."
                },
                {
                    "visual_type": "concept_bullets",
                    "visual_data": {"heading": "Core Principles", "bullets": facts.get("key_points", ["Conceptual Overview", "Mechanism of Action"])[:3]},
                    "narration_text": "Let's begin with the core principles. Understanding the underlying mechanism is the key to mastering this topic."
                },
                {
                    "visual_type": "annotated_image",
                    "visual_data": {
                        "label": f"Anatomy of {topic}", 
                        "target_landmark": "heart",
                        "region": "center_right",
                        "bullets": ["Primary clinical features", "Mechanism of dysfunction"]
                    },
                    "narration_text": "Observe the relevant structures here. Identifying the specific dysfunctional regions is critical for diagnosis."
                },
                {
                    "visual_type": "mcq_layout",
                    "visual_data": {
                        "question": f"What is the primary clinical feature of {topic}?",
                        "options": {l: (o.get("name") if isinstance(o, dict) else str(o)) for l, o in mcq_options.items()}
                    },
                    "narration_text": "Now, let's test your knowledge with a board-style question. Study the options carefully."
                },
                {
                    "visual_type": "cross_out",
                    "visual_data": {
                        "question": f"What is the primary clinical feature of {topic}?",
                        "letters": [l for l in mcq_options.keys() if l != correct_letter]
                    },
                    "narration_text": "We can immediately rule out several of these. Focus on the core pathophysiology we discussed."
                },
                {
                    "visual_type": "answer_reveal",
                    "visual_data": {
                        "question": f"What is the primary clinical feature of {topic}?",
                        "letter": correct_letter,
                        "name": correct_name,
                        "explanation": explanation
                    },
                    "narration_text": "The correct answer is highlighted. Clinical mastery requires recognizing these specific patterns."
                }
            ]
        scenes = fallback_scenes
        state["scenes"] = scenes
        print(f"   ✅ Industrial Recovery: Forced a subject-appropriate fallback structure.")

    state["scenes"] = scenes
    state["search_queries"] = director_output.search_queries
    
    print(f"   Render mode: {state['render_mode'].upper()} | Scenes: {len(scenes)}")
    if state["search_queries"]:
        print(f"   🔎 Research Requested: {len(state['search_queries'])} queries")
    print(f"   💡 Reasoning: {director_output.decision_reasoning}")
    
    _log_progress(state, "DIRECTOR", f"Planned {len(scenes)} scenes for {state['render_mode']} path.", duration=time.time() - start_t)
    return state


def research_node(state: TonyState) -> TonyState:
    """Execute SearXNG queries requested by the Director."""
    import copy
    import time
    start_t = time.time()
    state = copy.deepcopy(state)
    
    queries = state.get("search_queries") or []
    topic = state.get("topic", "")
    
    # INDUSTRIAL SENTINEL: Semantic Memory Recall
    if topic:
        print(f"   🧠 Vector Brain: Consulting internal memory for '{topic}'...")
        hits = retrieve_related_research(
            topic, 
            node="research", 
            job_id=state.get("job_id", "unknown"),
            render_mode=state.get("render_mode", "unknown")
        )
        if hits and hits[0]["similarity"] > 0.85:
            match = hits[0]
            print(f"   🎯 Vector Hit! Retrieved '{match['topic']}' (Similarity: {match['similarity']})")
            _log_progress(state, "KNOWLEDGE", f"💎 KNOWLEDGE ACQUIRED: Reusing grounded research for '{match['topic']}'", log_type="knowledge")
            state["knowledge_base"] = {
                "summary": match["summary"],
                "key_facts": match["key_facts"],
                "visual_metaphors": match["metadata"].get("video_metaphors", [])
            }
            state["search_queries"] = [] # Bypass web search
            return state

    if not queries:
        return state

    _log_progress(state, "RESEARCH", f"Performing metasearch for {len(queries)} terms...")
    
    from searxng_tool import search_searxng
    all_results = state.get("search_results") or []
    
    try:
        for query in queries:
            print(f"   🔎 Searching: {query}")
            _log_progress(state, "RESEARCH", f"🔎 Metasearch: '{query}'")
            results = search_searxng(query, job_id=state.get("job_id"))
            all_results.extend(results)
    except Exception as e:
        # CIRCUIT BREAKER: If search fails technically, log warning and proceed with internal knowledge
        warn_msg = f"⚠️ SearXNG Connection Failed: {e}. Falling back to internal knowledge."
        print(f"   {warn_msg}")
        _log_progress(state, "RESEARCH", warn_msg, "warning")
    
    # Store unique results by URL to avoid bloat
    seen_urls = set()
    unique_results = []
    for r in all_results:
        if r["url"] not in seen_urls:
            unique_results.append(r)
            seen_urls.add(r["url"])
    
    state["search_results"] = unique_results
    state["search_queries"] = [] # Clear queries to prevent infinite loops

    # ━━━ 2. Knowledge Distillation & Memorization ━━━
    # Convert raw search results into a clean, reusable fact sheet.
    from knowledge_manager import distill_search_results, save_knowledge, get_knowledge
    if unique_results:
        print(f"   🧠 Distilling search results into verified knowledge...")
        _log_progress(state, "KNOWLEDGE", f"🧠 Distilling {len(unique_results)} search results into verified knowledge...")
        distilled = distill_search_results(state["topic"], unique_results, job_id=state.get("job_id"))
        save_knowledge(state["topic"], distilled)
        state["knowledge_base"] = distilled
    
    _log_progress(state, "RESEARCH", f"Gathered {len(unique_results)} unique reference points and updated KB.", duration=time.time() - start_t)
    state["research_count"] = state.get("research_count", 0) + 1
    return state


def vision_node(state: TonyState) -> TonyState:
    """Generate concept diagrams and multimodal metaphors using Gemini Imagen 3."""
    import copy
    import time
    start_t = time.time()
    state = copy.deepcopy(state)
    _log_progress(state, "VISION", "AI Vision Engine: Initializing high-fidelity asset generation...")
    print(f"🎨 [Vision] Generating assets for: {state['topic']}")

    if state.get("no_vision"):
        print("   Skipping image generation (user-requested)")
        state["image_path"] = None
        state["image_paths"] = {}
        return state

    # Phase 8 Optimization: Skip Vision logic early if the current mode doesn't use Imagen assets
    render_mode = state.get("render_mode")
    if render_mode not in ["manim", "explainer", "auto"]:
        print(f"   ℹ️  Vision Node: Skipping Imagen calls for {render_mode} path.")
        state["image_path"] = None
        state["image_paths"] = {}
        return state

    from image_generator import generate_concept_image

    job_prefix = f"job_{state.get('job_id', get_topic_safe(state))}"
    output_dir = os.path.join("output", job_prefix)
    os.makedirs(output_dir, exist_ok=True)

    subject = state.get("parsed_facts", {}).get("subject", "default")

    # ── PATH 1: Manim (Scene-Driven Asset Generation) ────────────────
    if state.get("render_mode") in ["manim", "auto"]:
        scenes = state.get("scenes") or []
        # Back-Pressure: Generate if any scene needs an image (legacy or annotated)
        needs_image = any(s.get("visual_type") in ["concept_image", "annotated_image"] for s in scenes)
        
        if not needs_image:
            print("   ℹ️  Vision Node: No image scenes detected. Skipping diagram generation.")
            state["image_path"] = None
            state["landmark_coords"] = {}
            return state

        # ── Legacy concept_image: single global diagram ──────────────
        if any(s.get("visual_type") == "concept_image" for s in scenes):
            pre_path = os.path.join(output_dir, "tony_diagram.png")
            if os.path.exists(pre_path):
                state["image_path"] = pre_path
            else:
                try:
                    target_prompt = state["topic"]
                    for s in scenes:
                        if s.get("visual_type") == "concept_image":
                            target_prompt = s.get("visual_data", {}).get("image_prompt") or s.get("visual_data", {}).get("title") or state["topic"]
                            break
                    state["image_path"] = generate_concept_image(target_prompt, subject, output_dir=output_dir, filename="tony_diagram.png", job_id=state.get("job_id"))
                except Exception as e:
                    state["image_path"] = None
                    _log_fallback(state, "VISION", "skip_concept_image", str(e), type(e).__name__)

        # ── Annotated image: per-scene image + vision grounding ──────
        all_landmark_coords = {}
        for i, scene in enumerate(scenes):
            if scene.get("visual_type") != "annotated_image":
                continue

            v_data = scene.get("visual_data", {})
            label = v_data.get("label", state.get("topic", "diagram"))
            img_filename = f"annotated_{i}_{label[:30].replace(' ', '_').lower()}.png"
            img_pre_path = os.path.join(output_dir, img_filename)

            # Generate the image if not already cached
            if not os.path.exists(img_pre_path):
                try:
                    img_path = generate_concept_image(label, subject, output_dir=output_dir, filename=img_filename, job_id=state.get("job_id"))
                except Exception as e:
                    print(f"   ⚠️  Annotated image generation failed for scene {i}: {e}")
                    img_path = state.get("image_path")  # fallback to global
            else:
                img_path = img_pre_path

            # Inject the image path into the scene data for the renderer
            if img_path:
                scene["visual_data"]["image_path"] = img_path

            # ── Vision Grounding: get precise landmark coordinates ────
            target_landmark = v_data.get("target_landmark", "")
            if target_landmark and img_path:
                try:
                    from vision_grounder import ground_landmarks
                    coords = ground_landmarks(img_path, [target_landmark], job_id=state.get("job_id"))
                    if coords:
                        # Store coords keyed by scene index for the renderer
                        all_landmark_coords[str(i)] = coords
                        print(f"   📍 Scene {i}: Grounded '{target_landmark}' → {coords}")
                except Exception as e:
                    print(f"   ⚠️  Vision grounding failed for scene {i}: {e} — falling back to region grid")

        state["landmark_coords"] = all_landmark_coords

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
                pre_path = os.path.join(output_dir, f"{asset_id}.png")
                
                if os.path.exists(pre_path):
                    image_paths[asset_id] = pre_path
                else:
                    print(f"   Generating counting item: {item}...")
                    try:
                        path = generate_concept_image(item, subject="counting_item", output_dir=output_dir, filename=f"{asset_id}.png", job_id=state.get("job_id"))
                        image_paths[asset_id] = path
                    except Exception as e:
                        print(f"   ⚠️  Counting asset failed: {e}")
                
                # BACKGROUND for counting scene
                bg_prompt = v_data.get("background_prompt")
                if bg_prompt:
                    bg_id = f"counting_bg_{i}"
                    bg_pre_path = os.path.join(output_dir, f"{bg_id}.png")
                    if os.path.exists(bg_pre_path):
                        image_paths[bg_id] = bg_pre_path
                    else:
                        print(f"   Generating thematic background for counting scene {i}: {bg_prompt}...")
                        try:
                            bg_path = generate_concept_image(bg_prompt, subject="explainer_background", output_dir=output_dir, filename=f"{bg_id}.png", job_id=state.get("job_id"))
                            image_paths[bg_id] = bg_path
                        except Exception as e:
                            print(f"   ⚠️  Counting background failed: {e}")

            elif v_type == "b_roll_clip" or v_type == "generative_video":
                prompt = v_data.get("prompt", "Educational visual")
                asset_id = f"metaphor_{i}"
                pre_path = os.path.join(output_dir, f"{asset_id}.png")
                
                if os.path.exists(pre_path):
                    image_paths[asset_id] = pre_path
                else:
                    print(f"   Generating cinematic metaphor for scene {i}...")
                    try:
                        path = generate_concept_image(prompt, subject="explainer_metaphor", output_dir=output_dir, filename=f"{asset_id}.png", job_id=state.get("job_id"))
                        image_paths[asset_id] = path
                    except Exception as e:
                        print(f"   ⚠️  Metaphor asset failed: {e}")

        state["image_paths"] = image_paths
        _log_progress(state, "VISION", f"Generated {len(image_paths)} assets for {state.get('render_mode')}.", duration=time.time() - start_t)

    return state


# ── Node 3: Architect ─────────────────────────────────────────────────────────

def architect_node(state: TonyState) -> TonyState:
    """Convert scenes into a Manim script (deterministic templates). Manim path only."""
    import copy
    import time
    start_t = time.time()
    state = copy.deepcopy(state)
    _log_progress(state, "ARCHITECT", "Orchestration: Building mathematical animation blueprint...")
    print(f"📐 [Architect] Building Manim script for: {state['topic']}")

    job_prefix = f"job_{state.get('job_id', get_topic_safe(state))}"
    job_dir = os.path.join("output", job_prefix)
    os.makedirs(job_dir, exist_ok=True)

    # manim mode — generate TTS first to get real durations, then build Manim script
    from tts_generator import generate_audio
    from moviepy.editor import AudioFileClip
    from template_renderer import build_manim_script

    scenes = state["scenes"] or []
    image_path = state.get("image_path")

    # 1. INDUSTRIAL GUARD: Fix stringified visual_data if the LLM hallucinated the type
    for scene in scenes:
        if isinstance(scene.get("visual_data"), str):
            try:
                import json
                scene["visual_data"] = json.loads(scene["visual_data"])
            except:
                scene["visual_data"] = {"name": scene["visual_data"]}

    # 2. INDUSTRIAL MANIFEST: Declare asset needs instead of hoping they exist.
    # We scan scenes for 'concept_image' and add them to the manifest.
    for i, scene in enumerate(scenes):
        if scene.get("visual_type") == "concept_image":
            v_data = scene.get("visual_data", {})
            prompt = v_data.get("image_prompt") or v_data.get("title") or state["topic"]
            state["media_manifest"].append({
                "id": f"scene_{i}_image",
                "type": "concept_image",
                "prompt": prompt,
                "target_scene_index": i
            })
    
    print("   Generating TTS audio for sync...")
    audio_files = []
    use_el = state.get("use_elevenlabs", False)
    for i, scene in enumerate(scenes):
        # ━━━ Audio & Alignment ━━━
        audio_path, char_count = generate_audio(scene["narration_text"], i, output_dir=job_dir, use_elevenlabs=use_el, job_id=state.get("job_id"))
        
        # INDUSTRIAL LEDGER: Capture characters
        state["ledger"] = state.get("ledger", {})
        state["ledger"]["elevenlabs_chars"] = state["ledger"].get("elevenlabs_chars", 0) + char_count
        audio_files.append(audio_path)

    # 2. Inject real duration into each scene's visual_data
    for i, (scene, audio_path) in enumerate(zip(scenes, audio_files)):
        try:
            clip = AudioFileClip(audio_path)
            try:
                scene["visual_data"]["duration"] = round(clip.duration, 2)
            finally:
                clip.close()
        except Exception as e:
            _log_fallback(state, "ARCHITECT", "duration_default_3s", str(e), type(e).__name__)
            scene["visual_data"]["duration"] = 3.0  # safe fallback

    state["audio_files"] = audio_files
    state["scenes"]      = scenes

    # INDUSTRIAL PROVENANCE: Trace the source of truth for labels/diagrams
    truth_source = "KNOWLEDGE_BASE" if state.get("knowledge_base") else "PARSED_FACTS"
    _log_progress(state, "ARCHITECT", f"Provenance Trace: Script labels anchored in {truth_source}.")

    # 3. Build Manim script with synced durations
    script_path = os.path.join(job_dir, "scene_script.py")
    build_manim_script(
        scenes=scenes,
        image_path=state.get("image_path"),
        topic=state["topic"],
        output_path=script_path,
        knowledge_base=state.get("knowledge_base"),
        landmark_coords=state.get("landmark_coords", {}),
        job_id=state.get("job_id")
    )
    state["manim_script_path"] = script_path
    print(f"   Script written with synced durations: {script_path}")
    _log_progress(state, "ARCHITECT", "Manim script generated successfully.", duration=time.time() - start_t)
    return state


# ── Node 4: Supervisor ────────────────────────────────────────────────────────

def supervisor_node(state: TonyState) -> TonyState:
    """Global Render Sentinel — Coordinates Manim, Audio, and S3."""
    import copy
    import time
    start_t = time.time()
    state = copy.deepcopy(state)
    _log_progress(state, "SUPERVISOR", "Production: Rendering Manim mathematics animation...")
    print(f"🔍 [Supervisor] Rendering — attempt {state['attempt_count'] + 1}")

    job_dir     = os.path.dirname(state["manim_script_path"])
    script_path = state["manim_script_path"]
    topic_safe  = get_topic_safe(state)


    # ── 1. Render Manim (Industrial Hardening: Sandbox-Local Cache) ──
    print("   Rendering Manim animation with cache isolation...")
    try:
        # Industrial Sentinel: Use group-aware runner to prevent zombie LaTeX sub-processes
        render_result = _run_command_with_group_cleanup(
            [_manim(), "-ql", script_path, "EaseToLearnScene",
             "--media_dir", os.path.join(job_dir, "manim_media")],
            timeout=_MANIM_TIMEOUT_SECONDS
        )

    except subprocess.TimeoutExpired:
        _record_error(state, "SUPERVISOR", f"Manim render timed out after {_MANIM_TIMEOUT_SECONDS}s")
        return state

    if render_result.returncode != 0:
        print(f"   ❌ Manim render failed.")
        _record_error(state, "SUPERVISOR", render_result.stderr)
        return state

    # Find rendered video
    renders = glob.glob(f"{job_dir}/**/EaseToLearnScene.mp4", recursive=True)
    if not renders:
        _record_error(state, "SUPERVISOR", "Manim output file not found after render")
        return state

    manim_video = renders[0]
    print(f"   ✅ Manim video: {manim_video}")

    # ── 2. Concatenate pre-generated TTS audio ────────
    print("   Concatenating narration audio...")
    from moviepy.editor import AudioFileClip, concatenate_audioclips

    audio_files = state.get("audio_files") or []
    if not audio_files:
        _record_error(state, "SUPERVISOR", "No narration audio files found for Manim stitching.")
        return state
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

    try:
        stitch_result = _run_command_with_group_cleanup([
            _ffmpeg(), "-y",
            "-i", manim_video,
            "-i", combined_audio_path,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-map", "0:v", "-map", "1:a",
            "-movflags", "+faststart",
            "-shortest",
            final_output,
        ], timeout=_FFMPEG_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        _record_error(state, "SUPERVISOR", f"FFmpeg stitch timed out after {_FFMPEG_TIMEOUT_SECONDS}s")
        return state

    if stitch_result.returncode != 0:
        _record_error(state, "SUPERVISOR", stitch_result.stderr)
        return state


    print(f"   ✅ Final video: {final_output}")
    state["output_path"]       = os.path.abspath(final_output)
    state["rendering_errors"]  = None

    # ── 4. Upload to S3 ───────────────────────────────
    state["video_url"] = _upload_to_s3(final_output, state["topic"], state.get("job_id"))

    _log_progress(state, "SUPERVISOR", "Manim production lifecycle complete.", duration=time.time() - start_t)
    return state


def healer_node(state: TonyState) -> TonyState:
    """Industrial Healer: Claude Opus fixes broken Manim code."""
    import copy
    import time
    start_t = time.time()
    state = copy.deepcopy(state)
    print(f"🩹 [Healer] Fixing render errors — attempt {state['attempt_count'] + 1}")

    with open(state["manim_script_path"], "r") as f:
        script_content = f.read()

    # INDUSTRIAL PROVENANCE: Trace the source of the repair logic
    truth_source = "KNOWLEDGE_BASE" if state.get("knowledge_base") else "SEARCH_RESULTS"
    _log_progress(state, "HEALER", f"Provenance Trace: Self-healing grounded in {truth_source}.")
    
    fixed_script, usage = run_healer(
        script_content, 
        state["rendering_errors"], 
        knowledge_base=state.get("knowledge_base"),
        job_id=state.get("job_id")
    )
    # INDUSTRIAL LEDGER: Capture tokens
    state["ledger"] = state.get("ledger", {})
    state["ledger"]["prompt_tokens"] = state["ledger"].get("prompt_tokens", 0) + usage.get("prompt_tokens", 0)
    state["ledger"]["completion_tokens"] = state["ledger"].get("completion_tokens", 0) + usage.get("completion_tokens", 0)

    with open(state["manim_script_path"], "w") as f:
        f.write(fixed_script)

    state["attempt_count"] += 1
    state["rendering_errors"] = None  # Reset error state for the fresh attempt
    _log_progress(state, "HEALER", f"Repair completed. Retrying render (attempt {state['attempt_count']}).", duration=time.time() - start_t)
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
        # Local dev: act as a local CDN fallback via FastAPI
        print("   ℹ️  S3_BUCKET not set — using local CDN fallback via /stream/")
        job_id_safe = job_id or "unknown"
        filename = os.path.basename(local_path)
        
        # Default to localhost:8000 (FastAPI port) if LOCAL_CDN_URL is not set
        base_url = os.environ.get("LOCAL_CDN_URL", "http://localhost:8000").rstrip("/")
        
        # Use the existing FastAPI streaming endpoint
        full_url = f"{base_url}/stream/{job_id_safe}/{filename}"
        
        _log_fallback(
            {"job_id": job_id, "rendering_errors": None},  # minimal state for structured telemetry
            "DEPLOY",
            fallback=full_url,
            reason="S3_BUCKET not set",
            error_class="MissingConfig",
        )
        return full_url

    import boto3
    # Inclusion of job_id in S3 key prevents URL collision for identical topics
    normalized_topic = str(topic or "video").lower()
    safe_topic = "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in normalized_topic)
    safe_topic = "_".join(filter(None, safe_topic.split("_"))) or "video"
    raw_prefix = str(job_id or os.environ.get("JOB_ID_FALLBACK", "factory"))
    unique_prefix = "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in raw_prefix)
    unique_prefix = "_".join(filter(None, unique_prefix.split("_"))) or "factory"
    s3_key = f"videos/{unique_prefix}_{safe_topic}/{os.path.basename(local_path)}"

    import botocore

    print(f"   ☁️  Uploading to s3://{bucket}/{s3_key} ...")
    s3 = boto3.client("s3", region_name=region)
    for attempt in range(1, _S3_UPLOAD_MAX_ATTEMPTS + 1):
        try:
            s3.upload_file(
                local_path,
                bucket,
                s3_key,
                ExtraArgs={"ContentType": "video/mp4"},
            )
            break
        except botocore.exceptions.ClientError as e:
            print(f"   ❌ S3 Upload Failed (IAM/Bucket issue) on attempt {attempt}/{_S3_UPLOAD_MAX_ATTEMPTS}: {e}")
            if attempt >= _S3_UPLOAD_MAX_ATTEMPTS:
                job_id = job_id or "unknown"
                filename = os.path.basename(local_path)
                return f"/stream/{job_id}/{filename}"
        except Exception as e:
            print(f"   ❌ S3 Upload Failed (unexpected) on attempt {attempt}/{_S3_UPLOAD_MAX_ATTEMPTS}: {e}")
            if attempt >= _S3_UPLOAD_MAX_ATTEMPTS:
                filename = os.path.basename(local_path)
                return f"/stream/{job_id}/{filename}"
        time.sleep(_S3_RETRY_SLEEP_SECONDS * min(attempt, 3))

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
- PRIORITIZE GROUND TRUTH: If a "Verified Ground Truth" section is provided below, treat it as your absolute primary source for facts.

STEP 3 — Layout rules:
- 6 to 9 slides total
- MANDATORY: Start each major chapter with chaos_chapter (use 2-3 times with incrementing numbers)
- NO layout should appear more than 3 times
- chaos_chapter subtitles must be specific to the content — never generic like "Introduction"
- big_statement must quote a specific dramatic fact, not a vague claim
- bullets must list SPECIFIC items (names, dates, numbers) — not vague categories
- key_highlight must show ONE specific number/date/name that defines this topic
- Narration must be 1-3 sentences, conversational, adds insight beyond the slide text

{knowledge_section}

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
    import time
    start_t = time.time()
    attempt = state.get("ppt_attempt_count", 0)
    feedback = state.get("critic_feedback", "")

    print(f"📋 [PPT Planner] Planning slides for: {state['topic']} (attempt {attempt + 1})")

    import json
    text = " ".join(s["narration_text"] for s in state["scenes"])

    # Inject Knowledge Base if available
    knowledge_section = ""
    kb = state.get("knowledge_base")
    if kb:
        knowledge_section = f"\n━━━ VERIFIED GROUND TRUTH (KNOWLEDGE BASE) ━━━\n{json.dumps(kb, indent=2)}\n"

    # Inject historical rejections on retry
    feedback_section = ""
    rejections = state.get("rejected_attempts", [])
    if rejections:
        history = "\n".join([
            f"--- REJECTED ATTEMPT {i+1} ---\nPLAN: {r['plan']}\nCRITIQUE: {r['feedback']}" 
            for i, r in enumerate(rejections)
        ])
        feedback_section = f"\n⚠️ PREVIOUS ATTEMPTS WERE REJECTED. Do NOT repeat these specific mistakes:\n{history}\n"
    elif feedback:
        feedback_section = f"\n⚠️ PREVIOUS ATTEMPT WAS REJECTED. Fix these specific issues:\n{feedback}\n"

    prompt = _PPT_PLANNER_PROMPT.format(
        knowledge_section=knowledge_section,
        feedback_section=feedback_section
    )

    try:
        data = _llm_json_with_retry(
            messages=[
                {"role": "user",   "content": f"TOPIC: {state['topic']}\n\nCONTENT:\n{text}"}
            ],
            system_prompt=prompt,
            node_name="PPT_PLANNER",
            state=state,
        )
        slides = data.get("slides", [])
        print(f"   Planned {len(slides)} slides:")
        for i, s in enumerate(slides):
            print(f"     {i+1}. [{s.get('layout','?')}] {s.get('data',{}).get('title') or s.get('data',{}).get('heading') or s.get('data',{}).get('statement','')[:40]}")
    except Exception as e:
        if isinstance(e, (json.JSONDecodeError, KeyError, TypeError, ValueError)):
            _record_error(state, "PPT_PLANNER", f"Non-retryable planner failure: {e}")
            return state
        print(f"   ⚠️  Groq failed: {e} — using fallback")
        _log_fallback(state, "PPT_PLANNER", "fallback_split", str(e), type(e).__name__)
        from ppt_engine.ppt_pipeline import _fallback_split
        slides = _fallback_split(state["topic"], text)

    state["slides"]          = slides
    state["critic_feedback"] = None   # clear feedback after use
    _log_progress(state, "PPT_PLANNER", f"Planned {len(slides)} slides.", duration=time.time() - start_t)
    return state


def ppt_critic_node(state: TonyState) -> TonyState:
    """Groq: review slide plan quality. Reject if generic, repetitive, or wrong tone."""
    import time
    start_t = time.time()
    video_type = state.get("video_type") or "educational"
    print(f"🔍 [PPT Critic] Reviewing slide plan (mode: {video_type})...")

    from groq import Groq
    import json

    groq_api_key = os.environ.get("GROQ_API_KEY")
    client = Groq(api_key=groq_api_key) if groq_api_key else None

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
        result = _llm_json_with_retry(
            messages=[
                {"role": "user",    "content": f"TOPIC: {state['topic']}\n\nSLIDE PLAN:\n{slides_summary}"}
            ],
            system_prompt=critic_prompt,
            node_name="PPT_CRITIC",
            state=state,
        )
        approved = result.get("approved", True)
        feedback = result.get("feedback", "")
        score    = result.get("score", 7)

        print(f"   Score: {score}/10 | {'✅ Approved' if approved else '❌ Rejected'}")
        if not approved:
            print(f"   Feedback: {feedback}")

        state["critic_feedback"]   = None if approved else feedback
        state["ppt_attempt_count"] = state.get("ppt_attempt_count", 0) + (0 if approved else 1)
        
        # INDUSTRIAL MEMORY: Sliding Window (Cap at 3, truncate text)
        if not approved:
            if "rejected_attempts" not in state or state["rejected_attempts"] is None:
                state["rejected_attempts"] = []
            
            # Truncate feedback for prompt efficiency
            truncated_feedback = feedback[:500] + "..." if len(feedback) > 500 else feedback
            
            state["rejected_attempts"].append({
                "plan": slides_summary[:1000], # Summary only
                "feedback": truncated_feedback,
                "score": score
            })
            
            # Keep only last 3 to prevent prompt bloat
            if len(state["rejected_attempts"]) > 3:
                state["rejected_attempts"] = state["rejected_attempts"][-3:]

    except Exception as e:
        # Phase 8: Critic Resilience — Auto-Approve on failure to prevent production block
        print(f"   ⚠️  Critic unavailable: {e} — Auto-approving slide plan.")
        _log_fallback(state, "PPT_CRITIC", "auto_approve", str(e), type(e).__name__)
        state["critic_feedback"] = None # Auto-Approved

    _log_progress(state, "PPT_CRITIC", f"Critic review complete (Approved: {approved}).", duration=time.time() - start_t)
    return state


def ppt_renderer_node(state: TonyState) -> TonyState:
    """Render each slide as a 1920x1080 PNG."""
    import time
    start_t = time.time()
    print(f"🖼️  [PPT Renderer] Rendering {len(state['slides'])} slides...")

    _root = os.path.dirname(os.path.abspath(__file__))
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from ppt_engine.slide_generator import generate_slide_image
    from ppt_engine.ppt_pipeline import run_ppt_pipeline # Import to get access to job_id passing if needed

    job_prefix = f"job_{state.get('job_id', get_topic_safe(state))}"
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
            job_id=state.get("job_id")
        )
        if path and os.path.exists(path):
            slide_paths.append(path)
        else:
            print(f"   ⚠️ Slide render failed for index {i}")

    state["slide_paths"] = slide_paths
    _log_progress(state, "PPT_RENDERER", "Visual presentation layer rendered.", duration=time.time() - start_t)
    return state


def ppt_tts_node(state: TonyState) -> TonyState:
    """Generate TTS audio for each slide's narration."""
    import time
    start_t = time.time()
    print(f"🔊 [PPT TTS] Generating audio for {len(state['slides'])} slides...")

    from tts_generator import generate_audio

    job_prefix = f"job_{state.get('job_id', get_topic_safe(state))}"
    job_dir = os.path.join("output", job_prefix)
    audio_files = []

    for i, slide in enumerate(state["slides"]):
        narration = (slide.get("narration", "") or "").strip()
        if not narration:
            data = slide.get("data", {})
            narration = data.get("heading") or data.get("title") or state["topic"]
        try:
            path, char_count = generate_audio(narration, i, output_dir=job_dir, job_id=state.get("job_id"))
            # INDUSTRIAL LEDGER: Capture characters
            state["ledger"] = state.get("ledger", {})
            state["ledger"]["elevenlabs_chars"] = state["ledger"].get("elevenlabs_chars", 0) + char_count
        except Exception as e:
            _record_error(state, "PPT_TTS", f"TTS failed for slide {i}: {e}")
            return state
        audio_files.append(path)

    state["audio_files"] = audio_files
    _log_progress(state, "PPT_TTS", "Narration synthesis complete.", duration=time.time() - start_t)
    return state


def ppt_video_node(state: TonyState) -> TonyState:
    """Combine slides + audio into clips, optionally add avatar, concat to MP4."""
    import time
    start_t = time.time()
    print(f"🎬 [PPT Video] Building video from {len(state['slide_paths'])} slides...")

    from ppt_engine.ppt_pipeline import _image_to_video, _concat_clips

    job_prefix = f"job_{state.get('job_id', get_topic_safe(state))}"
    job_dir    = os.path.join("output", job_prefix)
    with_avatar = state.get("with_avatar", False)
    clip_paths  = []

    slide_paths = state.get("slide_paths") or []
    audio_files = state.get("audio_files") or []
    for i, (slide_img, audio_path) in enumerate(zip(slide_paths, audio_files)):
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
            avatar_path, duration_sec = generate_avatar_video(
                state["slides"][i].get("narration", ""), audio_path, i,
                output_dir=job_dir, avatar_type=state.get("avatar_type") or "human",
                job_id=state.get("job_id")
            )
            # INDUSTRIAL LEDGER: Capture duration
            state["ledger"] = state.get("ledger", {})
            state["ledger"]["heygen_seconds"] = state["ledger"].get("heygen_seconds", 0) + duration_sec
            
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
            print(f"   ✅ Clip {i+1}/{len(slide_paths)}")

    state["clip_paths"] = clip_paths

    if not clip_paths:
        _record_error(state, "PPT_VIDEO", "No slide clips were successfully rendered (likely TTS failures).")
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
                except Exception as e:
                    print(f"⚠️ Cleanup Warning: Could not remove ephemeral clip {os.path.basename(cpath)}: {e}")
                    _log_fallback(state, "PPT_VIDEO", "cleanup_clip_failed", str(e), type(e).__name__)

                
    if not concat_success:
        _record_error(state, "PPT_VIDEO", "PPT concat failed")
        return state
    if not os.path.exists(final_output):
        _record_error(state, "PPT_VIDEO", "PPT output file missing after concat.")
        return state

    state["output_path"]      = os.path.abspath(final_output)
    state["rendering_errors"] = None
    print(f"   ✅ PPT video: {final_output}")
    _log_progress(state, "PPT_VIDEO", "Presentation video production complete.", duration=time.time() - start_t)
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
                _log_fallback(state, "DEPLOY", "job_dir_cleanup_failed", str(e), type(e).__name__)
                
    return state


def _run_presentation_fallback(state: TonyState, source_node: str) -> TonyState:
    """Recover failed non-presentation paths by running the presentation pipeline."""
    _log_fallback(state, source_node, "presentation_recovery", "Falling back to presentation pipeline.", "Fallback")
    state["render_mode"] = "presentation"
    state = ppt_planner_node(state)
    if state.get("rendering_errors"):
        return state
    state = ppt_critic_node(state)
    if state.get("critic_feedback"):
        state = ppt_planner_node(state)
    if state.get("rendering_errors"):
        return state
    state = ppt_renderer_node(state)
    if state.get("rendering_errors"):
        return state
    state = ppt_tts_node(state)
    if state.get("rendering_errors"):
        return state
    return ppt_video_node(state)


def explainer_node(state: TonyState) -> TonyState:
    """Explainer engine - B-roll and multimodal metaphors."""
    import copy
    import time
    start_t = time.time()
    state = copy.deepcopy(state)
    print(f"🎬 [Explainer Node] Generating narrative explainer for: {state['topic']}")
    
    from explainer_generator import generate_explainer_video

    job_prefix = f"job_{state.get('job_id', get_topic_safe(state))}"
    job_dir = os.path.join("output", job_prefix)
    os.makedirs(job_dir, exist_ok=True)

    # 1. Call explainer generator (B-roll stitching)
    try:
        video_path, metrics = generate_explainer_video(
            state["scenes"], 
            state.get("image_paths", {}), 
            job_dir, 
            state["topic"],
            job_id=state.get("job_id")
        )
        state["output_path"] = os.path.abspath(video_path)
        
        # INDUSTRIAL LEDGER: Capture Higgsfield calls
        state["ledger"] = state.get("ledger", {})
        state["ledger"]["higgsfield_calls"] = state["ledger"].get("higgsfield_calls", 0) + metrics.get("higgsfield_calls", 0)
        # Note: Handed off to deploy_node for S3 sync and Disk Hygiene
    except Exception as e:
        print(f"   ❌ Explainer failed: {e}")
        _record_error(state, "EXPLAINER", str(e))
        return _run_presentation_fallback(state, "EXPLAINER")

    _log_progress(state, "EXPLAINER", "Narrative production lifecycle complete.", duration=time.time() - start_t)
    return state


def heygen_node(state: TonyState) -> TonyState:
    """Render high-fidelity talking head via HeyGen."""
    import copy
    import time
    start_t = time.time()
    state = copy.deepcopy(state)
    _log_progress(state, "HEYGEN", "Personalization: Orchestrating avatar generation...")
    
    from tts_generator import generate_audio
    from heygen_generator import generate_heygen_avatar

    job_prefix = f"job_{state.get('job_id', get_topic_safe(state))}"
    job_dir = os.path.join("output", job_prefix)
    os.makedirs(job_dir, exist_ok=True)

    # 1. Generate audio for HeyGen to lip-sync to
    try:
        full_text = " ".join(s["narration_text"] for s in state["scenes"])
        audio_path, char_count = generate_audio(full_text, 0, output_dir=job_dir, job_id=state.get("job_id"))
        # INDUSTRIAL LEDGER: Capture characters
        state["ledger"] = state.get("ledger", {})
        state["ledger"]["elevenlabs_chars"] = state["ledger"].get("elevenlabs_chars", 0) + char_count
        state["audio_files"] = [audio_path]

        heygen_video_output = os.path.join(job_dir, "heygen_avatar.mp4")
        heygen_res = generate_heygen_avatar(
            full_text, audio_path, 
            output_dir=job_dir,
            avatar_id=state.get("avatar_id"),
            avatar_type=state.get("avatar_type"),
            job_id=state.get("job_id")
        )
        
        # Validate return tuple format
        if not heygen_res or not isinstance(heygen_res, tuple) or len(heygen_res) < 2:
             heygen_res = (None, 0)
             
        heygen_video, duration_sec = heygen_res
        
        # INDUSTRIAL LEDGER: Capture duration
        state["ledger"] = state.get("ledger", {})
        state["ledger"]["heygen_seconds"] = state["ledger"].get("heygen_seconds", 0) + duration_sec
        
        if not heygen_video or not os.path.exists(heygen_video):
             raise RuntimeError("HeyGen API produced no video output.")

        state["heygen_video_path"] = heygen_video
        _log_progress(state, "HEYGEN", "Avatar assets generated successfully.", duration=time.time() - start_t)
    except Exception as e:
        _record_error(state, "HEYGEN", f"HeyGen path failed: {e}")
        print(f"   ❌ {state['rendering_errors']}")
        return _run_presentation_fallback(state, "HEYGEN")
    
    return state


def subtitle_node(state: TonyState) -> TonyState:
    """Generate kinetic Insta-style subtitles and overlay them."""
    import copy
    import time
    start_t = time.time()
    state = copy.deepcopy(state)
    _log_progress(state, "SUBTITLE", "Post-Production: Adding kinetic subtitles...")
    
    from subtitle_generator import generate_kinetic_subtitles
    from moviepy.editor import VideoFileClip, AudioFileClip

    video_path = state["heygen_video_path"]
    
    # INDUSTRIAL GUARD: Ensure we have a valid MP4 before attempting MoviePy operations
    if not video_path or not os.path.exists(video_path) or not str(video_path).lower().endswith(".mp4"):
        print(f"   ⚠️  HeyGen video not found or invalid ({video_path}) — skipping subtitles.")
        if video_path and os.path.exists(video_path):
            state["output_path"] = os.path.abspath(video_path)
        return state

    video_clip = None
    try:
        video_clip = VideoFileClip(video_path)
        audio_path = state["audio_files"][0]

        tmp_aud = AudioFileClip(audio_path)
        try:
            audio_dur = tmp_aud.duration
        finally:
            tmp_aud.close()

        # Determine alignment path (sidecar JSON)
        alignment_path = audio_path.replace(".m4a", ".json").replace(".mp3", ".json")
        if not os.path.exists(alignment_path):
            alignment_path = None

        full_text  = " ".join(s["narration_text"] for s in state["scenes"])

        # Apply kinetic styling (Insta Reels style)
        final_clip = generate_kinetic_subtitles(
            video_clip,
            full_text,
            audio_dur,
            style="insta_reels",
            alignment_path=alignment_path,
            audio_path=audio_path  # Enable High-Fidelity Sync
        )

        try:
            output_path = video_path.replace(".mp4", "_subtitled.mp4")
            final_clip.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
            state["output_path"] = os.path.abspath(output_path)
            _log_progress(state, "SUBTITLE", "Kinetic subtitle overlay complete.", duration=time.time() - start_t)
        finally:
            final_clip.close()
    except Exception as e:
        print(f"   ⚠️  Subtitle overlay failed: {e}")
        _log_fallback(state, "SUBTITLE", "use_original_video", str(e), type(e).__name__)
        state["output_path"] = os.path.abspath(video_path)
        state["rendering_errors"] = None
    finally:
        if video_clip is not None:
            video_clip.close()

    return state


def fusion_node(state: TonyState) -> TonyState:
    """Final assembly sentinel — validates output is a real video, not raw audio."""
    import copy
    import time
    start_t = time.time()
    state = copy.deepcopy(state)
    _log_progress(state, "FUSION", "Quality Guard: Finalizing assembly and deployment readiness...")
    
    output = state.get("output_path")
    
    if not output or not os.path.exists(output):
        _record_error(state, "FUSION", "Final production failed — output artifact missing before deploy.")
        _log_progress(state, "FUSION", "Assembly failed — no output.", duration=time.time() - start_t)
        return state
    
    # Guard: Ensure the output is a video, not a raw audio file delivered by a failed pipeline
    ext = os.path.splitext(output)[1].lower()
    if ext in (".mp3", ".m4a", ".wav", ".aac", ".aiff"):
        print(f"   ⚠️ [FUSION] Output is raw audio ({ext}), not a video. Pipeline produced no video.")
        _record_error(state, "FUSION", f"Output is raw audio ({os.path.basename(output)}), not a video — upstream pipeline failed.")
        state["output_path"] = None  # Prevent deploy from shipping raw audio
        _log_progress(state, "FUSION", "Assembly rejected — output was audio, not video.", duration=time.time() - start_t)
        return state
        
    _log_progress(state, "FUSION", "Assembly finalized.", duration=time.time() - start_t)
    return state

def deploy_node(state: TonyState) -> TonyState:
    """Industrial Deployment Sentinel: Unified S3 Sync + Post-Deploy Disk Hygiene."""
    import copy
    import time
    start_t = time.time()
    state = copy.deepcopy(state)
    _log_progress(state, "DEPLOY", "Synchronizing final assets with Production CDN...")
    
    job_id = state.get("job_id")
    output_path = state.get("output_path")
    topic = state.get("topic")
    
    if state.get("rendering_errors"):
        _log_progress(state, "DEPLOY", f"Skipped deploy due to upstream render error: {state['rendering_errors']}", "warning", duration=time.time() - start_t)
        return state

    if not output_path or not os.path.exists(output_path):
        _log_progress(state, "DEPLOY", "Handover Failure: Final video asset not found.", "warning", duration=time.time() - start_t)
        _record_error(state, "DEPLOY", state.get("rendering_errors") or "Deploy blocked: output asset not found.")
        return state
        
    video_url = _upload_to_s3(output_path, topic, job_id)
    state["video_url"] = video_url
    
    if video_url:
        _log_progress(state, "DEPLOY", f"Masterclass published successfully: {video_url}", duration=time.time() - start_t)
    else:
        _log_progress(state, "DEPLOY", "Deployment succeeded with local asset only.", duration=time.time() - start_t)

    # Thumbnail generation
    job_dir = get_job_dir(state)
    try:
        from thumbnail_generator import generate_thumbnail
        thumbnail_path = generate_thumbnail(
            topic=state.get("topic", ""),
            subject=state.get("parsed_facts", {}).get("subject", "unknown"),
            key_points=state.get("parsed_facts", {}).get("key_points", []),
            job_dir=job_dir,
            filename="thumbnail.png"
        )
        thumbnail_url = _upload_to_s3(
            thumbnail_path, 
            state["topic"], 
            job_id
        )
        state["thumbnail_url"] = thumbnail_url
        _log_progress(state, "DEPLOY", f"Thumbnail generated: {thumbnail_url}")
    except Exception as e:
        print(f"⚠️ Thumbnail generation failed: {e}")
        state["thumbnail_url"] = ""

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

def should_research(state: TonyState) -> str:
    """Route to research node if director requested queries, otherwise proceed to vision."""
    if state.get("search_queries") and state.get("research_count", 0) < 3:
        return "research"
    return "vision"

def route_by_mode(state: TonyState) -> str:
    """After vision — branch to one of the 4 paths."""
    mode = (state.get("render_mode") or "").strip().lower()
    if mode == "presentation":
        return "ppt_planner"
    elif mode == "explainer":
        return "explainer"
    elif mode in {"heygen", "user_generated_video", "user_generated", "human_face"}:
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
    
    # Phase 8: Explicit Error Reporting on max retry depletion
    if state.get("rendering_errors") and state["attempt_count"] >= 3:
        # Use the actual Manim/FFmpeg stderr for actionable forensics
        final_err = state["rendering_errors"] or "Max retries reached"
        _record_error(state, "SYSTEM", f"Critical production failure after 3 healer attempts: {final_err}")
        
    return "deploy"

def after_heygen(state: TonyState) -> str:
    """Route to subtitles for normal heygen, or deploy for presentation fallback."""
    # If render_mode was swapped to presentation by _run_presentation_fallback,
    # skip subtitles/fusion and go straight to deploy (the fallback node already produced the video).
    if state.get("render_mode") == "presentation":
        return "deploy"
    return "subtitles"


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

workflow.add_node("research", research_node)

workflow.add_edge("research", "director")
# Conditional routing for Director to either Research or Vision
workflow.add_conditional_edges("director", should_research, {
    "research": "research",
    "vision": "vision"
})

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
workflow.add_conditional_edges("heygen", after_heygen, {
    "subtitles": "subtitles",
    "deploy":    "deploy"
})
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
        "video_type":         "marketing" if args.marketing else "educational",

        "image_paths":        None,

        "heygen_video_path":  None,
        "subtitle_style":     None,

        "search_queries":     None,
        "search_results":     None,
        "knowledge_base":     None,
    })

    print(f"\n🏆 Curtain Call: {args.topic}")
    print(f"   Industrial Video URL: {final.get('video_url')}")
    print(f"   Local Cache Snapshot: {final.get('output_path')}")
