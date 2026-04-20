"""
PPT Pipeline — Doodle-style presentation video generator.

Separate from the Manim/Tony AI pipeline. Used for:
  - Marketing videos (EaseToLearn feature explainers)
  - Concept theory videos (English, UPSC, MBA, etc.)
  - Any text-heavy content that doesn't need math animations

Flow:
  topic + raw text
      ↓
  Groq — split into slides (heading + bullets + narration per slide)
      ↓
  slide_generator — 1920x1080 doodle PNG per slide
      ↓
  tts_generator — MP3 per slide
      ↓
  ffmpeg — image + audio → clip per slide
      ↓
  ffmpeg — concatenate all clips → final MP4

Entry points:
  CLI  : python ppt_pipeline.py --topic "Newton Laws" --text newton.txt
  Code : from ppt_pipeline import run_ppt_pipeline
"""

import os
import sys
import json
import subprocess
import argparse
import textwrap
from dotenv import load_dotenv

load_dotenv()


# ── Slide splitter (Groq) ─────────────────────────────────────────────────────

_SPLIT_PROMPT = """You are a senior presentation director for an educational video platform.

Your job: read the content deeply, understand its nature, then design the best possible presentation for IT — not a generic template.

STEP 1 — Analyze the content before deciding anything:
- Is this content definition-heavy? comparison-heavy? process-heavy? fact-heavy?
- What is the single most important thing a student must remember?
- What would confuse a student most — and how to clarify it visually?
- Does this content have a natural narrative arc, or is it a list of facts?
- Break the content into 2-4 logical CHAPTERS (not just topics — actual dramatic narrative chapters)

STEP 2 — Design the presentation based on what YOU found:
- MANDATORY: Start each chapter with a "chaos_chapter" slide (Chapter 1, Chapter 2, Chapter 3...)
- Each chapter then has 1-2 content slides beneath it
- Total slides: 6 to 10 (more chapters = more drama = better retention)
- Each slide must earn its place — if a layout doesn't serve the content, don't use it
- The arc should feel like a teacher explaining, not a template being filled
- End with a "summary" slide

STRUCTURE EXAMPLE (follow this pattern):
  chaos_chapter (Chapter 1) → content slide(s) for chapter 1
  chaos_chapter (Chapter 2) → content slide(s) for chapter 2
  chaos_chapter (Chapter 3) → content slide(s) for chapter 3
  summary

AVAILABLE LAYOUTS:

"chaos_chapter" — High impact chapter intro mimicking the EaseToLearn thumbnail style
data: {"number": "1", "title": str, "subtitle": str}
REQUIRED at the start of every chapter — use it 2-4 times with incrementing numbers.

"title_card" — Generic Opening
data: {"title": str, "subtitle": str}

"bullets" — Heading + 2-4 points
data: {"heading": str, "bullets": [str, ...]}
Best when: listing distinct types, features, or examples

"big_statement" — One bold sentence, centered
data: {"statement": str, "context": str}
Best when: the content has a core truth or definition that must land hard

"steps" — Numbered sequence
data: {"heading": str, "steps": [str, ...]}
Best when: content is genuinely a process or ordered sequence

"two_column" — Side by side comparison
data: {"heading": str, "left_title": str, "left_points": [str], "right_title": str, "right_points": [str]}
Best when: content naturally has two sides — contrast, comparison, before/after

"key_highlight" — One critical fact, large on dark background
data: {"label": str, "fact": str, "detail": str}
Best when: there is ONE thing that must be memorized — a rule, number, or formula

"summary" — Closing checkmarks
data: {"heading": "Key Takeaways", "points": [str, ...]}
Best for closing — but only if you have genuine takeaways worth repeating

"timeline" — Horizontal timeline with dated events
data: {"heading": str, "events": [{"date": str, "description": str}, ...]}
Best when: content has a chronological sequence — history, wars, company milestones (3-5 events)

"quote_card" — Large centered quote with attribution
data: {"quote": str, "attribution": str}
Best when: there is one powerful sentence worth framing — a famous saying, a bold claim, a shocking stat

"stats_dashboard" — 3-4 big numbers in boxes side by side
data: {"heading": str, "stats": [{"value": str, "label": str}, ...]}
Best when: content is data-heavy — revenue, users, percentages, comparisons

"definition_card" — Term + definition + example
data: {"term": str, "definition": str, "example": str}
Best when: a key concept needs to be formally defined — legal terms, medical terms, technical jargon

"before_after" — Two-panel contrast (red vs green)
data: {"heading": str, "before_title": str, "before_points": [str], "after_title": str, "after_points": [str]}
Best when: showing transformation — old vs new, problem vs solution, without vs with

"callout_box" — Warning/tip/note/important box with icon
data: {"type": "tip"|"warning"|"note"|"important", "heading": str, "body": str}
Best when: there is ONE critical thing the viewer must not miss — a warning, a pro tip, a common mistake

"ranking_list" — Numbered top-3 to top-5 list with medal badges
data: {"heading": str, "items": [{"label": str, "detail": str}, ...]}
Best when: content is a ranking, leaderboard, or ordered comparison — top movies, best strategies, most common mistakes

"image_hero" — Cinematic dark full-frame slide with large title + tagline
data: {"title": str, "tagline": str, "context": str}
Best when: you need a dramatic emotional moment — opening a new act, revealing a big idea, a "this changed everything" moment

NARRATION RULES:
- Narration is what the teacher SAYS while this slide is shown
- Must add insight beyond what is written — examples, analogies, why it matters
- Conversational tone — "notice that", "think of it this way", "here is the trick"
- 1-3 sentences only

Return valid JSON only — no explanation, no markdown:
{
  "slides": [
    {"layout": "...", "data": {...}, "narration": "..."},
    ...
  ]
}"""


def _split_into_slides(topic: str, text: str) -> list[dict]:
    """Use configured LLM to intelligently split text into presentation slides."""
    from llm_factory import LLMFactory, clean_llm_json

    content = LLMFactory.get_completion(
        messages=[
            {"role": "user", "content": f"TOPIC: {topic}\n\nCONTENT:\n{text}"}
        ],
        system_prompt=_SPLIT_PROMPT,
        json_mode=True
    )

    data = clean_llm_json(content)
    slides = data.get("slides", [])
    print(f"   Groq planned {len(slides)} slides:")
    for i, s in enumerate(slides):
        print(f"     {i+1}. [{s.get('layout','?')}] {s.get('data',{}).get('title') or s.get('data',{}).get('heading') or s.get('data',{}).get('statement','')[:40]}")
    return slides


def _fallback_split(topic: str, text: str) -> list[dict]:
    """Rule-based fallback if Groq fails — split on sentences."""
    import re
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 20]

    slides = [{"heading": topic, "bullets": sentences[:3], "narration": sentences[0] if sentences else topic}]

    chunk_size = 3
    for i in range(0, len(sentences[3:]), chunk_size):
        chunk = sentences[3 + i: 3 + i + chunk_size]
        if chunk:
            slides.append({
                "heading": f"Part {len(slides)}",
                "bullets": chunk,
                "narration": " ".join(chunk)
            })

    slides.append({
        "heading": "Key Takeaways",
        "bullets": sentences[-3:] if len(sentences) >= 3 else sentences,
        "narration": "Let us quickly recap what we covered today."
    })

    return slides[:8]


# ── Video builder ─────────────────────────────────────────────────────────────

def _ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def _run_command_with_group_cleanup(args: list, timeout: int) -> subprocess.CompletedProcess:
    """Industrial Sentinel: Run a command in a process group and kill the entire group on timeout."""
    import signal
    import os
    
    # start_new_session=True makes this the leader of a new process group.
    # This ensures that killing the group kills all descendants.
    proc = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
        text=True, env=os.environ, start_new_session=True
    )
    
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, args, output=stdout, stderr=stderr)
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


def _image_to_video(image_path: str, audio_path: str, output_path: str) -> bool:
    """Combine a PNG slide + MP3 audio into a video clip using ffmpeg."""
    _run_command_with_group_cleanup([
        _ffmpeg(), "-y",
        "-loop", "1",
        "-i", image_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-preset", "veryfast",
        output_path
    ], timeout=300)
    return True




def _concat_clips(clip_paths: list[str], output_path: str) -> bool:
    """Concatenate multiple video clips using ffmpeg concat demuxer."""
    list_file = output_path.replace(".mp4", "_list.txt")
    with open(list_file, "w") as f:
        for clip in clip_paths:
            f.write(f"file '{os.path.abspath(clip)}'\n")

    tmp_output = output_path + ".tmp"
    success = True
    try:
        _run_command_with_group_cleanup([
            _ffmpeg(), "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            "-f", "mp4",
            tmp_output
        ], timeout=600)
        os.replace(tmp_output, output_path)


    except subprocess.CalledProcessError as e:
        print(f"❌ _concat_clips Failed: {e.stderr}")
        success = False
    finally:
        if os.path.exists(list_file):
            os.remove(list_file)
        if os.path.exists(tmp_output):
            os.remove(tmp_output)
    return success


# ── Public API ────────────────────────────────────────────────────────────────

def run_ppt_pipeline(
    topic: str,
    text: str,
    output_dir: str = None,
    with_avatar: bool = False,
) -> str:
    """
    Generate a doodle-style presentation video.

    Args:
        topic       : Topic name (shown on title slide)
        text        : Raw content text (paragraphs or bullet points)
        output_dir  : Output directory (default: output/ppt_<topic>)
        with_avatar : Composite an animated avatar in the bottom-right corner

    Returns:
        Absolute path to the output MP4
    """
    # ppt_engine is a subfolder — add parent to path for tts_generator
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from ppt_engine.slide_generator import generate_slide_image
    from tts_generator import generate_audio

    import re
    # Industrial Sentinel: Ultra-hardened sanitization matches S3/Imagen paths
    safe_topic = re.sub(r'[^a-zA-Z0-9_\-]', '_', topic.lower().strip())
    safe_topic = re.sub(r'_+', '_', safe_topic)[:50]


    job_dir = output_dir or os.path.join("output", f"ppt_{safe_topic}")
    os.makedirs(job_dir, exist_ok=True)

    print(f"\n🎨 [PPT Pipeline] Topic: {topic}")
    print(f"   Output dir: {job_dir}")

    # ── 1. Split into slides ───────────────────────────────────────────────────
    print("   Splitting content into slides...")
    try:
        slides = _split_into_slides(topic, text)
    except Exception as e:
        print(f"   ⚠️  Groq split failed: {e} — using rule-based fallback")
        slides = _fallback_split(topic, text)

    if not slides:
        raise ValueError("No slides generated — check input text")

    # ── 2. Generate slide images + TTS per slide ───────────────────────────────
    print(f"   Generating {len(slides)} slides + audio...")
    clip_paths = []

    for i, slide in enumerate(slides):
        layout        = slide.get("layout", "bullets")
        layout_data   = slide.get("data", {})
        narration_text = slide.get("narration", "")

        # Fallback text for old format compatibility
        slide_text = layout_data.get("heading") or layout_data.get("title") or layout_data.get("statement") or topic

        # Slide image with layout
        slide_img = generate_slide_image(
            slide_text, i, output_dir=job_dir,
            narration=narration_text,
            layout=layout,
            layout_data=layout_data,
        )

        # TTS audio
        audio_path = generate_audio(narration_text, i, output_dir=job_dir)

        # Avatar overlay (optional)
        if with_avatar:
            from avatar_generator import generate_avatar_video
            from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip
            from moviepy.video.fx.all import loop as fx_loop

            # Slide + audio → base clip
            base_path = os.path.join(job_dir, f"base_{i:02d}.mp4")
            _image_to_video(slide_img, audio_path, base_path)

            avatar_path = generate_avatar_video(
                narration_text, audio_path, i,
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

            clip_path = os.path.join(job_dir, f"clip_{i:02d}.mp4")
            try:
                composite.write_videofile(clip_path, fps=24, codec="libx264", logger=None)
            finally:
                composite.close()
                base_clip.close()
                raw_avatar.close()
                avatar_clip.close()
                av_resized.close()
            success = os.path.exists(clip_path)
        else:
            # Image + audio → clip (fast ffmpeg path)
            clip_path = os.path.join(job_dir, f"clip_{i:02d}.mp4")
            success = _image_to_video(slide_img, audio_path, clip_path)

        if success:
            clip_paths.append(clip_path)
            print(f"   ✅ Slide {i+1}/{len(slides)}: {layout_data.get('title') or layout_data.get('heading') or layout}")
        else:
            print(f"   ⚠️  Slide {i+1} failed — skipping")

    if not clip_paths:
        raise RuntimeError("All slides failed to render")

    # ── 3. Concatenate all clips ───────────────────────────────────────────────
    print("   Stitching clips into final video...")
    final_output = os.path.join(job_dir, f"{safe_topic}_presentation.mp4")
    success = _concat_clips(clip_paths, final_output)

    if not success:
        raise RuntimeError("Final concat failed")

    print(f"\n✅ PPT video done: {final_output}")
    print(f"   Slides: {len(clip_paths)} | Topic: {topic}")

    # ── 4. Cleanup temporary clips ─────────────────────────────────────────────
    import shutil
    try:
        for clip in clip_paths:
            if os.path.exists(clip):
                os.remove(clip)
        # Also clean up any 'base_' clips from avatar path
        for f in os.listdir(job_dir):
            if f.startswith("base_") and f.endswith(".mp4"):
                os.remove(os.path.join(job_dir, f))
    except Exception as e:
        print(f"   ⚠️ Cleanup warning: {e}")

    return os.path.abspath(final_output)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EaseToLearn PPT Video Generator")
    parser.add_argument("--topic",       required=True, help="Topic name")
    parser.add_argument("--text",        required=True, help="Path to text file OR raw text string")
    parser.add_argument("--output",      help="Output directory (optional)")
    parser.add_argument("--with-avatar", action="store_true", help="Add animated avatar overlay")
    args = parser.parse_args()

    # Support both file path and inline text
    if os.path.exists(args.text):
        with open(args.text) as f:
            content = f.read()
    else:
        content = args.text

    video_path = run_ppt_pipeline(
        topic=args.topic,
        text=content,
        output_dir=args.output,
        with_avatar=args.with_avatar,
    )
    print(f"\n🎬 Final video: {video_path}")
