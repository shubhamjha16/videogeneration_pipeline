import os
import sys
sys.path.append(os.path.abspath("."))

from PIL import Image, ImageDraw, ImageFont

sub_to_norm = {
    '₀': '0', '₁': '1', '₂': '2', '₃': '3', '₄': '4',
    '₅': '5', '₆': '6', '₇': '7', '₈': '8', '₉': '9',
    '₊': '+', '₋': '-', '₌': '=', '₍': '(', '₎': ')',
    'ₐ': 'a', 'ₑ': 'e', 'ₕ': 'h', 'ᵢ': 'i', 'ⱼ': 'j',
    'ₖ': 'k', 'ₗ': 'l', 'ₘ': 'm', 'ₙ': 'n', 'ₒ': 'o',
    'ₚ': 'p', 'ᵣ': 'r', 'ₛ': 's', 'ₜ': 't', 'ᵤ': 'u',
    'ᵥ': 'v', 'ₓ': 'x', 'ᵧ': 'y'
}

sup_to_norm = {
    '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4',
    '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9',
    '⁺': '+', '⁻': '-', '⁼': '=', '⁽': '(', '⁾': ')',
    'ⁿ': 'n', 'ⁱ': 'i', 'ˣ': 'x', 'ʸ': 'y', 'ᵃ': 'a',
    'ᵇ': 'b', 'ᶜ': 'c', 'ᵈ': 'd', 'ᵉ': 'e', 'ᵍ': 'g',
    'ʰ': 'h', 'ʲ': 'j', 'ᵏ': 'k', 'ˡ': 'l', 'ᵐ': 'm',
    'ᵒ': 'o', 'ᵖ': 'p', 'ʳ': 'r', 'ˢ': 's', 'ᵗ': 't',
    'ᵘ': 'u', 'ᵛ': 'v', 'ʷ': 'w', 'ᶻ': 'z',
    'ᴬ': 'A', 'ᴮ': 'B', 'ᴰ': 'D', 'ᴱ': 'E', 'ᴳ': 'G',
    'ᴴ': 'H', 'ᴵ': 'I', 'ᴶ': 'J', 'ᴲ': 'K', 'ᴸ': 'L',
    'ᴹ': 'M', 'ᴺ': 'N', 'ᴼ': 'O', 'ᴾ': 'P', 'ᴿ': 'R',
    'ᵀ': 'T', 'ᵁ': 'U', 'ᵂ': 'W'
}

def parse_rich_math(text: str):
    sub_chars = "".join(sub_to_norm.keys())
    sup_chars = "".join(sup_to_norm.keys())
    
    segments = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == '∫':
            i += 1
            sub = ""
            sup = ""
            while i < n:
                char = text[i]
                if char in sub_chars:
                    sub += char
                    i += 1
                elif char in sup_chars:
                    sup += char
                    i += 1
                else:
                    break
            segments.append({
                "type": "integral",
                "sub": sub,
                "sup": sup
            })
        elif text[i:i+5] == "\\frac":
            i += 5
            while i < n and text[i].isspace():
                i += 1
            if i < n and text[i] == '{':
                i += 1
                num = ""
                brace_count = 1
                while i < n and brace_count > 0:
                    if text[i] == '{':
                        brace_count += 1
                        num += text[i]
                        i += 1
                    elif text[i] == '}':
                        brace_count -= 1
                        if brace_count > 0:
                            num += text[i]
                        i += 1
                    else:
                        num += text[i]
                        i += 1
                
                while i < n and text[i].isspace():
                    i += 1
                if i < n and text[i] == '{':
                    i += 1
                    den = ""
                    brace_count = 1
                    while i < n and brace_count > 0:
                        if text[i] == '{':
                            brace_count += 1
                            den += text[i]
                            i += 1
                        elif text[i] == '}':
                            brace_count -= 1
                            if brace_count > 0:
                                den += text[i]
                            i += 1
                        else:
                            den += text[i]
                            i += 1
                    segments.append({
                        "type": "fraction",
                        "num": num,
                        "den": den
                    })
                else:
                    segments.append({
                        "type": "text",
                        "content": "\\frac{" + num + "}"
                    })
            else:
                segments.append({
                    "type": "text",
                    "content": "\\frac"
                })
        else:
            start = i
            while i < n and text[i] != '∫' and text[i:i+5] != "\\frac":
                i += 1
            segments.append({
                "type": "text",
                "content": text[start:i]
            })
    return segments

def measure_rich_math_width(draw, text, font):
    segments = parse_rich_math(text)
    width = 0
    for seg in segments:
        if seg["type"] == "text":
            content = seg["content"]
            try:
                width += draw.textlength(content, font=font)
            except Exception:
                width += len(content) * (font.size * 0.6)
        elif seg["type"] == "integral":
            try:
                int_w = draw.textlength("∫", font=font)
            except Exception:
                int_w = font.size * 0.5
            sub = seg["sub"]
            sup = seg["sup"]
            try:
                small_font = ImageFont.truetype(font.path, int(font.size * 0.6))
            except Exception:
                small_font = font
            sup_w = len(sup) * (small_font.size * 0.6)
            sub_w = len(sub) * (small_font.size * 0.6)
            width += int_w * 0.8 + max(sup_w, sub_w) + font.size * 0.1
        elif seg["type"] == "fraction":
            try:
                small_font = ImageFont.truetype(font.path, int(font.size * 0.75))
            except Exception:
                small_font = font
            num_w = measure_rich_math_width(draw, seg["num"], small_font)
            den_w = measure_rich_math_width(draw, seg["den"], small_font)
            width += max(num_w, den_w) + font.size * 0.2
    return width

def draw_rich_math_text(draw, xy, text, font, fill):
    segments = parse_rich_math(text)
    x, y = xy
    
    try:
        small_font = ImageFont.truetype(font.path, int(font.size * 0.6))
    except Exception:
        small_font = font
        
    for seg in segments:
        if seg["type"] == "text":
            content = seg["content"]
            if not content:
                continue
            draw.text((x, y), content, fill=fill, font=font)
            try:
                x += draw.textlength(content, font=font)
            except Exception:
                x += len(content) * (font.size * 0.6)
        elif seg["type"] == "integral":
            draw.text((x, y), "∫", fill=fill, font=font)
            try:
                int_w = draw.textlength("∫", font=font)
            except Exception:
                int_w = font.size * 0.5
                
            sub = seg["sub"]
            sup = seg["sup"]
            
            norm_sub = "".join(sub_to_norm.get(c, c) for c in sub)
            norm_sup = "".join(sup_to_norm.get(c, c) for c in sup)
            
            sup_w = 0
            if norm_sup:
                draw.text((x + int_w * 0.8, y - font.size * 0.15), norm_sup, fill=fill, font=small_font)
                try:
                    sup_w = draw.textlength(norm_sup, font=small_font)
                except Exception:
                    sup_w = len(norm_sup) * (small_font.size * 0.6)
            
            sub_w = 0
            if norm_sub:
                draw.text((x + int_w * 0.8, y + font.size * 0.45), norm_sub, fill=fill, font=small_font)
                try:
                    sub_w = draw.textlength(norm_sub, font=small_font)
                except Exception:
                    sub_w = len(norm_sub) * (small_font.size * 0.6)
            
            x += int_w * 0.8 + max(sup_w, sub_w) + font.size * 0.1
        elif seg["type"] == "fraction":
            try:
                frac_font = ImageFont.truetype(font.path, int(font.size * 0.75))
            except Exception:
                frac_font = font
                
            num_w = measure_rich_math_width(draw, seg["num"], frac_font)
            den_w = measure_rich_math_width(draw, seg["den"], frac_font)
            frac_w = max(num_w, den_w)
            
            # Numerator top centered
            num_x = x + (frac_w - num_w) / 2
            draw_rich_math_text(draw, (num_x, y - font.size * 0.35), seg["num"], frac_font, fill)
            
            # Denominator bottom centered
            den_x = x + (frac_w - den_w) / 2
            draw_rich_math_text(draw, (den_x, y + font.size * 0.45), seg["den"], frac_font, fill)
            
            # Line in middle
            line_y = y + font.size * 0.35
            line_thickness = max(1, int(font.size * 0.06))
            draw.line([(x - 2, line_y), (x + frac_w + 2, line_y)], fill=fill, width=line_thickness)
            
            x += frac_w + font.size * 0.2

def test_draw():
    img = Image.new("RGB", (800, 200), "#F5F8F8")
    draw = ImageDraw.Draw(img)
    
    font_path = "/Library/Fonts/Arial Unicode.ttf"
    if not os.path.exists(font_path):
        font_path = "/System/Library/Fonts/Helvetica.ttc"
        
    font = ImageFont.truetype(font_path, 28)
    
    # Test containing BOTH vertical stacked integral AND vertical stacked fraction!
    text = "If f(x) = ∫₁ˣ \\frac{ln t}{1+t} dt, then find..."
    print(f"Drawing rich text: {text}")
    
    draw_rich_math_text(draw, (40, 80), text, font, "#0D7A7F")
    
    output_path = "scratch/rich_math_fraction_test.png"
    img.save(output_path)
    print(f"Saved rendered rich fraction test image to: {output_path}")

if __name__ == "__main__":
    test_draw()
