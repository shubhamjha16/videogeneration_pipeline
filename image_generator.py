"""
Image Generator — Gemini Imagen 3
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
from pathlib import Path
from google import genai
from google.genai import types
import config


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
) -> str:
    """
    Generate an educational diagram using Gemini Imagen 3.

    Args:
        topic      : Topic name (e.g. "Internal Iliac Artery")
        subject    : Subject type from html_parser (medical/physics/maths/...)
        output_dir : Directory to save the image
        filename   : Override filename (default: topic_diagram.png)

    Returns:
        Absolute path to the saved PNG file
    """
    api_key = config.GEMINI_API_KEY
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in environment / .env")

    client = genai.Client(api_key=api_key)

    # Build subject-aware prompt
    template = _PROMPT_TEMPLATES.get(subject, _PROMPT_TEMPLATES["default"])
    prompt = template.format(topic=topic)

    print(f"🎨 Generating image for: {topic} [{subject}]...")

    response = client.models.generate_images(
        model="imagen-4.0-generate-001",
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio="16:9",          # matches video frame
            safety_filter_level="block_low_and_above",
        ),
    )

    if not response.generated_images:
        raise RuntimeError(f"Imagen returned no images for topic: {topic}")

    # Save the image
    os.makedirs(output_dir, exist_ok=True)
    safe_name = filename or (
        topic.lower().replace(" ", "_").replace("/", "_") + "_diagram.png"
    )
    output_path = os.path.join(output_dir, safe_name)

    image_bytes = response.generated_images[0].image.image_bytes
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
