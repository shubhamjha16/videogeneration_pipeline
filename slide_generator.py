from PIL import Image, ImageDraw, ImageFont
import textwrap
import os
import re
import math
import random

# ── Font loader ────────────────────────────────────────────────────────────────
_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")

def _font(bold=False, size=24):
    """Load Caveat (hand-drawn) font, fallback to system fonts."""
    candidates = [
        # Caveat — hand-drawn style (bundled in assets/fonts)
        os.path.join(_FONT_DIR, "Caveat-Bold.ttf" if bold else "Caveat-Regular.ttf"),
        # macOS fallbacks
        "/Library/Fonts/Arial{}.ttf".format(" Bold" if bold else ""),
        "/System/Library/Fonts/Supplemental/Arial{}.ttf".format(" Bold" if bold else ""),
        "/System/Library/Fonts/Helvetica.ttc",
        # Linux / Docker
        "/usr/share/fonts/truetype/dejavu/DejaVuSans{}.ttf".format("-Bold" if bold else ""),
        "/usr/share/fonts/truetype/liberation/LiberationSans{}-Regular.ttf".format("-Bold" if bold else ""),
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except:
            pass
    return ImageFont.load_default()


# ── Doodle drawing helpers ─────────────────────────────────────────────────────

def _draw_wobbly_rect(draw, x0, y0, x1, y1, outline=(30, 30, 30), fill=None, width=3):
    """Draw a slightly wobbly rectangle to mimic hand-drawn style."""
    w = 4  # wobble amount
    pts = [
        (x0 + w, y0), (x1 - w, y0 + w//2),
        (x1, y0 + w), (x1 - w//2, y1 - w),
        (x1 - w, y1), (x0 + w, y1 - w//2),
        (x0, y1 - w), (x0 + w//2, y0 + w),
    ]
    if fill:
        draw.polygon(pts, fill=fill)
    draw.line(pts + [pts[0]], fill=outline, width=width)


def _draw_star(draw, cx, cy, r=10, fill=(255, 200, 0)):
    """Draw a 5-point star."""
    pts = []
    for i in range(10):
        angle = math.pi * i / 5 - math.pi / 2
        radius = r if i % 2 == 0 else r * 0.4
        pts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    draw.polygon(pts, fill=fill, outline=(200, 150, 0))


def _draw_circle_doodle(draw, cx, cy, r=8, fill=(255, 220, 50)):
    """Draw a small circle decoration."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill, outline=(180, 140, 0), width=2)


def _draw_arrow(draw, x0, y0, x1, y1, color=(50, 50, 50), width=3):
    """Draw a simple arrow from (x0,y0) to (x1,y1)."""
    draw.line([(x0, y0), (x1, y1)], fill=color, width=width)
    # Arrowhead
    angle = math.atan2(y1 - y0, x1 - x0)
    arrow_len = 12
    for a in [angle + 2.5, angle - 2.5]:
        draw.line([
            (x1, y1),
            (x1 - arrow_len * math.cos(a), y1 - arrow_len * math.sin(a))
        ], fill=color, width=width)


def _scatter_decorations(draw, width, height, seed=42):
    """Scatter stars and circles around the background."""
    rng = random.Random(seed)
    # Stars in corners and edges
    star_positions = [
        (60, 50), (width - 60, 45), (40, height - 50), (width - 45, height - 55),
        (width // 2 + 180, 35), (width // 2 - 150, height - 40),
        (80, height // 2 - 80), (width - 80, height // 2 + 60),
    ]
    star_colors = [(255, 200, 0), (255, 220, 50), (255, 180, 0)]
    for i, (x, y) in enumerate(star_positions):
        r = rng.randint(8, 16)
        _draw_star(draw, x + rng.randint(-10, 10), y + rng.randint(-8, 8),
                   r=r, fill=star_colors[i % len(star_colors)])

    # Small circles
    circle_positions = [
        (width - 30, 120), (25, 200), (width - 25, height - 130), (30, height - 120),
    ]
    for x, y in circle_positions:
        _draw_circle_doodle(draw, x + rng.randint(-5, 5), y + rng.randint(-5, 5),
                            r=rng.randint(6, 10))

    # Dotted border accents (top + bottom)
    for x in range(120, width - 120, 40):
        r = rng.randint(3, 5)
        draw.ellipse([x - r, 8 - r, x + r, 8 + r], fill=(220, 180, 0))
        draw.ellipse([x - r, height - 8 - r, x + r, height - 8 + r], fill=(220, 180, 0))


# ── Main slide generator ───────────────────────────────────────────────────────

def generate_slide_image(text: str, scene_idx: int, output_dir: str = ".", bg_image: str = None) -> str:
    """
    Generate a premium doodle/whiteboard style educational slide.
    Matches EaseToLearn brand: cream background, hand-drawn font, yellow accents.
    Output: 1920x1080 PNG
    """
    output_filename = os.path.join(output_dir, f"scene_{scene_idx}_slide.png")
    W, H = 1920, 1080

    # ── Background ─────────────────────────────────────────────────────────────
    img = Image.new("RGB", (W, H), color=(255, 252, 230))  # warm cream
    draw = ImageDraw.Draw(img)

    # Subtle gradient — slightly darker at bottom
    for y in range(H):
        ratio = y / H
        r = int(255 - ratio * 8)
        g = int(252 - ratio * 15)
        b = int(230 - ratio * 20)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # ── Yellow accent bars (left + right) ──────────────────────────────────────
    draw.rectangle([0, 0, 18, H], fill=(255, 200, 0))
    draw.rectangle([W - 18, 0, W, H], fill=(255, 200, 0))

    # ── Scatter decorations ────────────────────────────────────────────────────
    _scatter_decorations(draw, W, H, seed=scene_idx * 7 + 3)

    # ── EaseToLearn logo area (top-left) ───────────────────────────────────────
    logo_font = _font(bold=True, size=28)
    draw.text((40, 22), "∞  EaseToLearn", font=logo_font, fill=(40, 40, 40))

    # ── Parse text into title + bullets ───────────────────────────────────────
    parts   = re.split(r'\.\s+(?=[A-Z])', text.strip())
    title   = parts[0].rstrip('.')
    bullets = [p.strip().rstrip('.') for p in parts[1:] if p.strip()]

    # ── Layout constants ───────────────────────────────────────────────────────
    CONTENT_X  = 80
    CONTENT_W  = W - 160
    TITLE_Y    = 100
    BULLET_START_Y = 280

    # ── Title card ─────────────────────────────────────────────────────────────
    title_font = _font(bold=True, size=90)
    title_wrapped = textwrap.fill(title, width=38)
    title_lines = title_wrapped.split('\n')

    # Title background card (wobbly)
    card_pad = 24
    title_h_est = len(title_lines) * 96 + card_pad * 2
    _draw_wobbly_rect(
        draw,
        CONTENT_X - card_pad, TITLE_Y - card_pad,
        CONTENT_X + CONTENT_W + card_pad, TITLE_Y + title_h_est,
        outline=(30, 30, 30), fill=(255, 255, 255), width=4
    )

    # Draw title text
    ty = TITLE_Y
    for line in title_lines:
        draw.text((CONTENT_X + 10, ty), line, font=title_font, fill=(20, 20, 20))
        ty += 96

    # Yellow underline accent
    draw.rectangle([CONTENT_X, ty + 4, CONTENT_X + 400, ty + 12], fill=(255, 200, 0))

    # ── Bullet points ──────────────────────────────────────────────────────────
    if bullets:
        body_font  = _font(bold=False, size=58)
        label_font = _font(bold=True,  size=58)

        cols = 2 if len(bullets) >= 3 else 1
        col_w = (CONTENT_W - 40) // cols
        by = BULLET_START_Y
        BULLET_H = 130  # height per bullet card
        BULLET_PAD = 16

        for i, bullet in enumerate(bullets[:6]):  # max 6 bullets
            col = i % cols
            row = i // cols
            bx = CONTENT_X + col * (col_w + 20)
            card_y = by + row * (BULLET_H + 16)

            # Bullet card background
            _draw_wobbly_rect(
                draw,
                bx, card_y,
                bx + col_w - 10, card_y + BULLET_H,
                outline=(30, 30, 30), fill=(255, 255, 255), width=3
            )

            # Yellow circle with number
            num_cx = bx + 36
            num_cy = card_y + BULLET_H // 2
            draw.ellipse([num_cx - 28, num_cy - 28, num_cx + 28, num_cy + 28],
                         fill=(255, 200, 0), outline=(30, 30, 30), width=3)
            num_font = _font(bold=True, size=42)
            draw.text((num_cx, num_cy), str(i + 1), font=num_font,
                      fill=(20, 20, 20), anchor="mm")

            # Bullet text
            max_chars = max(18, int((col_w - 100) / 30))
            wrapped = textwrap.fill(bullet, width=max_chars)
            lines = wrapped.split('\n')
            text_x = bx + 76
            text_y = card_y + BULLET_H // 2 - (len(lines) * 62) // 2
            for line in lines[:2]:
                draw.text((text_x, text_y), line, font=body_font, fill=(30, 30, 30))
                text_y += 62

    # ── Bottom brand line ──────────────────────────────────────────────────────
    brand_font = _font(bold=False, size=28)
    draw.text((W - 40, H - 36), "www.easetolearn.com",
              font=brand_font, fill=(120, 100, 50), anchor="rs")

    img.save(output_filename, quality=95)
    print(f"Generated doodle slide for scene {scene_idx} → {output_filename}")
    return output_filename
