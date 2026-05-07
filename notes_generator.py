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
    "Make notes of the following topic in format image, and proper notes with "
    "flowchart diagrams such that easy recalling graphic, handwritten kinda font, "
    "heading big, subheading semi big, then para, then flowchart. "
    "FMGE exam style. Proper diagrams well labeled.\n\n"
    "Topic: {topic}\n\n"
    "Content:\n{content_summary}\n\n"
    "Additional style requirements:\n"
    "- White or light cream notebook background\n"
    "- Handwritten-style typography with clear hierarchy\n"
    "- Color-coded sections using pastel highlights (lavender, soft blue, mint green, warm yellow)\n"
    "- Boxed 'Key Points', 'Pearl', and 'Final Answer' callouts with star icons\n"
    "- Hand-drawn flowcharts with rounded boxes and colored arrows\n"
    "- Well-labeled anatomical/clinical diagrams where relevant\n"
    "- Option Analysis section (A, B, C, D) with reasoning for MCQs\n"
    "- Normal Values box if applicable\n"
    "- Key Take-Home Message bar at the bottom\n"
    "- All text must be legible and correctly spelled\n"
    "- Portrait layout, dense but organized like GoodNotes/Notability\n"
    "- NO watermarks, NO stock photos"
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
                model="gpt-image-2",
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


# ── Sequential Reveal Animation Engine ────────────────────────────────────────

def _compute_section_breakpoints(num_sections: int) -> list[float]:
    """
    Divide the image into evenly-spaced vertical sections.
    Returns a list of fractional breakpoints [0.0, 0.2, 0.4, ..., 1.0].
    """
    return [i / num_sections for i in range(num_sections + 1)]


def _apply_animated_reveal(
    image_path: str,
    audio_path: str,
    output_path: str,
    audio_duration: float,
    num_sections: int = 5,
) -> str:
    """
    Apply a 'Sequential Reveal' animation to the notes infographic.

    Instead of a simple scroll, each section of the infographic is
    progressively unveiled with a smooth wipe-down transition:
      - Already-revealed sections: fully visible
      - Currently revealing section: wipe-down from top to bottom
      - Unrevealed sections: covered with a blurred/foggy overlay
      - Camera auto-pans to follow the reveal point

    Args:
        image_path: Path to the tall portrait infographic PNG.
        audio_path: Path to the narration audio file.
        output_path: Where to save the final MP4.
        audio_duration: Duration of the audio in seconds.
        num_sections: Number of sections to divide the image into.
    """
    import numpy as np
    from moviepy.editor import AudioFileClip, VideoClip
    from PIL import Image, ImageFilter

    # Load and scale the image
    img_pil = Image.open(image_path).convert("RGB")
    img_w, img_h = img_pil.size

    # Output video dimensions (16:9 landscape viewport)
    out_w, out_h = 1280, 720

    # Scale image width to fill viewport
    scale = out_w / img_w
    scaled_w = out_w
    scaled_h = int(img_h * scale)
    img_pil = img_pil.resize((scaled_w, scaled_h), Image.LANCZOS)

    # Pre-render: full image as numpy array
    img_full = np.array(img_pil)

    # Pre-render: blurred/foggy version (unrevealed sections)
    img_blurred_pil = img_pil.filter(ImageFilter.GaussianBlur(radius=18))
    # Add a semi-transparent cream overlay to the blurred version
    cream_overlay = Image.new("RGB", (scaled_w, scaled_h), (255, 253, 245))
    img_foggy_pil = Image.blend(img_blurred_pil, cream_overlay, alpha=0.55)
    img_foggy = np.array(img_foggy_pil)

    # Section breakpoints (fractional positions on the image height)
    breakpoints = _compute_section_breakpoints(num_sections)

    # Time allocated per section
    time_per_section = audio_duration / num_sections

    # Transition duration (wipe effect within each section)
    transition_dur = min(1.5, time_per_section * 0.4)

    def get_reveal_mask(t):
        """
        For a given time t, compute a per-pixel alpha mask (0.0 to 1.0)
        indicating how much of each row is revealed.
        """
        mask = np.zeros(scaled_h, dtype=np.float32)

        for i in range(num_sections):
            section_start_time = i * time_per_section
            section_top = int(breakpoints[i] * scaled_h)
            section_bot = int(breakpoints[i + 1] * scaled_h)
            section_height = section_bot - section_top

            if t >= section_start_time + transition_dur:
                # Fully revealed
                mask[section_top:section_bot] = 1.0
            elif t > section_start_time:
                # Currently revealing — wipe down
                progress = (t - section_start_time) / transition_dur
                # Smooth ease-in-out
                smooth = progress * progress * (3 - 2 * progress)
                reveal_rows = int(smooth * section_height)
                mask[section_top:section_top + reveal_rows] = 1.0
            # else: not yet revealed (stays 0.0)

        return mask

    def get_camera_y(t):
        """Camera follows the current reveal point with smooth easing."""
        # Which section is currently being revealed?
        current_section = min(int(t / time_per_section), num_sections - 1)

        # Target: center the viewport on the middle of the current section
        section_mid = int((breakpoints[current_section] + breakpoints[current_section + 1]) / 2 * scaled_h)
        target_y = max(0, min(section_mid - out_h // 2, scaled_h - out_h))

        # For smooth transitions, blend with previous target
        if current_section > 0:
            prev_mid = int((breakpoints[current_section - 1] + breakpoints[current_section]) / 2 * scaled_h)
            prev_y = max(0, min(prev_mid - out_h // 2, scaled_h - out_h))

            # Interpolate between previous and current target
            section_progress = (t - current_section * time_per_section) / time_per_section
            ease = section_progress * section_progress * (3 - 2 * section_progress)
            target_y = int(prev_y + (target_y - prev_y) * ease)

        return target_y

    # Highlight glow color (warm golden yellow, subtle)
    glow_color = np.array([255, 235, 130], dtype=np.uint8)

    def make_frame(t):
        """Compose each video frame with reveal mask + camera pan."""
        # Get the reveal mask
        mask = get_reveal_mask(t)

        # Blend full image and foggy image using the mask
        mask_3d = mask[:, np.newaxis, np.newaxis]  # (H, 1, 1) for broadcasting
        frame = (img_full * mask_3d + img_foggy * (1.0 - mask_3d)).astype(np.uint8)

        # Add subtle highlight glow at the reveal boundary
        current_section = min(int(t / time_per_section), num_sections - 1)
        section_start_time = current_section * time_per_section
        if t < section_start_time + transition_dur and t >= section_start_time:
            progress = (t - section_start_time) / transition_dur
            smooth = progress * progress * (3 - 2 * progress)
            section_top = int(breakpoints[current_section] * scaled_h)
            section_height = int((breakpoints[current_section + 1] - breakpoints[current_section]) * scaled_h)
            glow_row = section_top + int(smooth * section_height)
            # Draw a 4px warm glow line at the reveal edge
            glow_start = max(0, glow_row - 2)
            glow_end = min(scaled_h, glow_row + 2)
            glow_alpha = 0.35
            for row in range(glow_start, glow_end):
                frame[row, :] = (
                    frame[row, :] * (1 - glow_alpha) + glow_color * glow_alpha
                ).astype(np.uint8)

        # Camera pan: crop viewport from the full-height composed frame
        cam_y = get_camera_y(t)
        viewport = frame[cam_y:cam_y + out_h, :out_w]

        # Safety: pad if viewport is smaller than expected
        if viewport.shape[0] < out_h:
            pad = np.ones((out_h - viewport.shape[0], out_w, 3), dtype=np.uint8) * 255
            viewport = np.vstack([viewport, pad])

        return viewport

    # Build the video
    video = VideoClip(make_frame, duration=audio_duration).set_fps(24)
    audio = AudioFileClip(audio_path)
    final = video.set_audio(audio)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    final.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", logger=None)

    final.close()
    audio.close()

    print(f"  [Notes] Animated reveal video saved: {output_path}")
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

    # 4. Apply animated sequential reveal
    print(f"[Notes Pipeline] Step 4/4: Applying animated sequential reveal...")
    output_path = os.path.join(output_dir, "notes_video.mp4")

    # Use scene count to determine section count (min 3, max 8)
    num_sections = max(3, min(8, len(scenes)))
    _apply_animated_reveal(image_path, audio_path, output_path, audio_duration, num_sections)
    ledger["notes_video_duration"] = audio_duration
    ledger["notes_sections"] = num_sections

    print(f"[Notes Pipeline] Complete: {output_path}")
    return output_path, ledger
