"""
Thumbnail Generator — EaseToLearn Hybrid Engine
================================================
Step 1: Gemini Imagen generates base image (background + teacher + decorative elements)
Step 2: PIL overlays precise text on top (orange pill, headline, year badge, bullets, logo)

Output: 1280x720 PNG (16:9) — matches EaseToLearn YouTube thumbnail style exactly
"""

import os
import math
import random
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap

# ── Constants ──────────────────────────────────────────────────────────────────

W, H = 1280, 720
CURRENT_YEAR = str(datetime.now().year)

WHITE        = (255, 255, 255)
YELLOW       = (255, 200, 0)
YELLOW_DARK  = (200, 155, 0)
ORANGE       = (235, 110, 30)
ORANGE_DARK  = (180, 75, 10)
DARK_TEXT    = (15, 15, 15)
SHADOW       = (0, 0, 30)

LEFT_MARGIN  = 55
TEXT_ZONE_W  = 750


# ── Gemini prompts per subject ─────────────────────────────────────────────────

_GEMINI_PROMPTS = {
    "medical": (
        "Professional YouTube thumbnail base for Indian medical education. "
        "Dark navy blue gradient background (#0a1440 to #0d1f6e). "
        "On the RIGHT side only (right 40% of image), a confident Indian male educator "
        "in professional attire, smiling, gesturing with open hand toward left. "
        "Background has subtle DNA double helix graphics, molecular structures, "
        "and soft blue circular light effects. "
        "LEFT side (60%) must be completely CLEAN and EMPTY — no text, no graphics, "
        "just clean dark blue gradient for text overlay. "
        "16:9 ratio, 1280x720, photorealistic, premium coaching institute style, "
        "high contrast, professional studio lighting on teacher. No text anywhere."
    ),
    "physics": (
        "Professional YouTube thumbnail base for Indian physics JEE education. "
        "Dark navy blue gradient background. "
        "On the RIGHT side only (right 40% of image), a confident Indian male educator "
        "in grey blazer, smiling, pointing finger toward left side. "
        "Background has subtle physics diagrams — velocity arrows, sine waves, "
        "circuit symbols, soft blue glow effects scattered on right side. "
        "LEFT side (60%) must be completely CLEAN and EMPTY — no text, no graphics, "
        "just clean dark blue gradient for text overlay. "
        "16:9 ratio, 1280x720, photorealistic, premium JEE coaching style. No text anywhere."
    ),
    "maths": (
        "Professional YouTube thumbnail base for Indian mathematics JEE education. "
        "Dark navy blue gradient background. "
        "On the RIGHT side only (right 40% of image), a confident Indian male educator "
        "in navy blazer, smiling confidently, one hand gesturing open palm. "
        "Background has subtle math elements — integral symbols, parabola curves, "
        "coordinate axes, soft golden glow on right side. "
        "LEFT side (60%) must be completely CLEAN and EMPTY — no text, no graphics, "
        "just clean dark blue gradient for text overlay. "
        "16:9 ratio, 1280x720, photorealistic, premium JEE coaching style. No text anywhere."
    ),
    "chemistry": (
        "Professional YouTube thumbnail base for Indian chemistry education. "
        "Dark navy blue to dark background. "
        "On the RIGHT side only (right 40% of image), a confident young Indian male educator "
        "in navy blazer and white shirt, smiling, pointing upward. "
        "Background has floating 3D molecular structures, benzene rings, "
        "red and blue atom spheres on right background. "
        "LEFT side (60%) must be completely CLEAN and EMPTY — no text, no graphics. "
        "16:9 ratio, 1280x720, photorealistic, premium coaching institute style. No text anywhere."
    ),
    "upsc": (
        "Professional YouTube thumbnail base for Indian UPSC civil services education. "
        "Dark navy blue gradient background. "
        "On the RIGHT side only (right 40% of image), a confident Indian male educator "
        "in formal grey suit, smiling, gesturing with open hand. "
        "Background has a faint Ashoka Chakra watermark on right side. "
        "LEFT side (60%) must be completely CLEAN and EMPTY — no text, no graphics. "
        "16:9 ratio, 1280x720, photorealistic, premium IAS coaching style. No text anywhere."
    ),
    "english": (
        "Professional YouTube thumbnail base for Indian English CUET education. "
        "Dark navy blue gradient background with subtle blue wave textures. "
        "On the RIGHT side only (right 40% of image), a confident Indian male educator "
        "in dark shirt, smiling, gesturing expressively. "
        "LEFT side (60%) must be completely CLEAN and EMPTY — no text, no graphics. "
        "16:9 ratio, 1280x720, photorealistic, premium CUET coaching style. No text anywhere."
    ),
    "mba": (
        "Professional YouTube thumbnail base for Indian MBA CAT exam education. "
        "Dark navy blue gradient background. "
        "On the RIGHT side only (right 40% of image), a confident Indian male educator "
        "in sharp business suit, smiling professionally, gesturing authoritatively. "
        "LEFT side (60%) must be completely CLEAN and EMPTY — no text, no graphics. "
        "16:9 ratio, 1280x720, photorealistic, premium MBA coaching style. No text anywhere."
    ),
    "unknown": (
        "Professional YouTube thumbnail base for Indian competitive exam education. "
        "Dark navy blue gradient background. "
        "On the RIGHT side only (right 40% of image), a confident Indian male educator "
        "in professional attire, smiling, gesturing with open hand toward left. "
        "LEFT side (60%) must be completely CLEAN and EMPTY — no text, no graphics. "
        "16:9 ratio, 1280x720, photorealistic, premium coaching institute style. No text anywhere."
    ),
}

EXAM_NAME_MAP = {
    "medical":   "FMGE",
    "physics":   "JEE",
    "maths":     "JEE",
    "chemistry": "JEE",
    "upsc":      "UPSC",
    "english":   "CUET",
    "mba":       "CAT",
    "unknown":   "MASTER",
}

SUBJECT_KEYWORD_MAP = {
    "medical":   "MEDICAL",
    "physics":   "PHYSICS",
    "maths":     "MATHEMATICS",
    "chemistry": "CHEMISTRY",
    "upsc":      "UPSC",
    "english":   "ENGLISH",
    "mba":       "MBA",
    "unknown":   "MASTERY",
}

PILL_TEXT_MAP = {
    "medical":   "How to prepare for",
    "physics":   "How to prepare for",
    "maths":     "How to prepare for",
    "chemistry": "8 Week Strategic Prep For",
    "upsc":      "How to prepare for",
    "english":   "How to prepare for",
    "mba":       "How to prepare for",
    "unknown":   "How to prepare for",
}

BULLET_DEFAULTS = {
    "medical":   ["High Yield FMGE Topics", "Clinically Important Concepts", "Smart Exam Strategy"],
    "physics":   ["High Priority Topics", "Formula Based Approach", "Concept Clarity"],
    "maths":     ["High Priority Topics", "Step-by-Step Solutions", "Score Maximization"],
    "chemistry": ["High Priority Topics", "Mark Winning Strategy", "Reaction Mastery"],
    "upsc":      ["High Priority Topics", "Smart Study Strategy", "Answer Writing Tips"],
    "english":   ["High Priority Topics", "Grammar Mastery", "Score Winning Strategy"],
    "mba":       ["High Priority Topics", "Case Study Approach", "Strategic Preparation"],
    "unknown":   ["High Priority Topics", "Smart Strategy", "Score Maximization"],
}


# ── Font loader ────────────────────────────────────────────────────────────────

def _font(bold=False, size=24):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "assets", "fonts",
                     "Inter-Bold.ttf" if bold else "Inter-Regular.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold
            else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


# ── Step 1: Gemini base image ──────────────────────────────────────────────────

def _generate_base_with_gemini(subject: str, job_dir: str) -> str:
    """
    Use Gemini Imagen to generate background + teacher layer.
    Returns path to saved base PNG.
    Falls back to PIL base if Gemini unavailable.
    """
    try:
        import config
        from google import genai
        from google.genai import types

        api_key = config.GEMINI_API_KEY
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set")

        client = genai.Client(api_key=api_key)
        prompt = _GEMINI_PROMPTS.get(subject, _GEMINI_PROMPTS["unknown"])

        print(f"   🎨 Gemini generating base layer for: {subject}...")

        for attempt in range(3):
            try:
                response = client.models.generate_images(
                    model="imagen-4.0-generate-001",
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio="16:9",
                        safety_filter_level="block_low_and_above",
                    ),
                )
                if not response.generated_images:
                    raise RuntimeError("Gemini returned no images")

                base_path = os.path.join(job_dir, "thumb_base.png")
                image_bytes = response.generated_images[0].image.image_bytes
                with open(base_path, "wb") as f:
                    f.write(image_bytes)

                # Ensure exact 1280x720
                img = Image.open(base_path).convert("RGB")
                img = img.resize((W, H), Image.Resampling.LANCZOS)
                img.save(base_path, quality=95)

                print(f"   ✅ Gemini base ready")
                return base_path

            except Exception as e:
                if "429" in str(e) and attempt < 2:
                    print(f"   ⚠️  Rate limit, retrying in {2**attempt}s...")
                    time.sleep(2 ** attempt)
                    continue
                raise e

    except Exception as e:
        print(f"   ⚠️  Gemini unavailable ({e}) — using PIL fallback base")
        return _generate_pil_fallback_base(job_dir)


def _generate_pil_fallback_base(job_dir: str) -> str:
    """Clean PIL base when Gemini is unavailable."""
    img = Image.new("RGB", (W, H), (15, 30, 100))
    draw = ImageDraw.Draw(img)

    # Gradient
    for y in range(H):
        ratio = y / H
        r = int(15 + (8  - 15)  * ratio)
        g = int(30 + (18 - 30)  * ratio)
        b = int(100 + (65 - 100) * ratio)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Decorative circles right side
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for cx, cy, r, alpha in [(950,300,280,25),(980,320,200,35),(1050,180,160,20)]:
        od.ellipse([cx-r, cy-r, cx+r, cy+r], outline=(60, 100, 220, alpha), width=3)
    rng = random.Random(42)
    for _ in range(50):
        x = rng.randint(500, W)
        y = rng.randint(0, H)
        r = rng.randint(3, 10)
        od.ellipse([x-r, y-r, x+r, y+r],
                   fill=(50, 90, 200, rng.randint(20, 50)))

    # Teacher placeholder silhouette
    od.ellipse([870, 140, 990, 260], outline=(255,255,255,120), width=3)
    od.line([(930,260),(930,460)], fill=(200,200,200,100), width=3)
    od.line([(850,360),(1010,360)], fill=(200,200,200,100), width=3)
    od.line([(930,460),(870,620)], fill=(200,200,200,100), width=3)
    od.line([(930,460),(990,620)], fill=(200,200,200,100), width=3)

    img = img.convert("RGBA")
    img.paste(overlay, (0,0), overlay)
    img = img.convert("RGB")

    base_path = os.path.join(job_dir, "thumb_base.png")
    img.save(base_path)
    return base_path


# ── Step 2: PIL text overlay ───────────────────────────────────────────────────

def _overlay_text(base_path, exam_name, subject_keyword, bullets, pill_text):
    """Load Gemini base and overlay all text elements via PIL."""
    img = Image.open(base_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Subtle dark overlay on left zone for text readability
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for x in range(int(W * 0.62)):
        alpha = int(70 * (1 - x / (W * 0.62)))
        od.line([(x, 0), (x, H)], fill=(0, 0, 20, alpha))
    img = img.convert("RGBA")
    img.paste(overlay, (0, 0), overlay)
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)

    # Draw all elements
    pill_bottom    = _draw_orange_pill(draw, pill_text)
    subject_bottom = _draw_main_headline(draw, exam_name, subject_keyword, pill_bottom)
    badge_bottom   = _draw_year_badge(draw, subject_bottom)
    _draw_bullets(draw, bullets, badge_bottom)
    _draw_logo(draw, img)

    return img


def _draw_orange_pill(draw, pill_text):
    """Orange rounded pill bar at top."""
    font = _font(bold=True, size=38)
    bbox = draw.textbbox((0, 0), pill_text, font=font)
    tw   = bbox[2] - bbox[0]
    x1, y1 = LEFT_MARGIN, 42
    x2, y2 = x1 + tw + 60, y1 + 62

    draw.rounded_rectangle([x1, y1, x2, y2], radius=31,
                            fill=ORANGE, outline=ORANGE_DARK, width=2)
    draw.text((x1 + 30, y1 + 31), pill_text, font=font,
              fill=DARK_TEXT, anchor="lm")
    return y2


def _draw_main_headline(draw, exam_name, subject_keyword, pill_bottom):
    """Exam name white + subject keyword yellow, both huge."""
    start_y = pill_bottom + 18

    # Exam name — white
    for size in [148, 130, 115, 100]:
        ef = _font(bold=True, size=size)
        bbox = draw.textbbox((0, 0), exam_name, font=ef)
        if (bbox[2] - bbox[0]) < TEXT_ZONE_W - LEFT_MARGIN:
            break
    draw.text((LEFT_MARGIN + 3, start_y + 3), exam_name, font=ef, fill=SHADOW)
    draw.text((LEFT_MARGIN, start_y), exam_name, font=ef, fill=WHITE,
              stroke_width=2, stroke_fill=(0, 0, 40))
    exam_bottom = draw.textbbox((LEFT_MARGIN, start_y), exam_name, font=ef)[3]

    # Subject keyword — yellow
    subj_text = subject_keyword[:12]
    for size in [148, 130, 115, 100, 88]:
        sf = _font(bold=True, size=size)
        bbox = draw.textbbox((0, 0), subj_text, font=sf)
        if (bbox[2] - bbox[0]) < TEXT_ZONE_W - LEFT_MARGIN:
            break
    subj_y = exam_bottom - 8
    draw.text((LEFT_MARGIN + 3, subj_y + 3), subj_text, font=sf, fill=(80, 60, 0))
    draw.text((LEFT_MARGIN, subj_y), subj_text, font=sf, fill=YELLOW,
              stroke_width=2, stroke_fill=(100, 75, 0))

    return draw.textbbox((LEFT_MARGIN, subj_y), subj_text, font=sf)[3]


def _draw_year_badge(draw, subject_bottom):
    """Orange rounded year badge."""
    badge_font = _font(bold=True, size=52)
    bbox = draw.textbbox((0, 0), CURRENT_YEAR, font=badge_font)
    bw, bh = bbox[2] - bbox[0] + 44, 66
    bx = LEFT_MARGIN
    by = min(subject_bottom + 8, H - 180 - bh - 10)

    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=14,
                            fill=ORANGE, outline=ORANGE_DARK, width=2)
    draw.text((bx + bw // 2, by + bh // 2), CURRENT_YEAR, font=badge_font,
              fill=WHITE, anchor="mm", stroke_width=1, stroke_fill=ORANGE_DARK)
    return by + bh


def _draw_bullets(draw, bullets, badge_bottom):
    """Yellow checkmark + white bold bullets."""
    font  = _font(bold=True, size=33)
    check = _font(bold=True, size=33)
    n     = min(len(bullets), 3)
    y     = max(badge_bottom + 20, H - n * 50 - 38)

    for bullet in bullets[:3]:
        draw.text((LEFT_MARGIN, y), "✓", font=check, fill=YELLOW)
        draw.text((LEFT_MARGIN + 38, y),
                  textwrap.shorten(bullet, width=42, placeholder="…"),
                  font=font, fill=WHITE,
                  stroke_width=1, stroke_fill=(0, 0, 30))
        y += 50


def _draw_logo(draw, img):
    """EaseToLearn logo top right."""
    base_dir  = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(base_dir, "assets", "logo.png")
    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo = logo.resize((160, 55), Image.Resampling.LANCZOS)
            img_rgba = img.convert("RGBA")
            img_rgba.paste(logo, (W - 175, 22), logo)
            img.paste(img_rgba.convert("RGB"), (0, 0))
            return
        except Exception:
            pass

    # Text fallback
    lx, ly = W - 190, 28
    draw.rounded_rectangle([lx-10, ly-6, W-10, ly+46],
                            radius=8, fill=(0, 0, 40))
    draw.text((lx, ly+8), "∞", font=_font(bold=True, size=30), fill=WHITE)
    draw.text((lx+36, ly+4), "EaseToLearn",
              font=_font(bold=True, size=20), fill=WHITE)
    draw.text((lx+36, ly+26), "www.easetolearn.com",
              font=_font(bold=False, size=13), fill=(180, 180, 200))


# ── Content helpers ────────────────────────────────────────────────────────────

def _extract_exam_name(topic, subject):
    topic_upper = topic.upper()
    for exam in ["FMGE", "JEE", "UPSC", "NEET", "CUET", "CAT", "GATE"]:
        if exam in topic_upper:
            return exam
    return EXAM_NAME_MAP.get(subject, "MASTER")


def _extract_subject_keyword(topic, subject):
    topic_upper = topic.upper()
    known = ["MEDICAL", "PHYSICS", "MATHEMATICS", "MATHS", "CHEMISTRY",
             "BIOLOGY", "UPSC", "ENGLISH", "ECONOMICS", "SOCIOLOGY",
             "HISTORY", "GEOGRAPHY", "POLITY", "MBA", "APTITUDE"]
    for kw in known:
        if kw in topic_upper:
            return kw
    return SUBJECT_KEYWORD_MAP.get(subject, "MASTERY")


def _build_bullets(subject, key_points=None):
    if key_points:
        cleaned = [kp.split('.')[0].strip()[:50]
                   for kp in key_points[:3] if len(kp.split('.')[0].strip()) >= 8]
        if len(cleaned) >= 2:
            return cleaned[:3]
    return BULLET_DEFAULTS.get(subject, BULLET_DEFAULTS["unknown"])[:3]


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_thumbnail(
    topic: str,
    subject: str,
    key_points: list = None,
    job_dir: str = ".",
    filename: str = "thumbnail.png",
) -> str:
    """
    Generate EaseToLearn-style thumbnail.
    Gemini Imagen → background + teacher
    PIL → text overlay (pill, headline, badge, bullets, logo)

    Returns absolute path to final PNG.
    """
    print(f"🎬 [Thumbnail] {topic} [{subject}]")
    os.makedirs(job_dir, exist_ok=True)

    exam_name       = _extract_exam_name(topic, subject)
    subject_keyword = _extract_subject_keyword(topic, subject)
    bullets         = _build_bullets(subject, key_points)
    pill_text       = PILL_TEXT_MAP.get(subject, "How to prepare for")

    # Step 1: Gemini base
    base_path = _generate_base_with_gemini(subject, job_dir)

    # Step 2: PIL text overlay
    print(f"   ✍️  Overlaying text: {exam_name} / {subject_keyword}")
    final_img = _overlay_text(base_path, exam_name, subject_keyword,
                               bullets, pill_text)

    # Save + cleanup
    output_path = os.path.join(job_dir, filename)
    final_img.save(output_path, quality=95)
    if os.path.exists(base_path):
        try:
            os.remove(base_path)
        except Exception:
            pass

    print(f"   ✅ Thumbnail: {output_path}")
    return os.path.abspath(output_path)


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    topic   = sys.argv[1] if len(sys.argv) > 1 else "Carpopedal Spasm in Hyperventilation"
    subject = sys.argv[2] if len(sys.argv) > 2 else "medical"

    path = generate_thumbnail(
        topic=topic,
        subject=subject,
        key_points=[
            "Respiratory alkalosis reduces ionized calcium",
            "Calcium binds to plasma proteins",
            "Neuromuscular excitability increases"
        ],
        job_dir="output/test_thumbnails",
        filename=f"thumb_{subject}_hybrid.png"
    )
    print(f"\n📸 Done: {path}")
