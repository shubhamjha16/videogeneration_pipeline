"""
Image Generator gpt image 2
Generates educational diagrams for concept phase of the video.

Subject-aware prompt engineering:
  medical   → clinical anatomical illustration
  physics   → scientific graph / diagram
  maths     → geometric / visual math diagram
  chemistry → molecular / atomic structure
  upsc      → historical map / infographic style
  english   → clean typography-based visual
  default   → educational infographic
"""

import os
import base64
import re
from pathlib import Path
import config
from openai import OpenAI


# ── Prompt templates per subject ──────────────────────────────────────────────

_PROMPT_TEMPLATES = {
    "medical": (
        "Clinical educational illustration of {topic}. "
        "Dark background (#1a1a2e), anatomical diagram style, "
        "clearly labeled with arrows pointing to key structures, "
        "professional medical textbook quality, vibrant accent colors, "
        "no watermarks, no text overlays except anatomical labels."
    ),
    "physics": (
        "Scientific educational diagram of {topic}. "
        "Clean dark background, graph or diagram style, "
        "labeled axes if applicable, arrows showing direction/force/motion, "
        "bright color coding for different elements, "
        "physics textbook illustration quality, no watermarks."
    ),
    "maths": (
        "Mathematical educational visualization of {topic}. "
        "Dark background, geometric or graphical representation, "
        "clearly marked points and curves, color-coded regions, "
        "clean and minimal style like 3Blue1Brown, no watermarks."
    ),
    "chemistry": (
        "Chemistry educational diagram of {topic}. "
        "Dark background, molecular or atomic structure illustration, "
        "color-coded atoms/bonds/orbitals, clear labels, "
        "professional chemistry textbook quality, no watermarks."
    ),
    "upsc": (
        "Educational infographic about {topic} for Indian competitive exams. "
        "Clean dark background, structured layout with icons and arrows, "
        "key facts highlighted, map or timeline if relevant, "
        "professional government exam study material style, no watermarks."
    ),
    "english": (
        "Educational visual about {topic} grammar or language concept. "
        "Clean dark background, clear typography-based diagram, "
        "color-coded sentence structures or rule examples, "
        "minimal and clear, no watermarks."
    ),
    "mba": (
        "Business educational diagram of {topic}. "
        "Dark professional background, flowchart or framework style, "
        "clean boxes and arrows, color-coded decision points, "
        "MBA case study illustration quality, no watermarks."
    ),
    "explainer_metaphor": (
        "Cinematic educational metaphor for {topic}. "
        "High-fidelity 3D render, dark atmospheric background, "
        "vibrant colors, clean and professional, no watermarks."
    ),
    "whiteboard_doodle": (
        "A premium, high-fidelity educational presentation slide explaining {topic}. "
        "The slide design has a modern, clean academic aesthetic. "
        "The background is a beautiful solid teal or a muted off-white color with a subtle, clean grid pattern. "
        "The layout is highly structured and organized: on the left side, there is a giant, bold, stylized numeral/section marker (like '1', '2', or '3') or a large, high-fidelity textbook illustration. "
        "On the right side, there is a clean white rectangular content card with rounded corners overlaying the background, featuring large, clean bold typography for the titles and subtitles, and elegant academic text in a highly legible sans-serif font. "
        "The slide is enriched with a detailed, professional-grade sketched illustration (such as a textbook-quality clinical anatomical diagram, a physics wave, gears, or complex scientific models depending on the topic) with clean black outlines and vibrant accent colors. "
        "Include dynamic guiding elements like hand-drawn arrow indicators or highlighted boxes with a soft yellow background. "
        "No watermark, no generic stock photo placeholders, extremely high resolution, professional educational graphics, wowed visual design."
    ),
    "counting_item": (
        "A single, high-quality 3D stylized {topic} isolated on a dark background. "
        "Vibrant colors, glossy finish, professional render style similar to premium 3D emojis, "
        "centered, no distractions, no watermarks."
    ),
    "default": (
        "Educational diagram explaining {topic}. "
        "Dark background (#1a1a2e), clear visual explanation, "
        "arrows and labels, professional illustration quality, "
        "suitable for competitive exam preparation, no watermarks."
    ),
}


def _draw_whiteboard_fallback(prompt: str, output_path: str, size_str: str = "1024x1024"):
    """Premium offline visual generator fallback when DALL-E 3 fails."""
    import re
    from PIL import Image, ImageDraw, ImageFont

    try:
        w, h = map(int, size_str.split("x"))
    except:
        w, h = 1024, 1024

    # Create off-white whiteboard canvas
    img = Image.new("RGB", (w, h), "#FAFAFA")
    draw = ImageDraw.Draw(img)

    # Draw nice grid lines (whiteboard feel)
    grid_spacing = 40
    for x in range(0, w, grid_spacing):
        draw.line([(x, 0), (x, h)], fill="#EEEEEE", width=1)
    for y in range(0, h, grid_spacing):
        draw.line([(0, y), (w, y)], fill="#EEEEEE", width=1)

    # Parse key elements
    title = "Educational Slide"
    subtitle = ""
    bullets = []
    objects = []

    title_match = re.search(r"Title:\s*(.*?)(?=\n|$)", prompt, re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()
    
    subtitle_match = re.search(r"Subtitle:\s*(.*?)(?=\n|$)", prompt, re.IGNORECASE)
    if subtitle_match:
        subtitle = subtitle_match.group(1).strip()

    bullets_match = re.search(r"Key Points:\s*(.*?)(?=\n|$)", prompt, re.IGNORECASE)
    if bullets_match:
        bullets_raw = bullets_match.group(1).strip()
        if "," in bullets_raw and "\n" not in bullets_raw:
            bullets = [b.strip() for b in bullets_raw.split(",")]
        else:
            bullets = [b.strip() for b in bullets_raw.split("\n")]
    else:
        lines = [l.strip() for l in prompt.split("\n") if l.strip()]
        bullets = [l for l in lines if not l.startswith("Title:") and not l.startswith("Subtitle:")]

    # Load nice clean font
    def get_font(font_size, bold=False):
        paths = []
        if bold:
            paths = [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/Library/Fonts/Arial Bold.ttf",
                "/System/Library/Fonts/HelveticaNeue.dfont",
            ]
        else:
            paths = [
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/Library/Fonts/Arial.ttf",
                "/System/Library/Fonts/Helvetica.dfont",
            ]
        for p in paths:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, font_size)
                except:
                    pass
        return ImageFont.load_default()

    font_title = get_font(40, bold=True)
    font_subtitle = get_font(24, bold=False)
    font_body = get_font(20, bold=False)

    # Draw border frame
    draw.rounded_rectangle([20, 20, w - 20, h - 20], radius=15, outline="#0D7A7F", width=4)

    # Draw title block
    draw.rounded_rectangle([40, 40, w - 40, 140], radius=10, fill="#E6F2F2", outline="#0D7A7F", width=2)
    draw.text((60, 65), title, fill="#1E1E1E", font=font_title)

    current_y = 160
    if subtitle:
        draw.text((60, current_y), subtitle, fill="#555555", font=font_subtitle)
        current_y += 50

    # Word wrapping
    def wrap_text(text, font, max_width):
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            test_line = " ".join(current_line + [word])
            try:
                tw = draw.textlength(test_line, font=font)
            except:
                tw = len(test_line) * (font.size * 0.6)
            if tw <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))
        return lines

    # Draw bullet points
    for bullet in bullets:
        if not bullet: continue
        bullet_lines = wrap_text(bullet, font_body, w - 160)
        
        # draw a premium filled bullet dot
        draw.ellipse([60, current_y + 6, 72, current_y + 18], fill="#0D7A7F", outline="#0D7A7F")
        
        for line in bullet_lines:
            draw.text((90, current_y), line, fill="#2E2E2E", font=font_body)
            current_y += 30
        current_y += 15

    # Decorative whiteboard doodle element on bottom right
    doodle_box = [w - 180, h - 180, w - 50, h - 50]
    draw.rounded_rectangle(doodle_box, radius=8, outline="#0D7A7F", width=2)
    draw.text((w - 165, h - 150), "INFO", fill="#0D7A7F", font=get_font(28, bold=True))
    draw.line([(w - 180, h - 110), (w - 50, h - 110)], fill="#0D7A7F", width=2)
    draw.text((w - 165, h - 100), "Doodle", fill="#555555", font=get_font(18, bold=False))

    img.save(output_path)
    print(f"🎨 Safe offline whiteboard infographic saved to: {output_path}")


_DALLE_FAILED = False

def generate_concept_image(
    topic: str,
    subject: str = "default",
    output_dir: str = ".",
    filename: str = None,
    job_id: str = None,
) -> str:
    """
    Generate an educational diagram using OpenAI gpt-image-2.
    """
    global _DALLE_FAILED

    # Same subject-aware prompts you already have
    template = _PROMPT_TEMPLATES.get(subject, _PROMPT_TEMPLATES["default"])
    prompt = template.format(topic=topic)

    # Safe clean name preparation
    os.makedirs(output_dir, exist_ok=True)
    safe_name = filename or (
        re.sub(r'[^a-zA-Z0-9_\-]', '_', topic.lower().strip())[:50]
        + "_diagram.png"
    )
    output_path = os.path.join(output_dir, safe_name)

    if _DALLE_FAILED:
        print(f"   ℹ️  DALL-E 3 known to be offline/blocked. Bypassing and using Premium PIL Fallback directly...")
        _draw_whiteboard_fallback(prompt, output_path, size_str="1024x1024")
        return os.path.abspath(output_path)

    api_key = config.OPENAI_API_KEY
    if not api_key:
        print("   ⚠️  OPENAI_API_KEY not set. Activating offline PIL Fallback...")
        _DALLE_FAILED = True
        _draw_whiteboard_fallback(prompt, output_path, size_str="1024x1024")
        return os.path.abspath(output_path)

    # Record cost if job_id is provided
    try:
        from cost_tracker import LedgerManager
        LedgerManager.record_dalle_call(job_id, cost=0.04) # DALL-E 3 Standard price
    except Exception as e:
        print(f"⚠️ Failed to log image cost: {e}")

    from openai import Timeout
    client = OpenAI(
        api_key=api_key,
        timeout=Timeout(connect=5.0, read=300.0, write=5.0, pool=5.0)
    )

    print(f"🎨 Generating image for: {topic} [{subject}] via gpt-image-2...")

    import time
    for attempt in range(3):
        try:
            # Industrial Sentinel: gpt-image-2 may not support response_format='b64_json'
            # We default to URL-based retrieval for maximum compatibility.
            response = client.images.generate(
                model="gpt-image-2",
                prompt=prompt,
                size="1024x1024",
                quality="high",
                n=1
            )
            break
        except Exception as e:
            if attempt == 2:
                print(f"   ⚠️ DALL-E 3 Failed on all attempts: {e}. Activating Premium PIL Whiteboard Fallback and caching offline status!")
                _DALLE_FAILED = True
                _draw_whiteboard_fallback(prompt, output_path, size_str="1024x1024")
                return os.path.abspath(output_path)
            print(f"   ⚠️ DALL-E 3 Error: {e}. Retrying in {2**attempt}s...")
            time.sleep(2**attempt)

    if not response.data:
        raise RuntimeError(f"DALL-E 3 returned no images for: {topic}")

    # Save the image
    os.makedirs(output_dir, exist_ok=True)
    safe_name = filename or (
        re.sub(r'[^a-zA-Z0-9_\-]', '_', topic.lower().strip())[:50]
        + "_diagram.png"
    )
    output_path = os.path.join(output_dir, safe_name)

    # ━━━ Data Extraction ━━━
    # Handle both URL and b64_json (gpt-image-2 polymorphism)
    image_data = response.data[0]
    if hasattr(image_data, 'b64_json') and image_data.b64_json:
        print("   📦 Extracting from b64_json...")
        image_bytes = base64.b64decode(image_data.b64_json)
        with open(output_path, "wb") as f:
            f.write(image_bytes)
    elif hasattr(image_data, 'url') and image_data.url:
        print(f"   🌐 Downloading from URL: {image_data.url[:50]}...")
        import requests
        img_resp = requests.get(image_data.url)
        img_resp.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(img_resp.content)
    else:
        raise RuntimeError(f"DALL-E 3 response missing both URL and B64: {image_data}")

    print(f"✅ Image saved: {output_path}")
    return os.path.abspath(output_path)


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    topic   = sys.argv[1] if len(sys.argv) > 1 else "Internal Iliac Artery"
    subject = sys.argv[2] if len(sys.argv) > 2 else "medical"

    path = generate_concept_image(topic, subject, output_dir="output/test_images")
    print(f"\n📸 Generated: {path}")
