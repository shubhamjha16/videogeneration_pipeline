from PIL import Image, ImageDraw, ImageFont
import textwrap
import os
import re

def generate_slide_image(text: str, scene_idx: int, output_dir: str = ".") -> str:
    """
    Generates a professional PPT-style educational slide.
    All sizing is scaled for 854x480 (480p) output.
    """
    output_filename = os.path.join(output_dir, f"scene_{scene_idx}_slide.png")
    width, height = 854, 480

    # ── Background: warm yellow → orange gradient ──────────────────────────
    img = Image.new('RGB', (width, height), color=(255, 200, 50))
    d = ImageDraw.Draw(img)
    for y in range(height):
        ratio = y / height
        d.line([(0, y), (width, y)], fill=(255, int(200 - ratio * 80), int(50 - ratio * 50)))

    # ── White rounded card ─────────────────────────────────────────────────
    m = 30
    card = [(m, m), (width - m, height - m)]
    d.rounded_rectangle(card, radius=14, fill=(255, 255, 255), outline=(200, 200, 200), width=2)

    # ── Decorative squares top-left corner of card ─────────────────────────
    sq = 22
    d.rectangle([(m + 8, m + 8), (m + 8 + sq, m + 8 + sq)], fill=(230, 120, 30))
    d.rectangle([(m + 20, m + 18), (m + 20 + sq, m + 18 + sq)], fill=(30, 100, 220))

    # ── Fonts (scaled down for 480p) ───────────────────────────────────────
    def load_font(bold=False, size=20):
        candidates = [
            "/Library/Fonts/Arial{}.ttf".format(" Bold" if bold else ""),
            "/System/Library/Fonts/Supplemental/Arial{}.ttf".format(" Bold" if bold else ""),
            "/System/Library/Fonts/Helvetica.ttc",
        ]
        for p in candidates:
            try:
                return ImageFont.truetype(p, size)
            except:
                pass
        return ImageFont.load_default()

    font_title = load_font(bold=True,  size=26)   # was 68 — scaled for 480p
    font_body  = load_font(bold=False, size=19)   # was 46

    # ── Parse text: split on ". CapitalLetter" to preserve abbreviations ───
    parts  = re.split(r'\.\s+(?=[A-Z])', text.strip())
    title  = parts[0].rstrip('.')
    bullets = [p.strip().rstrip('.') for p in parts[1:] if p.strip()]

    # ── Layout: constrain to 68% of width (safe zone before avatar panel) ──
    TEXT_MAX_X  = int(width * 0.68)   # 580px — text never enters avatar panel
    LEFT_PAD    = m + 20
    card_top    = m + 8
    card_bot    = height - m - 8
    card_h      = card_bot - card_top
    title_cx    = TEXT_MAX_X // 2

    # Estimate heights
    TITLE_LINE_H = 32
    BULLET_LINE_H = 28
    title_text  = textwrap.fill(title, width=36)
    title_lines = title_text.split('\n')
    title_h     = len(title_lines) * TITLE_LINE_H + 10
    bullets_h   = len(bullets) * BULLET_LINE_H
    block_h     = title_h + 10 + bullets_h
    text_top    = card_top + max(10, (card_h - block_h) // 2)

    # ── Draw title ─────────────────────────────────────────────────────────
    for i, line in enumerate(title_lines):
        d.text(
            (title_cx, text_top + i * TITLE_LINE_H + TITLE_LINE_H // 2),
            line, font=font_title, fill=(180, 0, 50), anchor="mm"
        )

    # ── Draw bullet points ─────────────────────────────────────────────────
    bullet_y = text_top + title_h + 10
    chars_per_line = max(20, int(TEXT_MAX_X / 11))   # ~11px per char at 19pt
    for line in bullets:
        wrapped = textwrap.fill(line, width=chars_per_line)
        d.text(
            (LEFT_PAD, bullet_y),
            f"\u2022  {wrapped}",
            font=font_body, fill=(20, 50, 130)
        )
        bullet_y += BULLET_LINE_H * (wrapped.count('\n') + 1) + 4

    img.save(output_filename)
    print(f"Generated Slide Image for scene {scene_idx} -> {output_filename}")
    return output_filename
