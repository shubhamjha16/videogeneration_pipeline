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
    """Use Groq to intelligently split text into presentation slides."""
    from groq import Groq

    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": _SPLIT_PROMPT},
            {"role": "user", "content": f"TOPIC: {topic}\n\nCONTENT:\n{text}"}
        ],
        response_format={"type": "json_object"}
    )

    data = json.loads(response.choices[0].message.content)
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

def _build_slide_text(slide: dict) -> str:
    """
    Convert slide dict to the text format slide_generator expects:
    'Heading. Bullet 1. Bullet 2. Bullet 3.'
    """
    parts = [slide["heading"].rstrip('.')]
    for b in slide.get("bullets", []):
        parts.append(b.rstrip('.'))
    return ". ".join(parts) + "."


def _ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def _image_to_video(image_path: str, audio_path: str, output_path: str) -> bool:
    """Combine a PNG slide + MP3 audio into a video clip using ffmpeg."""
    result = subprocess.run([
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
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"   ❌ ffmpeg error: {result.stderr[-500:]}")
        return False
    return True


def _concat_clips(clip_paths: list[str], output_path: str) -> bool:
    """Concatenate multiple video clips using ffmpeg concat demuxer."""
    list_file = output_path.replace(".mp4", "_list.txt")
    with open(list_file, "w") as f:
        for clip in clip_paths:
            f.write(f"file '{os.path.abspath(clip)}'\n")

    result = subprocess.run([
        _ffmpeg(), "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        output_path
    ], capture_output=True, text=True)

    os.remove(list_file)

    if result.returncode != 0:
        print(f"   ❌ concat error: {result.stderr[-500:]}")
        return False
    return True


# ── Public API ────────────────────────────────────────────────────────────────

def run_ppt_pipeline(
    topic: str,
    text: str,
    output_dir: str = None,
) -> str:
    """
    Generate a doodle-style presentation video.

    Args:
        topic      : Topic name (shown on title slide)
        text       : Raw content text (paragraphs or bullet points)
        output_dir : Output directory (default: output/ppt_<topic>)

    Returns:
        Absolute path to the output MP4
    """
    # ppt_engine is a subfolder — add parent to path for tts_generator
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from ppt_engine.slide_generator import generate_slide_image
    from tts_generator import generate_audio

    safe_topic = topic.lower().replace(" ", "_").replace("/", "_").replace("'", "").replace("'", "")
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

        # Image + audio → clip
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
    return os.path.abspath(final_output)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EaseToLearn PPT Video Generator")
    parser.add_argument("--topic", required=True, help="Topic name")
    parser.add_argument("--text",  required=True, help="Path to text file OR raw text string")
    parser.add_argument("--output", help="Output directory (optional)")
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
    )
    print(f"\n🎬 Final video: {video_path}")
