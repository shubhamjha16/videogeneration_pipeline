"""
Notes Pipeline Generator (Pipeline 5)

Generates premium "handwritten infographic" style educational videos:
  1. LLM structures the lesson into a visual notes blueprint
  2. DALL-E 3 (gpt-image-2) renders the infographic as a single high-res image
  3. ElevenLabs generates the narration audio
  4. Ken Burns "scanning zoom" animates the static image synced to audio
  5. Final .mp4 is stitched together

Output: A polished "study notes" video where the camera pans across
a premium whiteboard-style infographic while narration plays.
"""

import os
import time
import math
from pathlib import Path


# ── Notes Image Prompt ────────────────────────────────────────────────────────

NOTES_IMAGE_PROMPT = (
    "Create a premium handwritten-style educational infographic for: {topic}.\n\n"
    "Content to include:\n{content_summary}\n\n"
    "Style requirements:\n"
    "- White or light cream background (like a real notebook page)\n"
    "- Handwritten-style typography with clear hierarchy (large bold headers, smaller body text)\n"
    "- Color-coded sections using pastel highlights (lavender, soft blue, mint green, warm yellow)\n"
    "- Boxed 'Key Points' and 'Pearl' callouts with star icons\n"
    "- Simple hand-drawn flowcharts with rounded boxes and arrows where appropriate\n"
    "- Small diagrams or illustrations relevant to the topic\n"
    "- Clear section numbering (1, 2, 3...)\n"
    "- 'Final Answer' or 'Key Takeaway' box at the bottom\n"
    "- Professional medical/academic study notes aesthetic\n"
    "- All text must be legible and correctly spelled\n"
    "- Layout: dense but organized, like a GoodNotes or Notability page\n"
    "- Aspect ratio: portrait (tall), suitable for vertical scrolling\n"
    "- NO watermarks, NO stock photo elements"
)


# ── LLM: Structure lesson into notes blueprint ───────────────────────────────

def _build_notes_blueprint(scenes: list[dict], topic: str, job_id: str = None) -> str:
    """
    Use the LLM to convert scene narrations into a structured
    notes summary suitable for infographic generation.
    """
    from llm_factory import LLMFactory

    narration_text = "\n".join(
        f"- {s.get('narration_text', '')}" for s in scenes if s.get("narration_text")
    )

    prompt = (
        f"You are creating study notes for the topic: {topic}\n\n"
        f"Here is the full lesson narration:\n{narration_text}\n\n"
        "Convert this into a structured notes blueprint with:\n"
        "1. A clear TITLE\n"
        "2. CONCEPT section (3-5 bullet points)\n"
        "3. KEY DIAGRAM or FLOWCHART description (what boxes and arrows to draw)\n"
        "4. OPTION ANALYSIS if it's an MCQ (A, B, C, D with reasoning)\n"
        "5. KEY POINTS TO REMEMBER (3-5 starred items)\n"
        "6. FINAL ANSWER or TAKEAWAY\n\n"
        "Keep it concise. Use plain text, no markdown formatting.\n"
        "This will be used as input to an image generation model."
    )

    content, usage = LLMFactory.get_completion(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are a medical/academic study notes architect. Output structured plain-text notes.",
        json_mode=False,
        include_usage=True,
        job_id=job_id,
    )

    return content.strip()


# ── Image Generation ──────────────────────────────────────────────────────────

def _generate_notes_image(topic: str, content_summary: str, output_dir: str, job_id: str = None) -> str:
    """Generate the infographic image using DALL-E 3."""
    import config
    from openai import OpenAI
    import base64

    api_key = config.OPENAI_API_KEY
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set — cannot generate notes image.")

    # Ledger the image cost
    try:
        from cost_tracker import LedgerManager
        LedgerManager.record_higgsfield_call(job_id, cost_per_call=0.08)  # DALL-E 3 HD 1024x1792
    except Exception as e:
        print(f"  Failed to log notes image cost: {e}")

    client = OpenAI(api_key=api_key)
    prompt = NOTES_IMAGE_PROMPT.format(topic=topic, content_summary=content_summary[:1500])

    print(f"  [Notes] Generating infographic image for: {topic[:50]}...")

    for attempt in range(3):
        try:
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1792",  # Portrait for vertical scroll
                quality="hd",
                n=1,
                response_format="b64_json",
            )
            break
        except Exception as e:
            if attempt == 2:
                raise
            print(f"  [Notes] Image gen retry ({attempt + 1}/3): {e}")
            time.sleep(2 ** attempt)

    if not response.data:
        raise RuntimeError(f"DALL-E 3 returned no image for notes: {topic}")

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "notes_infographic.png")
    image_bytes = base64.b64decode(response.data[0].b64_json)

    with open(output_path, "wb") as f:
        f.write(image_bytes)

    print(f"  [Notes] Infographic saved: {output_path}")
    return os.path.abspath(output_path)


# ── TTS Audio ─────────────────────────────────────────────────────────────────

def _generate_notes_audio(scenes: list[dict], output_dir: str, job_id: str = None) -> tuple[str, float]:
    """Generate narration audio from scene text."""
    from tts_generator import generate_audio
    from moviepy.editor import AudioFileClip

    full_text = " ".join(s.get("narration_text", "") for s in scenes)
    audio_path, char_count = generate_audio(full_text, 0, output_dir=output_dir, job_id=job_id)

    # Get duration
    clip = AudioFileClip(audio_path)
    try:
        duration = clip.duration
    finally:
        clip.close()

    return audio_path, duration


# ── Ken Burns Scanning Zoom ───────────────────────────────────────────────────

def _apply_ken_burns(image_path: str, audio_path: str, output_path: str, audio_duration: float) -> str:
    """
    Apply a vertical scanning "Ken Burns" effect to the notes image.

    The camera starts at the top of the tall infographic and slowly
    pans downward over the duration of the audio, simulating a
    teacher scrolling through handwritten notes.
    """
    from moviepy.editor import AudioFileClip, ImageClip, CompositeVideoClip
    from PIL import Image

    # Load image dimensions
    img = Image.open(image_path)
    img_w, img_h = img.size
    img.close()

    # Output video dimensions (16:9 landscape viewport)
    out_w, out_h = 1280, 720

    # Scale image so its width fills the viewport
    scale = out_w / img_w
    scaled_w = out_w
    scaled_h = int(img_h * scale)

    # If scaled image is shorter than viewport, just center it (no pan needed)
    if scaled_h <= out_h:
        print("  [Notes] Image too short for scanning. Using static frame.")
        clip = ImageClip(image_path).set_duration(audio_duration).resize((out_w, out_h))
        audio = AudioFileClip(audio_path)
        final = clip.set_audio(audio)
        final.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
        final.close()
        audio.close()
        return output_path

    # Max vertical travel (how far the crop window can move)
    max_y_offset = scaled_h - out_h

    # Create the scanning animation using moviepy
    base_clip = ImageClip(image_path).resize(width=out_w).set_duration(audio_duration)

    def crop_position(t):
        """Return the y-offset for the crop window at time t."""
        # Ease-in-out sigmoid for smooth scanning
        progress = t / audio_duration
        # Smooth S-curve: slow start, steady middle, slow end
        smooth = 0.5 * (1 + math.tanh(6 * (progress - 0.5)))
        y = int(smooth * max_y_offset)
        return y

    # Apply vertical pan via cropping
    def make_frame(t):
        frame = base_clip.get_frame(t)
        y = crop_position(t)
        # Crop a viewport-sized window from the tall image
        return frame[y:y + out_h, :out_w]

    from moviepy.editor import VideoClip
    scanned = VideoClip(make_frame, duration=audio_duration).set_fps(24)

    # Attach audio
    audio = AudioFileClip(audio_path)
    final = scanned.set_audio(audio)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    final.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", logger=None)

    final.close()
    audio.close()
    base_clip.close()

    print(f"  [Notes] Ken Burns video saved: {output_path}")
    return output_path


# ── Main Orchestrator ─────────────────────────────────────────────────────────

def generate_notes_video(
    topic: str,
    scenes: list[dict],
    output_dir: str,
    job_id: str = None,
) -> tuple[str, dict]:
    """
    Full notes pipeline orchestrator.

    Returns:
        (output_path, ledger_dict) where ledger_dict contains usage metrics.
    """
    os.makedirs(output_dir, exist_ok=True)
    ledger = {}

    # 1. Structure the lesson into a notes blueprint via LLM
    print(f"[Notes Pipeline] Step 1/4: Building notes blueprint...")
    blueprint = _build_notes_blueprint(scenes, topic, job_id=job_id)
    ledger["notes_blueprint_chars"] = len(blueprint)

    # 2. Generate the infographic image
    print(f"[Notes Pipeline] Step 2/4: Generating infographic image...")
    image_path = _generate_notes_image(topic, blueprint, output_dir, job_id=job_id)
    ledger["notes_image_generated"] = True

    # 3. Generate narration audio
    print(f"[Notes Pipeline] Step 3/4: Generating narration audio...")
    audio_path, audio_duration = _generate_notes_audio(scenes, output_dir, job_id=job_id)
    ledger["notes_audio_duration"] = audio_duration

    # 4. Apply Ken Burns scanning zoom
    print(f"[Notes Pipeline] Step 4/4: Applying Ken Burns scanning zoom...")
    output_path = os.path.join(output_dir, "notes_video.mp4")
    _apply_ken_burns(image_path, audio_path, output_path, audio_duration)
    ledger["notes_video_duration"] = audio_duration

    print(f"[Notes Pipeline] Complete: {output_path}")
    return output_path, ledger
