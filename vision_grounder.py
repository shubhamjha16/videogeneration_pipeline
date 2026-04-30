"""
Vision Grounder — Pixel-Precise Landmark Detection for Annotated Images

After generating an educational diagram, this module sends it to GPT-4o vision
to get normalized [x, y] coordinates for specific landmarks. This allows the
Manim arrow to point directly at e.g. "the left ventricle" instead of using a
coarse 9-region grid like "lower_right".

Usage:
    from vision_grounder import ground_landmarks
    coords = ground_landmarks("heart_diagram.png", ["left ventricle", "aorta"])
    # → {"left ventricle": [0.62, 0.71], "aorta": [0.45, 0.22]}

Cost: ~$0.01–0.05 per image (single GPT-4o vision call).
Results are cached per image path to avoid duplicate API calls.
"""

import os
import json
import base64
import hashlib
from typing import Optional

import config

# ── In-Memory Cache ──────────────────────────────────────────────────────────
# Maps image_hash → {label: [x, y]} so we never re-call vision for the same image.
_landmark_cache: dict[str, dict[str, list[float]]] = {}


def _image_hash(image_path: str) -> str:
    """Fast content-based hash for cache keying."""
    h = hashlib.md5()
    with open(image_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _encode_image_base64(image_path: str) -> str:
    """Read an image file and return its base64-encoded string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def ground_landmarks(
    image_path: str,
    labels: list[str],
    model: str = "gpt-4o",
) -> dict[str, list[float]]:
    """
    Send an image to GPT-4o vision and return normalized coordinates for each landmark.

    Args:
        image_path: Absolute path to the generated diagram image.
        labels:     List of landmark names to locate (e.g. ["left ventricle", "aorta"]).
        model:      Vision model to use (default: gpt-4o).

    Returns:
        Dictionary mapping each label to [x_normalized, y_normalized] in range [0.0, 1.0].
        (0, 0) = top-left of image.  Missing labels are omitted from the result.
    """
    if not labels:
        return {}

    if not os.path.exists(image_path):
        print(f"⚠️  [VisionGrounder] Image not found: {image_path}")
        return {}

    # ── Cache lookup ──────────────────────────────────────────────────────
    img_hash = _image_hash(image_path)
    cache_key = f"{img_hash}_{','.join(sorted(labels))}"
    if cache_key in _landmark_cache:
        print(f"   ✅ [VisionGrounder] Cache hit for {len(labels)} landmarks")
        return _landmark_cache[cache_key]

    # ── Build vision request ──────────────────────────────────────────────
    api_key = config.OPENAI_API_KEY
    if not api_key:
        print("⚠️  [VisionGrounder] OPENAI_API_KEY not set — falling back to region grid")
        return {}

    from openai import OpenAI
    client = OpenAI(api_key=api_key, timeout=60.0)

    image_b64 = _encode_image_base64(image_path)
    ext = os.path.splitext(image_path)[1].lower().lstrip(".")
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext, "image/png")

    labels_str = ", ".join(f'"{l}"' for l in labels)
    prompt = (
        f"You are an expert at analyzing educational diagrams. "
        f"Given this image, locate the following landmarks and return their positions as "
        f"normalized coordinates (x, y) where (0.0, 0.0) is the top-left corner and "
        f"(1.0, 1.0) is the bottom-right corner.\n\n"
        f"Landmarks to locate: [{labels_str}]\n\n"
        f"Return ONLY valid JSON in this exact format, no other text:\n"
        f'{{"landmarks": {{"label_name": [x, y], ...}}}}\n\n'
        f"If a landmark is not visible in the image, omit it from the result. "
        f"Be as precise as possible — point to the center of the structure, not its edge."
    )

    print(f"🔍 [VisionGrounder] Grounding {len(labels)} landmarks via {model}...")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime};base64,{image_b64}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
            max_tokens=500,
            timeout=60.0,
        )

        raw = response.choices[0].message.content.strip()

        # Parse JSON — handle markdown wrappers
        if raw.startswith("```"):
            import re
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL)
            if match:
                raw = match.group(1)

        data = json.loads(raw)
        landmarks = data.get("landmarks", data)  # handle both wrapped and unwrapped

        # Validate: all coords must be [float, float] in [0, 1]
        result = {}
        for label, coords in landmarks.items():
            if (
                isinstance(coords, (list, tuple))
                and len(coords) == 2
                and all(isinstance(c, (int, float)) for c in coords)
            ):
                x, y = float(coords[0]), float(coords[1])
                # Clamp to valid range
                x = max(0.0, min(1.0, x))
                y = max(0.0, min(1.0, y))
                result[label.lower()] = [x, y]
            else:
                print(f"   ⚠️  [VisionGrounder] Invalid coords for '{label}': {coords}")

        # Cache the result
        _landmark_cache[cache_key] = result
        print(f"   ✅ [VisionGrounder] Grounded {len(result)}/{len(labels)} landmarks")
        return result

    except json.JSONDecodeError as e:
        print(f"   ❌ [VisionGrounder] JSON parse failed: {e}")
        print(f"   Raw response: {raw[:200]}")
        return {}
    except Exception as e:
        print(f"   ❌ [VisionGrounder] Vision call failed: {e}")
        return {}


# ── CLI Test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    if len(sys.argv) < 3:
        print("Usage: python vision_grounder.py <image_path> <label1> [label2] ...")
        sys.exit(1)

    image_path = sys.argv[1]
    labels = sys.argv[2:]

    coords = ground_landmarks(image_path, labels)
    print(f"\n📍 Grounded Landmarks:")
    for label, (x, y) in coords.items():
        print(f"   {label}: ({x:.3f}, {y:.3f})")
