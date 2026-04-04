"""
Autonomous LangGraph Pipeline — Team Tony
Orchestrates the full video generation flow:

  director_node   : parse Tony AI HTML → Claude director → scenes + render_mode
  vision_node     : Gemini Imagen → concept diagram PNG
  architect_node  : template_renderer → deterministic Manim script
  supervisor_node : render Manim → stitch audio → S3 upload

State flows through each node. On Manim render failure,
the supervisor retries up to 3 times via should_continue().
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
    """Resolve ffmpeg path — venv binary first, then system."""
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


# ── State ─────────────────────────────────────────────────────────────────────

class TonyState(TypedDict):
    # ── Input ──────────────────────────────────────────
    raw_input:   str          # Raw HTML from Tony AI backend
    topic:       str          # Topic name (from API caller)

    # ── After director_node ────────────────────────────
    parsed_facts:  Optional[dict]   # output of html_parser
    render_mode:   Optional[str]    # "manim" | "presentation" | "human_face"
    scenes:        Optional[list]   # list of Scene dicts from director_agent

    # ── After vision_node ──────────────────────────────
    image_path:  Optional[str]      # abs path to generated PNG

    # ── After architect_node ──────────────────────────
    manim_script_path: Optional[str]

    # ── After supervisor_node ─────────────────────────
    output_path:  Optional[str]     # local mp4 before upload
    video_url:    Optional[str]     # S3 URL returned to Spring Boot

    # ── Control ────────────────────────────────────────
    rendering_errors: Optional[str]
    attempt_count:    int


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
    state["render_mode"] = director_output.render_mode
    state["scenes"] = [s.model_dump() for s in director_output.scenes]

    print(f"   Render mode: {director_output.render_mode} | Scenes: {len(director_output.scenes)}")
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
    """Convert scenes into a Manim script (deterministic templates) or run presentation pipeline."""
    print(f"📐 [Architect] Building render script — mode: {state['render_mode']}")

    job_dir = os.path.join("output", f"job_{state['topic'].lower().replace(' ', '_')}")
    os.makedirs(job_dir, exist_ok=True)

    if state["render_mode"] == "presentation":
        # Hand off to existing tony_pipeline — no Manim needed
        from tony_pipeline import run_tony_pipeline
        from tts_generator import generate_audio

        narration = " ".join(s["narration_text"] for s in state["scenes"])
        output = run_tony_pipeline(
            narration,
            topic_name=state["topic"],
            output_dir=job_dir,
        )
        state["output_path"]       = output
        state["manim_script_path"] = None
        return state

    # manim mode — call template_renderer
    from template_renderer import build_manim_script

    script_path = os.path.join(job_dir, "scene_script.py")
    build_manim_script(
        scenes=state["scenes"],
        image_path=state.get("image_path"),
        topic=state["topic"],
        output_path=script_path,
    )
    state["manim_script_path"] = script_path
    print(f"   Script written: {script_path}")
    return state


# ── Node 4: Supervisor ────────────────────────────────────────────────────────

def supervisor_node(state: TonyState) -> TonyState:
    """Render Manim → generate TTS per scene → stitch with ffmpeg → upload to S3."""
    print(f"🔍 [Supervisor] Rendering — attempt {state['attempt_count'] + 1}")

    # Presentation mode: output_path already set by architect_node
    if state["render_mode"] == "presentation":
        if state.get("output_path") and os.path.exists(state["output_path"]):
            state["video_url"]        = _upload_to_s3(state["output_path"], state["topic"])
            state["rendering_errors"] = None
        else:
            state["rendering_errors"] = "Presentation pipeline produced no output"
        return state

    job_dir     = os.path.dirname(state["manim_script_path"])
    script_path = state["manim_script_path"]
    topic_safe  = state["topic"].replace(" ", "").replace("-", "")

    # ── 1. Render Manim ───────────────────────────────
    print("   Rendering Manim animation...")
    render_result = subprocess.run(
        ["./venv/bin/manim", "-ql", script_path, "EaseToLearnScene", "--media_dir", job_dir],
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

    # ── 2. Generate TTS per scene ─────────────────────
    print("   Generating narration audio...")
    from tts_generator import generate_audio
    from moviepy.editor import AudioFileClip, concatenate_audioclips

    audio_files = []
    for i, scene in enumerate(state["scenes"]):
        audio_path = generate_audio(scene["narration_text"], i, output_dir=job_dir)
        audio_files.append(audio_path)

    # Concatenate all scene audio into one track
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
        state["attempt_count"] += 1
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

    state["attempt_count"] += 1
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


# ── Router ────────────────────────────────────────────────────────────────────

def should_continue(state: TonyState) -> str:
    """Route to healer on failure, up to 3 times."""
    if state.get("rendering_errors") and state["attempt_count"] < 3:
        print(f"⚠️  Render error — routing to healer (attempt {state['attempt_count']})")
        return "healer"
    return END


# ── Graph ─────────────────────────────────────────────────────────────────────

workflow = StateGraph(TonyState)

workflow.add_node("director",   director_node)
workflow.add_node("vision",     vision_node)
workflow.add_node("architect",  architect_node)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("healer",     healer_node)

workflow.set_entry_point("director")
workflow.add_edge("director",  "vision")
workflow.add_edge("vision",    "architect")
workflow.add_edge("architect", "supervisor")
workflow.add_edge("healer",    "supervisor")
workflow.add_conditional_edges("supervisor", should_continue)

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
        "raw_input":    html,
        "topic":        topic,
        "attempt_count": 0,
        # optional fields start as None
        "parsed_facts": None, "render_mode": None, "scenes": None,
        "image_path": None, "manim_script_path": None,
        "output_path": None, "video_url": None, "rendering_errors": None,
    })

    print(f"\n🏆 Done!")
    print(f"   Video URL : {final.get('video_url')}")
    print(f"   Local path: {final.get('output_path')}")
