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


# ── Main generator ────────────────────────────────────────────────────────────

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
    api_key = config.OPENAI_API_KEY
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set in config / environment")

    # Record cost if job_id is provided
    try:
        from cost_tracker import LedgerManager
        LedgerManager.record_higgsfield_call(job_id, cost_per_call=0.04) # DALL-E 3 HD price
    except Exception as e:
        print(f"⚠️ Failed to log image cost: {e}")

    client = OpenAI(api_key=api_key)


    # Same subject-aware prompts you already have
    template = _PROMPT_TEMPLATES.get(subject, _PROMPT_TEMPLATES["default"])
    prompt = template.format(topic=topic)

    print(f"🎨 Generating image for: {topic} [{subject}] via gpt-image-2...")

    import time
    for attempt in range(3):
        try:
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="hd",
                n=1,
                response_format="b64_json"
            )
            break
        except Exception as e:
            if attempt == 2:
                raise
            print(f"   ⚠️ gpt-image-2 rate limit. Retrying in {2**attempt}s...")
            time.sleep(2**attempt)

    if not response.data:
        raise RuntimeError(f"gpt-image-2 returned no images for: {topic}")

    # Save the image
    os.makedirs(output_dir, exist_ok=True)
    safe_name = filename or (
        re.sub(r'[^a-zA-Z0-9_\-]', '_', topic.lower().strip())[:50]
        + "_diagram.png"
    )

    output_path = os.path.join(output_dir, safe_name)
    image_bytes = base64.b64decode(response.data[0].b64_json)

    with open(output_path, "wb") as f:
        f.write(image_bytes)

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
