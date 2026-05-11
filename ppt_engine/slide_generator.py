"""
Doodle Slide Generator — EaseToLearn Brand Style
Renders 1920x1080 PNG slides with 16 layout types.

Core layouts:
  chaos_chapter   — high-impact chapter opener (EaseToLearn thumbnail style)
  title_card      — big title + subtitle (opening)
  bullets         — heading + 2-4 bullet points
  big_statement   — single powerful statement, large centered text
  steps           — numbered 1,2,3,4 process flow
  two_column      — left concept + right example/detail
  key_highlight   — dark card, one big key fact in white
  summary         — checkmarks + key takeaways (closing)

Expanded layouts:
  timeline        — horizontal timeline with dated events
  quote_card      — large centered quote with attribution
  stats_dashboard — 3-4 big numbers in boxes
  definition_card — term + definition + example
  before_after    — two-panel red/green contrast
  callout_box     — warning/tip/note/important box with icon
  ranking_list    — top 3-5 numbered ranking with medal colors
  image_hero      — cinematic dark full-frame slide with large title
"""

from PIL import Image, ImageDraw, ImageFont
import textwrap
import os
import re
import math
import random

W, H = 1920, 1080

_FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts")

# ── Fonts ──────────────────────────────────────────────────────────────────────

def _font(bold=False, size=24):
    candidates = [
        # Brand Font (Manual Asset - MUST BE IN assets/fonts/ - Priority)
        os.path.join(_FONT_DIR, "Caveat-Bold.ttf" if bold else "Caveat-Regular.ttf"),

        # Linux / ECS Production Paths
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        
        # Mac / System Fallbacks
        "/Library/Fonts/Arial{}.ttf".format(" Bold" if bold else ""),
        "/System/Library/Fonts/Supplemental/Arial{}.ttf".format(" Bold" if bold else ""),
        "/System/Library/Fonts/Helvetica.ttc",
    ]

    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


# ── Base canvas ────────────────────────────────────────────────────────────────

def _base_canvas(seed=0):
    """Create cream background with yellow accents and scattered decorations."""
    img = Image.new("RGB", (W, H), color=(255, 252, 230))
    draw = ImageDraw.Draw(img)

    # Gradient
    for y in range(H):
        ratio = y / H
        draw.line([(0, y), (W, y)], fill=(
            int(255 - ratio * 8),
            int(252 - ratio * 15),
            int(230 - ratio * 20)
        ))

    # Yellow side bars
    draw.rectangle([0, 0, 18, H], fill=(255, 200, 0))
    draw.rectangle([W - 18, 0, W, H], fill=(255, 200, 0))

    # Decorations
    rng = random.Random(seed * 7 + 3)
    star_pos = [(60,50),(W-60,45),(40,H-50),(W-45,H-55),(W//2+180,35),(W//2-150,H-40)]
    star_cols = [(255,200,0),(255,220,50),(255,180,0)]
    for i,(x,y) in enumerate(star_pos):
        _draw_star(draw, x+rng.randint(-10,10), y+rng.randint(-8,8),
                   r=rng.randint(8,16), fill=star_cols[i%3])

    for x,y in [(W-30,120),(25,200),(W-25,H-130),(30,H-120)]:
        r = rng.randint(6,10)
        draw.ellipse([x-r,y-r,x+r,y+r], fill=(255,220,50), outline=(180,140,0), width=2)

    for x in range(120, W-120, 40):
        r = rng.randint(3,5)
        draw.ellipse([x-r,8-r,x+r,8+r], fill=(220,180,0))
        draw.ellipse([x-r,H-8-r,x+r,H-8+r], fill=(220,180,0))

    # Logo
    draw.text((40,22), "∞  EaseToLearn", font=_font(bold=True, size=28), fill=(40,40,40))

    return img, draw


def _narration_strip(img, draw, narration: str):
    """Dark strip at bottom with narration text."""
    if not narration or not narration.strip():
        return img, draw

    NAR_H = 120
    NAR_Y = H - NAR_H - 8

    overlay = Image.new("RGBA", (W, NAR_H), (25, 20, 15, 225))
    img = img.convert("RGBA")
    img.paste(overlay, (0, NAR_Y), overlay)
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, NAR_Y, 12, NAR_Y + NAR_H], fill=(255, 200, 0))

    nar_font = _font(bold=False, size=40)
    wrapped = textwrap.fill(narration.strip(), width=100)
    lines = wrapped.split('\n')[:2]
    ty = NAR_Y + (NAR_H - len(lines) * 50) // 2
    for line in lines:
        draw.text((32, ty), line, font=nar_font, fill=(255, 252, 220))
        ty += 50

    # Brand
    draw.text((W-40, H-12), "www.easetolearn.com",
              font=_font(bold=False, size=26), fill=(255, 255, 255), anchor="rs")
    return img, draw


# ── Doodle helpers ─────────────────────────────────────────────────────────────

def _draw_wobbly_rect(draw, x0, y0, x1, y1, outline=(30,30,30), fill=None, width=3):
    w = 4
    pts = [(x0+w,y0),(x1-w,y0+w//2),(x1,y0+w),(x1-w//2,y1-w),
           (x1-w,y1),(x0+w,y1-w//2),(x0,y1-w),(x0+w//2,y0+w)]
    if fill:
        draw.polygon(pts, fill=fill)
    draw.line(pts+[pts[0]], fill=outline, width=width)


def _draw_star(draw, cx, cy, r=10, fill=(255,200,0)):
    pts = []
    for i in range(10):
        angle = math.pi * i / 5 - math.pi / 2
        radius = r if i % 2 == 0 else r * 0.4
        pts.append((cx + radius*math.cos(angle), cy + radius*math.sin(angle)))
    draw.polygon(pts, fill=fill, outline=(200,150,0))


def _draw_arrow(draw, x0, y0, x1, y1, color=(50,50,50), width=3):
    draw.line([(x0,y0),(x1,y1)], fill=color, width=width)
    angle = math.atan2(y1-y0, x1-x0)
    for a in [angle+2.5, angle-2.5]:
        draw.line([(x1,y1),(x1-12*math.cos(a), y1-12*math.sin(a))], fill=color, width=width)


# ── Layout renderers ───────────────────────────────────────────────────────────

def _layout_title_card(draw, img, data: dict):
    """Big centered title + subtitle. Opening slide."""
    title    = data.get("title", "")
    subtitle = data.get("subtitle", "")

    # Big decorative circle behind title
    cx, cy = W//2, H//2 - 80
    for r in [320, 290]:
        alpha = 30 if r == 320 else 50
        overlay = Image.new("RGBA", (W, H), (0,0,0,0))
        od = ImageDraw.Draw(overlay)
        od.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(255,200,0,alpha))
        img = img.convert("RGBA")
        img.paste(overlay, (0,0), overlay)
        img = img.convert("RGB")
        draw = ImageDraw.Draw(img)

    # Title
    title_font = _font(bold=True, size=120)
    wrapped = textwrap.fill(title, width=28)
    lines = wrapped.split('\n')
    ty = H//2 - len(lines)*65 - 40
    for line in lines:
        bbox = draw.textbbox((0,0), line, font=title_font)
        tw = bbox[2] - bbox[0]
        draw.text(((W-tw)//2, ty), line, font=title_font, fill=(20,20,20))
        ty += 130

    # Yellow underline
    draw.rectangle([W//2-200, ty+10, W//2+200, ty+18], fill=(255,200,0))

    # Subtitle
    if subtitle:
        sub_font = _font(bold=False, size=60)
        bbox = draw.textbbox((0,0), subtitle, font=sub_font)
        sw = bbox[2] - bbox[0]
        draw.text(((W-sw)//2, ty+40), subtitle, font=sub_font, fill=(80,60,30))

    return img, draw


def _layout_bullets(draw, img, data: dict):
    """Heading + 2-4 bullet points with numbered yellow circles."""
    heading = data.get("heading", "")
    bullets = data.get("bullets", [])[:4]

    # Heading card
    title_font = _font(bold=True, size=82)
    wrapped_h = textwrap.fill(heading, width=42)
    h_lines = wrapped_h.split('\n')
    card_h = len(h_lines) * 88 + 40
    _draw_wobbly_rect(draw, 60, 90, W-60, 90+card_h, outline=(30,30,30), fill=(255,255,255), width=4)
    ty = 110
    for line in h_lines:
        draw.text((80, ty), line, font=title_font, fill=(20,20,20))
        ty += 88
    draw.rectangle([80, ty+8, 480, ty+16], fill=(255,200,0))

    # Bullet cards
    bullet_start = 90 + card_h + 30
    cols = 2 if len(bullets) >= 3 else 1
    col_w = (W - 160) // cols
    bfont = _font(bold=False, size=56)

    for i, bullet in enumerate(bullets):
        col = i % cols
        row = i // cols
        bx = 60 + col * (col_w + 20)
        by = bullet_start + row * 170

        _draw_wobbly_rect(draw, bx, by, bx+col_w-10, by+155, outline=(30,30,30), fill=(255,255,255), width=3)

        # Number circle
        draw.ellipse([bx+14, by+48, bx+86, by+120], fill=(255,200,0), outline=(30,30,30), width=3)
        draw.text((bx+50, by+84), str(i+1), font=_font(bold=True, size=46), fill=(20,20,20), anchor="mm")

        # Text
        max_chars = max(18, int((col_w-110)/28))
        wrapped = textwrap.fill(bullet, width=max_chars)
        lines = wrapped.split('\n')
        lty = by + 84 - (len(lines)*58)//2
        for line in lines[:2]:
            draw.text((bx+100, lty), line, font=bfont, fill=(30,30,30))
            lty += 58

    return img, draw


def _layout_big_statement(draw, img, data: dict):
    """Single powerful statement — large centered text with white card, dark text."""
    statement = data.get("statement", "")
    context   = data.get("context", "")

    # White card (not yellow — text is dark so needs contrast)
    cx, cy = W//2, H//2 - 60
    box_w, box_h = W - 160, 260
    _draw_wobbly_rect(draw, (W-box_w)//2, cy-box_h//2,
                      (W+box_w)//2, cy+box_h//2,
                      outline=(30,30,30), fill=(255,255,255), width=5)

    # Yellow left accent bar inside card
    draw.rectangle([(W-box_w)//2, cy-box_h//2, (W-box_w)//2+14, cy+box_h//2], fill=(255,200,0))

    # Statement text — dark on white
    st_font = _font(bold=True, size=88)
    wrapped = textwrap.fill(statement, width=36)
    lines = wrapped.split('\n')
    ty = cy - (len(lines) * 96) // 2
    for line in lines:
        bbox = draw.textbbox((0,0), line, font=st_font)
        tw = bbox[2] - bbox[0]
        draw.text(((W-tw)//2, ty), line, font=st_font, fill=(20,20,20))
        ty += 96

    # Context below card — wrapped, centered
    if context:
        ctx_font = _font(bold=False, size=52)
        ctx_wrapped = textwrap.fill(context, width=70)
        ctx_lines = ctx_wrapped.split('\n')
        cty = cy + box_h//2 + 30
        for cl in ctx_lines[:2]:
            bbox = draw.textbbox((0,0), cl, font=ctx_font)
            cw = bbox[2] - bbox[0]
            draw.text(((W-cw)//2, cty), cl, font=ctx_font, fill=(60,45,15))
            cty += 60

    return img, draw


def _layout_steps(draw, img, data: dict):
    """Numbered step-by-step process — horizontal flow."""
    heading = data.get("heading", "")
    steps   = data.get("steps", [])[:4]

    # Heading
    hfont = _font(bold=True, size=76)
    draw.text((W//2, 100), heading, font=hfont, fill=(20,20,20), anchor="mm")
    draw.rectangle([W//2-250, 148, W//2+250, 156], fill=(255,200,0))

    if not steps:
        return img, draw

    # Step boxes in a horizontal row with arrows
    step_w = min(380, (W - 160) // len(steps) - 40)
    step_h = 340
    total_w = len(steps) * step_w + (len(steps)-1) * 60
    start_x = (W - total_w) // 2
    sy = 220

    colors = [(255,220,50), (255,200,20), (240,170,0), (220,150,0)]

    for i, step in enumerate(steps):
        sx = start_x + i * (step_w + 60)

        # Step card
        _draw_wobbly_rect(draw, sx, sy, sx+step_w, sy+step_h,
                          outline=(30,30,30), fill=(255,255,255), width=4)

        # Step number circle (top center of card)
        ncx = sx + step_w//2
        ncy = sy + 60
        draw.ellipse([ncx-48, ncy-48, ncx+48, ncy+48], fill=colors[i%4], outline=(30,30,30), width=4)
        draw.text((ncx, ncy), str(i+1), font=_font(bold=True, size=56), fill=(20,20,20), anchor="mm")

        # Step text — truncate to fit card width
        sfont = _font(bold=False, size=44)
        max_chars = max(12, int(step_w / 26))
        wrapped = textwrap.fill(step, width=max_chars)
        lines = wrapped.split('\n')[:3]
        lty = ncy + 75
        for line in lines:
            bbox = draw.textbbox((0,0), line, font=sfont)
            lw = bbox[2] - bbox[0]
            # Ensure text doesn't overflow card
            if lw > step_w - 20:
                line = line[:max(5, int(step_w/28))] + "…"
                bbox = draw.textbbox((0,0), line, font=sfont)
                lw = bbox[2] - bbox[0]
            draw.text((sx + (step_w - lw)//2, lty), line, font=sfont, fill=(30,30,30))
            lty += 52

        # Arrow between steps
        if i < len(steps)-1:
            ax = sx + step_w + 10
            ay = sy + step_h//2
            _draw_arrow(draw, ax, ay, ax+40, ay, color=(80,60,20), width=4)

    return img, draw


def _layout_two_column(draw, img, data: dict):
    """Left: concept/question. Right: detail/answer."""
    heading     = data.get("heading", "")
    left_title  = data.get("left_title", "")
    left_points = data.get("left_points", [])[:3]
    right_title = data.get("right_title", "")
    right_points= data.get("right_points", [])[:3]

    # Heading
    hfont = _font(bold=True, size=76)
    draw.text((W//2, 90), heading, font=hfont, fill=(20,20,20), anchor="mm")
    draw.rectangle([W//2-220, 136, W//2+220, 144], fill=(255,200,0))

    col_w = (W-200)//2
    col_h = H - 260
    left_x  = 60
    right_x = W//2 + 40

    for col_x, title, points, col_color in [
        (left_x,  left_title,  left_points,  (255,240,180)),
        (right_x, right_title, right_points, (200,230,255)),
    ]:
        # Column card
        _draw_wobbly_rect(draw, col_x, 170, col_x+col_w-20, 170+col_h,
                          outline=(30,30,30), fill=col_color, width=4)

        # Column title
        tfont = _font(bold=True, size=60)
        draw.text((col_x+20, 190), title, font=tfont, fill=(30,30,30))
        draw.rectangle([col_x+20, 258, col_x+200, 264], fill=(30,30,30))

        # Points
        pfont = _font(bold=False, size=50)
        py = 285
        for pt in points:
            wrapped = textwrap.fill(pt, width=28)
            for line in wrapped.split('\n')[:2]:
                draw.text((col_x+30, py), f"• {line}", font=pfont, fill=(30,30,30))
                py += 58
            py += 10

    return img, draw


def _layout_key_highlight(draw, img, data: dict):
    """One BIG key fact — dark card, white text, yellow accent."""
    label   = data.get("label", "Key Fact")
    fact    = data.get("fact", "")
    detail  = data.get("detail", "")

    # Dark card (high contrast — white text on dark)
    card_m = 80
    _draw_wobbly_rect(draw, card_m, 150, W-card_m, H-170,
                      outline=(255,200,0), fill=(30,25,20), width=6)

    # Yellow label badge — dark text on yellow (readable)
    badge_font = _font(bold=True, size=44)
    label_text = label.upper()
    bbox = draw.textbbox((0,0), label_text, font=badge_font)
    bw = bbox[2]-bbox[0] + 60
    draw.rounded_rectangle([W//2-bw//2, 118, W//2+bw//2, 182],
                            radius=20, fill=(255,200,0), outline=(30,30,30), width=3)
    draw.text((W//2, 150), label_text, font=badge_font, fill=(20,20,20), anchor="mm")

    # Fact text — WHITE on dark card
    fact_font = _font(bold=True, size=96)
    wrapped = textwrap.fill(fact, width=32)
    lines = wrapped.split('\n')
    ty = H//2 - (len(lines)*106)//2 - 10
    for line in lines:
        bbox = draw.textbbox((0,0), line, font=fact_font)
        fw = bbox[2]-bbox[0]
        draw.text(((W-fw)//2, ty), line, font=fact_font, fill=(255,252,220))
        ty += 106

    # Detail — yellow on dark
    if detail:
        det_font = _font(bold=False, size=50)
        det_wrapped = textwrap.fill(detail, width=60)
        det_lines = det_wrapped.split('\n')
        dty = ty + 20
        for dl in det_lines[:2]:
            bbox = draw.textbbox((0,0), dl, font=det_font)
            dw = bbox[2]-bbox[0]
            draw.text(((W-dw)//2, dty), dl, font=det_font, fill=(255,220,100))
            dty += 58

    return img, draw


def _layout_summary(draw, img, data: dict):
    """Closing slide — checkmarks + key takeaways."""
    heading = data.get("heading", "Key Takeaways")
    points  = data.get("points", [])[:4]

    # Heading
    hfont = _font(bold=True, size=88)
    bbox = draw.textbbox((0,0), heading, font=hfont)
    hw = bbox[2]-bbox[0]
    draw.text(((W-hw)//2, 80), heading, font=hfont, fill=(20,20,20))
    draw.rectangle([(W-hw)//2, 174, (W+hw)//2, 184], fill=(255,200,0))

    # Takeaway cards with checkmarks
    pfont = _font(bold=False, size=58)
    py = 230
    for pt in points:
        card_h = 130
        _draw_wobbly_rect(draw, 80, py, W-80, py+card_h,
                          outline=(30,30,30), fill=(255,255,255), width=3)

        # Green check circle
        draw.ellipse([100, py+25, 170, py+95], fill=(60,180,60), outline=(30,30,30), width=3)
        # Use text "OK" instead of unicode checkmark for font compatibility
        draw.text((135, py+60), "OK", font=_font(bold=True, size=32), fill=(255,255,255), anchor="mm")

        # Point text — wrapped safely
        wrapped = textwrap.fill(pt, width=62)
        pt_lines = wrapped.split('\n')
        lty = py + card_h//2 - (len(pt_lines[:2]) * 32)
        for pl in pt_lines[:2]:
            draw.text((190, lty), pl, font=pfont, fill=(30,30,30))
            lty += 58

        py += card_h + 18

    return img, draw


def _draw_scribble_chaos(draw, W, H, seed):
    """Draws chaotic black scribbles, swirls, and question marks on the left."""
    import math
    rng = random.Random(seed)
    
    # Random Bezier / Spline approximations for scribbles
    for _ in range(80):
        # random cluster centers on the left side
        cx = rng.randint(-50, W//2 - 100)
        cy = rng.randint(-50, H + 50)
        
        # draw a random swirl
        r = rng.randint(40, 160)
        start = rng.randint(0, 360) 
        end = start + rng.randint(180, 500)
        width = rng.randint(3, 8)
        draw.arc([cx-r, cy-r, cx+r, cy+r], start, end, fill=(30, 30, 30), width=width)
        
        # occasionally draw small circles
        if rng.random() > 0.7:
            sr = rng.randint(10, 40)
            draw.ellipse([cx-sr, cy-sr, cx+sr, cy+sr], outline=(30, 30, 30), width=rng.randint(2, 5))
            
    # Draw question marks floating around
    q_font = _font(bold=True, size=150)
    for _ in range(15):
        qx = rng.randint(20, W//2 - 150)
        qy = rng.randint(50, H - 150)
        draw.text((qx, qy), "?", font=q_font, fill=(30, 30, 30), anchor="mm")

def _layout_chaos_chapter(draw, img, data: dict):
    """High-impact opening mimicking the 'Chaos into Clarity' thumbnail."""
    chapter_num = data.get("number", "1")
    title       = data.get("title", "Modern Teaching\nChallenge")
    subtitle    = data.get("subtitle", "Chaos into Clarity")
    
    # 1. Solid Yellow Background (Overriding the cream gradient)
    draw.rectangle([0, 0, W, H], fill=(250, 210, 70))
    
    # 2. Chaos Scribbles on the left
    _draw_scribble_chaos(draw, W, H, seed=hash(title))
    
    # 3. Clean White Rounded Card on the right
    card_x = W // 3 - 50
    card_y = 150
    card_w = W - card_x - 100
    card_h = H - 300
    draw.rounded_rectangle([card_x, card_y, card_x + card_w, card_y + card_h], 
                           radius=80, fill=(255, 255, 255), outline=(30, 30, 30), width=8)
    
    # 4. Giant Outline Number
    num_font = _font(bold=True, size=700)
    # PIL text stroke requires simulating outline or using stroke_width
    draw.text((150, H//2), str(chapter_num), font=num_font, fill=(255, 255, 255),
              stroke_width=25, stroke_fill=(30, 30, 30), anchor="lm")
              
    # 5. Title Text inside Card — wrap to fit
    tfont = _font(bold=True, size=110)
    ty = card_y + 120
    max_w = card_w - 160  # leave margins
    for raw_line in title.split('\n'):
        wrapped = textwrap.fill(raw_line.strip(), width=18)
        for line in wrapped.split('\n'):
            # Shrink font until line fits
            f = tfont
            for sz in [110, 90, 75]:
                f = _font(bold=True, size=sz)
                bbox = draw.textbbox((0, 0), line, font=f)
                if (bbox[2] - bbox[0]) <= max_w:
                    break
            draw.text((card_x + 120, ty), line, font=f, fill=(30, 30, 30))
            ty += f.size + 20
        
    # 6. Subtitle — wrap and shrink to fit card
    sfont   = _font(bold=False, size=65)
    sub_ty  = ty + 20
    max_w   = card_w - 160
    wrapped = textwrap.fill(subtitle, width=30)
    sub_lines = wrapped.split('\n')
    last_line_w = 0
    for line in sub_lines:
        # shrink font if still too wide
        sf = sfont
        for sz in [65, 52, 42]:
            sf = _font(bold=False, size=sz)
            bbox = draw.textbbox((0, 0), line, font=sf)
            if (bbox[2] - bbox[0]) <= max_w:
                break
        draw.text((card_x + 120, sub_ty), line, font=sf, fill=(60, 60, 60))
        bbox = draw.textbbox((0, 0), line, font=sf)
        last_line_w = bbox[2] - bbox[0]
        sub_ty += sf.size + 8

    # Yellow underline under last subtitle line
    draw.rectangle([card_x + 120, sub_ty + 4, card_x + 120 + last_line_w, sub_ty + 14], fill=(255, 200, 0))

    return img, draw

# ── NEW LAYOUTS ────────────────────────────────────────────────────────────────

def _layout_timeline(draw, img, data: dict):
    """Horizontal timeline with 3-5 events. Great for history, wars, company growth."""
    heading = data.get("heading", "Timeline")
    events  = data.get("events", [])[:5]

    # Heading
    hfont = _font(bold=True, size=72)
    draw.text((80, 80), heading, font=hfont, fill=(20, 20, 20))
    draw.rectangle([80, 160, 400, 168], fill=(255, 200, 0))

    if not events:
        return img, draw

    # Timeline bar
    bar_y = H // 2 + 20
    bar_x0, bar_x1 = 120, W - 120
    draw.line([(bar_x0, bar_y), (bar_x1, bar_y)], fill=(60, 60, 60), width=4)
    _draw_arrow(draw, bar_x1 - 30, bar_y, bar_x1, bar_y, color=(60, 60, 60), width=4)

    spacing = (bar_x1 - bar_x0) // max(len(events), 1)

    for i, event in enumerate(events):
        if isinstance(event, str):
            label, desc = event, ""
        elif isinstance(event, dict):
            label = event.get("date") or event.get("label", f"Event {i+1}")
            desc  = event.get("description") or event.get("text", "")
        else:
            label, desc = str(event), ""

        cx = bar_x0 + spacing * i + spacing // 2

        # Dot on timeline
        draw.ellipse([cx - 12, bar_y - 12, cx + 12, bar_y + 12],
                     fill=(255, 200, 0), outline=(30, 30, 30), width=3)

        # Alternate above and below the timeline
        if i % 2 == 0:
            card_y = bar_y - 200
            draw.line([(cx, bar_y - 12), (cx, card_y + 90)], fill=(180, 180, 180), width=2)
        else:
            card_y = bar_y + 40
            draw.line([(cx, bar_y + 12), (cx, card_y)], fill=(180, 180, 180), width=2)

        # Event card
        card_w = spacing - 30
        _draw_wobbly_rect(draw, cx - card_w // 2, card_y, cx + card_w // 2, card_y + 90,
                          outline=(30, 30, 30), fill=(255, 255, 255), width=3)

        # Label (bold)
        lfont = _font(bold=True, size=32)
        wrapped_label = textwrap.shorten(label, width=18, placeholder="…")
        draw.text((cx - card_w // 2 + 10, card_y + 8), wrapped_label, font=lfont, fill=(30, 30, 30))

        # Description
        if desc:
            dfont = _font(bold=False, size=26)
            wrapped_desc = textwrap.shorten(desc, width=22, placeholder="…")
            draw.text((cx - card_w // 2 + 10, card_y + 48), wrapped_desc, font=dfont, fill=(80, 80, 80))

    return img, draw


def _layout_quote_card(draw, img, data: dict):
    """Large inspirational/impactful quote with attribution. Great for marketing."""
    quote      = data.get("quote", "")
    attribution = data.get("attribution", "")

    # Large yellow quotation mark
    qfont = _font(bold=True, size=300)
    draw.text((100, 60), "\u201c", font=qfont, fill=(255, 200, 0, 120))

    # Quote text — centered, large
    qtext_font = _font(bold=True, size=72)
    wrapped = textwrap.fill(quote, width=32)
    lines = wrapped.split('\n')[:5]

    total_h = len(lines) * 90
    ty = (H - total_h) // 2 - 40

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=qtext_font)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2, ty), line, font=qtext_font, fill=(30, 30, 30))
        ty += 90

    # Yellow accent line
    draw.rectangle([W // 2 - 150, ty + 20, W // 2 + 150, ty + 28], fill=(255, 200, 0))

    # Attribution
    if attribution:
        afont = _font(bold=False, size=48)
        attr_text = f"— {attribution}"
        bbox = draw.textbbox((0, 0), attr_text, font=afont)
        aw = bbox[2] - bbox[0]
        draw.text(((W - aw) // 2, ty + 50), attr_text, font=afont, fill=(100, 80, 40))

    # Closing quote mark
    draw.text((W - 250, H - 350), "\u201d", font=qfont, fill=(255, 220, 50, 80))

    return img, draw


def _layout_stats_dashboard(draw, img, data: dict):
    """3-4 big numbers in boxes. Great for data-heavy, business, impact slides."""
    heading = data.get("heading", "By The Numbers")
    stats   = data.get("stats", [])[:4]

    # Heading
    hfont = _font(bold=True, size=72)
    bbox = draw.textbbox((0, 0), heading, font=hfont)
    hw = bbox[2] - bbox[0]
    draw.text(((W - hw) // 2, 70), heading, font=hfont, fill=(20, 20, 20))
    draw.rectangle([(W - hw) // 2, 150, (W + hw) // 2, 158], fill=(255, 200, 0))

    if not stats:
        return img, draw

    # Stat boxes — arrange in a row
    n = len(stats)
    box_w = min(380, (W - 160) // n - 30)
    total_w = n * box_w + (n - 1) * 30
    start_x = (W - total_w) // 2
    box_y = 220

    for i, stat in enumerate(stats):
        if isinstance(stat, dict):
            value = str(stat.get("value", stat.get("number", "?")))
            label = stat.get("label", stat.get("text", ""))
        elif isinstance(stat, str):
            parts = stat.split(":", 1) if ":" in stat else [stat, ""]
            value, label = parts[0].strip(), parts[1].strip() if len(parts) > 1 else ""
        else:
            value, label = str(stat), ""

        bx = start_x + i * (box_w + 30)

        # Box with yellow top accent
        _draw_wobbly_rect(draw, bx, box_y, bx + box_w, box_y + 320,
                          outline=(30, 30, 30), fill=(255, 255, 255), width=4)
        draw.rectangle([bx + 4, box_y + 4, bx + box_w - 4, box_y + 14], fill=(255, 200, 0))

        # Big number
        vfont = _font(bold=True, size=90)
        value_short = textwrap.shorten(value, width=10, placeholder="…")
        vbbox = draw.textbbox((0, 0), value_short, font=vfont)
        vw = vbbox[2] - vbbox[0]
        draw.text((bx + (box_w - vw) // 2, box_y + 60), value_short, font=vfont, fill=(30, 30, 30))

        # Label
        if label:
            lfont = _font(bold=False, size=38)
            wrapped = textwrap.fill(label, width=16)
            llines = wrapped.split('\n')[:3]
            ly = box_y + 180
            for ll in llines:
                lbbox = draw.textbbox((0, 0), ll, font=lfont)
                lw = lbbox[2] - lbbox[0]
                draw.text((bx + (box_w - lw) // 2, ly), ll, font=lfont, fill=(80, 80, 80))
                ly += 44

    return img, draw


def _layout_definition_card(draw, img, data: dict):
    """Term + meaning + example. Great for educational, legal, medical."""
    term       = data.get("term", "")
    definition = data.get("definition", "")
    example    = data.get("example", "")

    # Yellow "DEFINITION" label
    label_font = _font(bold=True, size=36)
    draw.text((100, 80), "D E F I N I T I O N", font=label_font, fill=(180, 140, 0))

    # Term — large, bold
    tfont = _font(bold=True, size=100)
    wrapped_term = textwrap.fill(term, width=26)
    tlines = wrapped_term.split('\n')[:2]
    ty = 140
    for tl in tlines:
        draw.text((100, ty), tl, font=tfont, fill=(20, 20, 20))
        ty += 110

    # Yellow divider
    draw.rectangle([100, ty + 10, 500, ty + 18], fill=(255, 200, 0))

    # Definition in a white card
    card_y = ty + 50
    _draw_wobbly_rect(draw, 80, card_y, W - 80, card_y + 250,
                      outline=(30, 30, 30), fill=(255, 255, 255), width=3)

    dfont = _font(bold=False, size=52)
    wrapped_def = textwrap.fill(definition, width=55)
    dlines = wrapped_def.split('\n')[:4]
    dy = card_y + 30
    for dl in dlines:
        draw.text((120, dy), dl, font=dfont, fill=(50, 50, 50))
        dy += 58

    # Example in a subtle yellow-tinted box
    if example:
        ey = card_y + 280
        _draw_wobbly_rect(draw, 80, ey, W - 80, ey + 140,
                          outline=(200, 170, 50), fill=(255, 248, 210), width=3)
        efont_label = _font(bold=True, size=34)
        draw.text((120, ey + 12), "💡 Example:", font=efont_label, fill=(150, 120, 20))
        efont = _font(bold=False, size=42)
        ex_wrapped = textwrap.shorten(example, width=80, placeholder="…")
        draw.text((120, ey + 55), ex_wrapped, font=efont, fill=(80, 70, 30))

    return img, draw


def _layout_before_after(draw, img, data: dict):
    """Two-panel visual contrast. Great for marketing, case studies, transformations."""
    heading     = data.get("heading", "")
    before_title = data.get("before_title", "Before")
    before_points = data.get("before_points", [])[:3]
    after_title  = data.get("after_title", "After")
    after_points = data.get("after_points", [])[:3]

    # Heading
    if heading:
        hfont = _font(bold=True, size=68)
        bbox = draw.textbbox((0, 0), heading, font=hfont)
        hw = bbox[2] - bbox[0]
        draw.text(((W - hw) // 2, 70), heading, font=hfont, fill=(20, 20, 20))

    # Two panels
    panel_w = (W - 200) // 2
    panel_h = 520
    left_x, right_x = 70, W // 2 + 30
    panel_y = 180

    # BEFORE panel — grey/dull tint
    _draw_wobbly_rect(draw, left_x, panel_y, left_x + panel_w, panel_y + panel_h,
                      outline=(150, 100, 100), fill=(245, 235, 230), width=4)
    # Red "X" accent bar
    draw.rectangle([left_x + 4, panel_y + 4, left_x + panel_w - 4, panel_y + 14],
                   fill=(200, 80, 80))

    btfont = _font(bold=True, size=56)
    draw.text((left_x + 40, panel_y + 30), f"✗  {before_title}", font=btfont, fill=(150, 50, 50))

    bfont = _font(bold=False, size=44)
    by = panel_y + 110
    for bp in before_points:
        wrapped = textwrap.shorten(bp, width=34, placeholder="…")
        draw.text((left_x + 60, by), f"•  {wrapped}", font=bfont, fill=(100, 70, 70))
        by += 60

    # Arrow between panels
    arrow_y = panel_y + panel_h // 2
    _draw_arrow(draw, left_x + panel_w + 10, arrow_y, right_x - 10, arrow_y,
                color=(255, 200, 0), width=5)

    # AFTER panel — bright/energetic tint
    _draw_wobbly_rect(draw, right_x, panel_y, right_x + panel_w, panel_y + panel_h,
                      outline=(50, 150, 50), fill=(230, 250, 230), width=4)
    # Green accent bar
    draw.rectangle([right_x + 4, panel_y + 4, right_x + panel_w - 4, panel_y + 14],
                   fill=(80, 200, 80))

    atfont = _font(bold=True, size=56)
    draw.text((right_x + 40, panel_y + 30), f"✓  {after_title}", font=atfont, fill=(30, 120, 30))

    afont = _font(bold=False, size=44)
    ay = panel_y + 110
    for ap in after_points:
        wrapped = textwrap.shorten(ap, width=34, placeholder="…")
        draw.text((right_x + 60, ay), f"•  {wrapped}", font=afont, fill=(40, 100, 40))
        ay += 60

    return img, draw


def _layout_callout_box(draw, img, data: dict):
    """Warning/tip/note style card. Great for technical, how-to, important facts."""
    callout_type = data.get("type", "note").lower()   # "tip", "warning", "note", "important"
    heading      = data.get("heading", "")
    body         = data.get("body", "")

    # Style per type
    styles = {
        "tip":       {"icon": "💡", "accent": (80, 200, 80),  "bg": (230, 250, 230), "label": "PRO TIP"},
        "warning":   {"icon": "⚠️", "accent": (220, 160, 40), "bg": (255, 248, 220), "label": "WARNING"},
        "note":      {"icon": "📌", "accent": (80, 130, 200), "bg": (230, 240, 255), "label": "NOTE"},
        "important": {"icon": "🔥", "accent": (220, 80, 80),  "bg": (255, 235, 235), "label": "IMPORTANT"},
    }
    style = styles.get(callout_type, styles["note"])

    # Main card
    card_x, card_y = 120, 120
    card_w, card_h = W - 240, H - 320

    _draw_wobbly_rect(draw, card_x, card_y, card_x + card_w, card_y + card_h,
                      outline=style["accent"], fill=style["bg"], width=5)

    # Thick accent bar on left
    draw.rectangle([card_x, card_y, card_x + 12, card_y + card_h], fill=style["accent"])

    # Icon + Label
    icon_font = _font(bold=True, size=60)
    draw.text((card_x + 40, card_y + 30), style["icon"], font=icon_font, fill=(30, 30, 30))

    label_font = _font(bold=True, size=48)
    draw.text((card_x + 120, card_y + 38), style["label"], font=label_font, fill=style["accent"])

    # Heading
    if heading:
        hfont = _font(bold=True, size=72)
        wrapped_h = textwrap.fill(heading, width=36)
        hlines = wrapped_h.split('\n')[:2]
        hy = card_y + 120
        for hl in hlines:
            draw.text((card_x + 40, hy), hl, font=hfont, fill=(20, 20, 20))
            hy += 85

    # Body text
    if body:
        bfont = _font(bold=False, size=52)
        wrapped_b = textwrap.fill(body, width=48)
        blines = wrapped_b.split('\n')[:6]
        by = card_y + 300
        for bl in blines:
            draw.text((card_x + 40, by), bl, font=bfont, fill=(50, 50, 50))
            by += 62

    return img, draw


def _layout_ranking_list(draw, img, data: dict):
    """Top 3-5 numbered ranking with medal colors. Great for listicles, comparisons, top-N."""
    heading = data.get("heading", "Top Rankings")
    items   = data.get("items", [])[:5]

    # Heading
    hfont = _font(bold=True, size=76)
    bbox = draw.textbbox((0, 0), heading, font=hfont)
    hw = bbox[2] - bbox[0]
    draw.text(((W - hw) // 2, 65), heading, font=hfont, fill=(20, 20, 20))
    draw.rectangle([(W - hw) // 2, 150, (W + hw) // 2, 158], fill=(255, 200, 0))

    if not items:
        return img, draw

    # Medal colors for ranks 1-3, plain for the rest
    medal_colors = [(255, 200, 0), (192, 192, 192), (180, 120, 60)]
    rank_labels  = ["#1", "#2", "#3", "#4", "#5"]

    row_h = 115
    start_y = 185
    for i, item in enumerate(items):
        if isinstance(item, dict):
            label = item.get("label") or item.get("name") or item.get("title", f"Item {i+1}")
            detail = item.get("detail") or item.get("description") or item.get("score", "")
        else:
            label, detail = str(item), ""

        ry = start_y + i * (row_h + 14)
        row_fill = (255, 255, 255)

        # Row card
        _draw_wobbly_rect(draw, 80, ry, W - 80, ry + row_h,
                          outline=(30, 30, 30), fill=row_fill, width=3)

        # Rank badge
        badge_color = medal_colors[i] if i < 3 else (210, 210, 210)
        draw.ellipse([96, ry + 18, 96 + 76, ry + 18 + 76],
                     fill=badge_color, outline=(30, 30, 30), width=3)
        draw.text((96 + 38, ry + 18 + 38), rank_labels[i],
                  font=_font(bold=True, size=34), fill=(20, 20, 20), anchor="mm")

        # Label text
        lfont = _font(bold=True, size=54)
        label_short = textwrap.shorten(label, width=52, placeholder="…")
        draw.text((196, ry + 24), label_short, font=lfont, fill=(20, 20, 20))

        # Detail text
        if detail:
            dfont = _font(bold=False, size=38)
            detail_short = textwrap.shorten(str(detail), width=70, placeholder="…")
            draw.text((196, ry + 70), detail_short, font=dfont, fill=(100, 80, 40))

    return img, draw


def _layout_image_hero(draw, img, data: dict):
    """Cinematic full-frame dark slide — large title + tagline on rich gradient. No external image needed."""
    title   = data.get("title", "")
    tagline = data.get("tagline", "")
    context = data.get("context", "")

    # Dark cinematic gradient background (deep navy → near black)
    for y in range(H):
        ratio = y / H
        r = int(18  + ratio * 8)
        g = int(22  + ratio * 5)
        b = int(45  + ratio * 10)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Yellow horizontal stripe near the top
    draw.rectangle([0, 0, W, 8], fill=(255, 200, 0))

    # Scattered dots (star-field feel)
    rng = random.Random(hash(title) % 99999)
    for _ in range(120):
        sx = rng.randint(0, W)
        sy = rng.randint(0, H)
        sr = rng.randint(1, 3)
        alpha = rng.randint(100, 220)
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=(255, 255, 255, alpha))
        img = img.convert("RGBA")
        img.paste(overlay, (0, 0), overlay)
        img = img.convert("RGB")
        draw = ImageDraw.Draw(img)

    # Yellow accent bar on left edge
    draw.rectangle([0, 0, 12, H], fill=(255, 200, 0))

    # Big title — white on dark
    tfont = _font(bold=True, size=110)
    wrapped = textwrap.fill(title, width=26)
    tlines = wrapped.split('\n')
    ty = H // 2 - len(tlines) * 70 - 30
    for line in tlines:
        bbox = draw.textbbox((0, 0), line, font=tfont)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2, ty), line, font=tfont, fill=(255, 252, 220))
        ty += 128

    # Yellow underline
    draw.rectangle([W // 2 - 200, ty + 10, W // 2 + 200, ty + 18], fill=(255, 200, 0))

    # Tagline — yellow
    if tagline:
        tgfont = _font(bold=False, size=62)
        tg_wrapped = textwrap.fill(tagline, width=50)
        for line in tg_wrapped.split('\n')[:2]:
            bbox = draw.textbbox((0, 0), line, font=tgfont)
            lw = bbox[2] - bbox[0]
            draw.text(((W - lw) // 2, ty + 40), line, font=tgfont, fill=(255, 220, 80))
            ty += 70

    # Context — subtle grey
    if context:
        cfont = _font(bold=False, size=44)
        ctx_wrapped = textwrap.fill(context, width=70)
        cy2 = ty + 50
        for line in ctx_wrapped.split('\n')[:2]:
            bbox = draw.textbbox((0, 0), line, font=cfont)
            lw = bbox[2] - bbox[0]
            draw.text(((W - lw) // 2, cy2), line, font=cfont, fill=(180, 170, 140))
            cy2 += 54

    # Brand watermark
    draw.text((W - 40, H - 30), "www.easetolearn.com",
              font=_font(bold=False, size=26), fill=(120, 110, 80), anchor="rs")

    return img, draw


# ── Layout dispatcher ──────────────────────────────────────────────────────────

_LAYOUTS = {
    "title_card":       _layout_title_card,
    "bullets":          _layout_bullets,
    "big_statement":    _layout_big_statement,
    "steps":            _layout_steps,
    "two_column":       _layout_two_column,
    "key_highlight":    _layout_key_highlight,
    "summary":          _layout_summary,
    "chaos_chapter":    _layout_chaos_chapter,
    "timeline":         _layout_timeline,
    "quote_card":       _layout_quote_card,
    "stats_dashboard":  _layout_stats_dashboard,
    "definition_card":  _layout_definition_card,
    "before_after":     _layout_before_after,
    "callout_box":      _layout_callout_box,
    "ranking_list":     _layout_ranking_list,
    "image_hero":       _layout_image_hero,
}


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_slide_image(
    text: str,
    scene_idx: int,
    output_dir: str = ".",
    bg_image: str = None,
    narration: str = None,
    layout: str = "bullets",
    layout_data: dict = None,
    job_id: str = None,
) -> str:
    """
    Generate a doodle-style 1920x1080 slide PNG.

    Args:
        text        : Fallback text (used if layout_data not provided)
        scene_idx   : Slide number (used for seed + filename)
        output_dir  : Output folder
        bg_image    : Optional background image
        narration   : Narration text shown in bottom strip
        layout      : Layout type (title_card/bullets/big_statement/steps/two_column/key_highlight/summary)
        layout_data : Dict with layout-specific fields (heading, bullets, statement, etc.)
    """
    output_filename = os.path.join(output_dir, f"scene_{scene_idx}_slide.png")

    img, draw = _base_canvas(seed=scene_idx)

    # Build layout_data from plain text if not provided
    if not layout_data:
        parts  = re.split(r'\.\s+(?=[A-Z])', text.strip())
        title  = parts[0].rstrip('.')
        bullets = [p.strip().rstrip('.') for p in parts[1:] if p.strip()]
        layout_data = {"heading": title, "bullets": bullets}
        layout = "bullets"

    # Render layout
    renderer = _LAYOUTS.get(layout, _layout_bullets)
    try:
        img, draw = renderer(draw, img, layout_data)
    except Exception as e:
        print(f"   ⚠️  Layout '{layout}' failed: {e} — falling back to bullets")
        img, draw = _layout_bullets(draw, img, layout_data)

    # Narration strip
    img, draw = _narration_strip(img, draw, narration)

    img.save(output_filename, quality=95)
    print(f"   Slide {scene_idx} [{layout}] → {output_filename}")
    return output_filename
