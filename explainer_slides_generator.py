import os
import re
import config
from moviepy.editor import (
    ImageClip, concatenate_videoclips, AudioFileClip
)
from tts_generator import generate_audio
from image_generator import generate_concept_image
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
        elif text[i] == '^':
            i += 1
            if i < n and text[i] == '{':
                i += 1
                content = ""
                brace_count = 1
                while i < n and brace_count > 0:
                    if text[i] == '{':
                        brace_count += 1
                        content += text[i]
                        i += 1
                    elif text[i] == '}':
                        brace_count -= 1
                        if brace_count > 0:
                            content += text[i]
                        i += 1
                    else:
                        content += text[i]
                        i += 1
                segments.append({
                    "type": "superscript",
                    "content": content
                })
            else:
                if i < n:
                    segments.append({
                        "type": "superscript",
                        "content": text[i]
                    })
                    i += 1
                else:
                    segments.append({
                        "type": "text",
                        "content": "^"
                    })
        elif text[i] == '_':
            i += 1
            if i < n and text[i] == '{':
                i += 1
                content = ""
                brace_count = 1
                while i < n and brace_count > 0:
                    if text[i] == '{':
                        brace_count += 1
                        content += text[i]
                        i += 1
                    elif text[i] == '}':
                        brace_count -= 1
                        if brace_count > 0:
                            content += text[i]
                        i += 1
                    else:
                        content += text[i]
                        i += 1
                segments.append({
                    "type": "subscript",
                    "content": content
                })
            else:
                if i < n:
                    segments.append({
                        "type": "subscript",
                        "content": text[i]
                    })
                    i += 1
                else:
                    segments.append({
                        "type": "text",
                        "content": "_"
                    })
        else:
            start = i
            while i < n and text[i] != '∫' and text[i:i+5] != "\\frac" and text[i] != '^' and text[i] != '_':
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
        elif seg["type"] == "superscript":
            try:
                small_font = ImageFont.truetype(font.path, int(font.size * 0.65))
            except Exception:
                small_font = font
            width += measure_rich_math_width(draw, seg["content"], small_font)
        elif seg["type"] == "subscript":
            try:
                small_font = ImageFont.truetype(font.path, int(font.size * 0.65))
            except Exception:
                small_font = font
            width += measure_rich_math_width(draw, seg["content"], small_font)
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
                draw.text((x + int_w * 0.8, y - font.size * 0.2), norm_sup, fill=fill, font=small_font)
                try:
                    sup_w = draw.textlength(norm_sup, font=small_font)
                except Exception:
                    sup_w = len(norm_sup) * (small_font.size * 0.6)
            
            sub_w = 0
            if norm_sub:
                draw.text((x + int_w * 0.8, y + font.size * 0.7), norm_sub, fill=fill, font=small_font)
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
            
            # Numerator top centered, shifted up clear of the line
            num_x = x + (frac_w - num_w) / 2
            num_y = y - font.size * 0.25 - 4
            draw_rich_math_text(draw, (num_x, num_y), seg["num"], frac_font, fill)
            
            # Denominator bottom centered, shifted down clear of the line
            den_x = x + (frac_w - den_w) / 2
            den_y = y + font.size * 0.5 + 4
            draw_rich_math_text(draw, (den_x, den_y), seg["den"], frac_font, fill)
            
            # Line in middle of standard line height
            line_y = y + font.size * 0.5
            line_thickness = max(1, int(font.size * 0.06))
            draw.line([(x - 2, line_y), (x + frac_w + 2, line_y)], fill=fill, width=line_thickness)
            
            x += frac_w + font.size * 0.2
        elif seg["type"] == "superscript":
            try:
                ss_font = ImageFont.truetype(font.path, int(font.size * 0.65))
            except Exception:
                ss_font = font
            draw_rich_math_text(draw, (x, y - font.size * 0.25), seg["content"], ss_font, fill)
            x += measure_rich_math_width(draw, seg["content"], ss_font)
        elif seg["type"] == "subscript":
            try:
                ss_font = ImageFont.truetype(font.path, int(font.size * 0.65))
            except Exception:
                ss_font = font
            draw_rich_math_text(draw, (x, y + font.size * 0.35), seg["content"], ss_font, fill)
            x += measure_rich_math_width(draw, seg["content"], ss_font)

def format_math_for_pillow(text: str) -> str:
    """
    Sanitizes and formats math text (LaTeX and plain notation) into premium,
    highly readable Unicode representation for Pillow rendering.
    Handles:
      - Superscripts: x^2 -> x², x^{10} -> x¹⁰, x^n -> xⁿ
      - Subscripts: x_1 -> x₁, a_{ij} -> aᵢⱼ, x_n -> xₙ
      - Fractions: \\frac{a}{b} -> a/b, \\frac{a+b}{2} -> (a+b)/2
      - Common LaTeX operators & Greek symbols: \\alpha, \\beta, \\theta, \\times, etc.
    """
    if not text:
        return text

    # Convert simple inline slash fractions (e.g. 1/2, 1/e, a/b) to LaTeX \frac format
    # so they are typeset vertically stacked by draw_rich_math_text
    text = re.sub(r'\b([0-9a-zA-Zα-ωΑ-Ω]+)\s*/\s*([0-9a-zA-Zα-ωΑ-Ω]+)\b', r'\\frac{\1}{\2}', text)

    # (Fractions are kept as raw \frac so draw_rich_math_text can typeset them vertically stacked)

    # --- 2. Greek and Mathematical LaTeX Commands
    greek_and_math_map = {
        r'\alpha': 'α',
        r'\beta': 'β',
        r'\gamma': 'γ',
        r'\delta': 'δ',
        r'\epsilon': 'ε',
        r'\zeta': 'ζ',
        r'\eta': 'η',
        r'\theta': 'θ',
        r'\iota': 'ι',
        r'\kappa': 'κ',
        r'\lambda': 'λ',
        r'\mu': 'μ',
        r'\nu': 'ν',
        r'\xi': 'ξ',
        r'\pi': 'π',
        r'\rho': 'ρ',
        r'\sigma': 'σ',
        r'\tau': 'τ',
        r'\upsilon': 'υ',
        r'\phi': 'φ',
        r'\chi': 'χ',
        r'\psi': 'ψ',
        r'\omega': 'ω',
        r'\Delta': 'Δ',
        r'\Omega': 'Ω',
        r'\Sigma': 'Σ',
        r'\Theta': 'Θ',
        r'\Phi': 'Φ',
        r'\times': '×',
        r'\div': '÷',
        r'\pm': '±',
        r'\cdot': '·',
        r'\infty': '∞',
        r'\approx': '≈',
        r'\neq': '≠',
        r'\leq': '≤',
        r'\geq': '≥',
        r'\to': '→',
        r'\leftarrow': '←',
        r'\rightarrow': '→',
        r'\leftrightarrow': '↔',
        r'\partial': '∂',
        r'\nabla': '∇',
        r'\sqrt': '√',
        r'\int': '∫',
        r'\ln': 'ln',
        r'\log': 'log',
        r'\sin': 'sin',
        r'\cos': 'cos',
        r'\tan': 'tan',
        r'\exp': 'exp',
        r'\,': ' ',
        r'\:': ' ',
        r'\;': ' ',
        r'\!': '',
        r'\quad': '  ',
        r'\qquad': '    ',
    }
    
    for cmd, char in greek_and_math_map.items():
        text = text.replace(cmd, char)

    # Clean up any residual LaTeX curly brackets around standard symbols, e.g., \sqrt{x} -> √{x} -> √x
    text = re.sub(r'√\s*\{([^}]+)\}', r'√\1', text)

    # --- 3. Unicode Superscript and Subscript Mapping
    superscript_map = {
        '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
        '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
        '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾',
        'n': 'ⁿ', 'i': 'ⁱ', 'x': 'ˣ', 'y': 'ʸ', 'a': 'ᵃ',
        'b': 'ᵇ', 'c': 'ᶜ', 'd': 'ᵈ', 'e': 'ᵉ', 'g': 'ᵍ',
        'h': 'ʰ', 'j': 'ʲ', 'k': 'ᵏ', 'l': 'ˡ', 'm': 'ᵐ',
        'o': 'ᵒ', 'p': 'ᵖ', 'r': 'ʳ', 's': 'ˢ', 't': 'ᵗ',
        'u': 'ᵘ', 'v': 'ᵛ', 'w': 'ʷ', 'z': 'ᶻ',
        'A': 'ᴬ', 'B': 'ᴮ', 'D': 'ᴰ', 'E': 'ᴱ', 'G': 'ᴳ',
        'H': 'ᴴ', 'I': 'ᴵ', 'J': 'ᴶ', 'K': 'ᴲ', 'L': 'ᴸ',
        'M': 'ᴹ', 'N': 'ᴺ', 'O': 'ᴼ', 'P': 'ᴾ', 'R': 'ᴿ',
        'T': 'ᵀ', 'U': 'ᵁ', 'W': 'ᵂ'
    }

    subscript_map = {
        '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
        '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
        '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎',
        'a': 'ₐ', 'e': 'ₑ', 'h': 'ₕ', 'i': 'ᵢ', 'j': 'ⱼ',
        'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ', 'o': 'ₒ',
        'p': 'ₚ', 'r': 'ᵣ', 's': 'ₛ', 't': 'ₜ', 'u': 'ᵤ',
        'v': 'ᵥ', 'x': 'ₓ', 'y': 'ᵧ'
    }

    def replace_superscript(match):
        inner = match.group(1)
        return "".join(superscript_map.get(c, c) for c in inner)

    def replace_subscript(match):
        inner = match.group(1)
        return "".join(subscript_map.get(c, c) for c in inner)

    # Resolve complex braces first: x^{10} or x_ {ij}
    # (Commented out to let parse_rich_math handle them natively with shifted smaller fonts)
    # text = re.sub(r'\^\s*\{([^}]+)\}', replace_superscript, text)
    # text = re.sub(r'_\s*\{([^}]+)\}', replace_subscript, text)

    # Resolve simple words/consecutive letters: x^2 or x_1 or x^10 or x_n
    # text = re.sub(r'\^\s*([0-9a-zA-Z]+)', replace_superscript, text)
    # text = re.sub(r'_\s*([0-9a-zA-Z]+)', replace_subscript, text)

    # Clean up standard LaTeX inline math delimiters ($) if present
    text = text.replace("$", "")
    text = text.replace(r"\(", "").replace(r"\)", "")
    
    return text

def render_explainer_mcq_slide(
    visual_type: str,
    visual_data: dict,
    output_path: str,
    avatar_type: str = None,
    with_avatar: bool = False,
    tony_pose_path: str = None
):
    """
    Renders high-contrast, premium, 100% correct MCQ Option Analysis slides
    locally using Pillow. This ensures absolute readability, mathematical accuracy,
    and a wowed academic/clinical interface matching the provided templates.
    """
    w, h = 1024, 1024
    
    has_tony = (avatar_type == "tony_cartoon" and with_avatar and tony_pose_path and os.path.exists(tony_pose_path))
    right_margin = 280 if has_tony else 40
    
    # 1. Background (Light Teal/Off-white grid background)
    img = Image.new("RGB", (w, h), "#F5F8F8")
    draw = ImageDraw.Draw(img)
    
    # Draw premium subtle grid lines
    grid_spacing = 40
    for x in range(0, w, grid_spacing):
        draw.line([(x, 0), (x, h)], fill="#EBF2F2", width=1)
    for y in range(0, h, grid_spacing):
        draw.line([(0, y), (w, y)], fill="#EBF2F2", width=1)
        
    # Draw dark teal border (consistent with provided templates)
    draw.rounded_rectangle([20, 20, w - 20, h - 20], radius=15, outline="#0D7A7F", width=4)
    
    def get_font(size, bold=False):
        paths = []
        if bold:
            paths = [
                "/Library/Fonts/Arial Unicode.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/Library/Fonts/Arial Bold.ttf",
                "/System/Library/Fonts/HelveticaNeue.dfont",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            ]
        else:
            paths = [
                "/Library/Fonts/Arial Unicode.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/Library/Fonts/Arial.ttf",
                "/System/Library/Fonts/Helvetica.dfont",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            ]
        for p in paths:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception as e:
                    print(f"⚠️ [explainer_slides] font load failed for {p}: {e}")
        return ImageFont.load_default()

        
    font_q = get_font(28, bold=True)
    font_opt = get_font(20, bold=False)
    font_opt_letter = get_font(24, bold=True)
    font_exp = get_font(18, bold=False)
    
    # 2. Get Question
    question = format_math_for_pillow(visual_data.get("question") or "Review the options below:")
    
    # Word wrap question
    def wrap_text(text, font, max_width):
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            test_line = " ".join(current_line + [word])
            try:
                tw = draw.textlength(test_line, font=font)
            except Exception as e:
                print(f"⚠️ [explainer_slides] textlength fallback: {e}")
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
        
    q_lines = wrap_text(question, font_q, w - right_margin - 80)
    
    # Draw question card
    draw.rounded_rectangle([40, 40, w - right_margin, 200], radius=15, fill="#EBF5F5", outline="#0D7A7F", width=2)
    q_y = 65
    for line in q_lines[:3]: # limit to 3 lines
        draw_rich_math_text(draw, (60, q_y), line, font_q, "#0D7A7F")
        q_y += 35
        
    # 3. Get Options
    raw_options = visual_data.get("options", {})
    if not raw_options:
        raw_options = {"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"}
        
    # Normalize options
    mapping = {
        "1": "A", "2": "B", "3": "C", "4": "D",
        "A": "A", "B": "B", "C": "C", "D": "D"
    }
    options = {}
    for k, v in raw_options.items():
        k_str = str(k).upper()
        std_key = mapping.get(k_str, k_str)
        options[std_key] = v
        
    opt_keys = ["A", "B", "C", "D"]
    
    # Determine the highlight, cross_out, or answer_reveal state of each card
    highlight_letter = str(visual_data.get("letter", "")).upper()
    cross_out_letters = [str(l).upper() for l in (visual_data.get("letters") or [])]
    if not cross_out_letters and visual_type == "cross_out":
        single_cross = str(visual_data.get("letter", "")).upper()
        if single_cross:
            cross_out_letters = [single_cross]
            
    is_reveal = (visual_type == "answer_reveal")
    
    # Smart check: if the explanation or correct_answer explicitly says "none of the above"
    correct_ans_val = str(visual_data.get("correct_answer", "")).strip().lower()
    explanation_val = str(visual_data.get("explanation", "")).strip().lower()
    is_none_of_above = False
    if is_reveal and (
        "none of the above" in explanation_val or 
        correct_ans_val in ["none", "none of the above"] or
        (not correct_ans_val and "none of the above" in explanation_val)
    ):
        is_none_of_above = True
        
    correct_letter = str(visual_data.get("letter", "")).upper() if (is_reveal and not is_none_of_above) else ""
    
    opt_y = 230
    for letter in opt_keys:
        opt_text = format_math_for_pillow(options.get(letter, f"Option {letter}"))
        
        # Determine styling based on state
        card_fill = "#FFFFFF"
        card_outline = "#E2E8F0"
        card_border_w = 2
        text_fill = "#1E293B"
        letter_fill = "#0D7A7F"
        draw_x_mark = False
        draw_check_mark = False
        
        if visual_type == "option_highlight" and letter == highlight_letter:
            card_fill = "#FEF2F2"
            card_outline = "#FCA5A5"
            card_border_w = 3
            letter_fill = "#DC2626"
            text_fill = "#991B1B"
            
        elif letter in cross_out_letters:
            card_fill = "#F8FAFC"
            card_outline = "#CBD5E1"
            card_border_w = 1
            letter_fill = "#94A3B8"
            text_fill = "#94A3B8"
            draw_x_mark = True
            
        elif is_reveal and letter == correct_letter:
            card_fill = "#F0FDF4"
            card_outline = "#4ADE80"
            card_border_w = 4
            letter_fill = "#16A34A"
            text_fill = "#14532D"
            draw_check_mark = True
            
        elif is_reveal and letter != correct_letter:
            card_fill = "#F8FAFC"
            card_outline = "#CBD5E1"
            card_border_w = 1
            letter_fill = "#94A3B8"
            text_fill = "#94A3B8"
            draw_x_mark = True
            
        # Draw option card rounded rectangle
        card_box = [40, opt_y, w - right_margin, opt_y + 120]
        draw.rounded_rectangle(card_box, radius=12, fill=card_fill, outline=card_outline, width=card_border_w)
        
        # Draw Letter Circle
        circle_box = [60, opt_y + 35, 110, opt_y + 85]
        draw.ellipse(circle_box, fill="#CBD5E1" if letter_fill == "#94A3B8" else "#EBF5F5", outline=card_outline)
        draw_rich_math_text(draw, (77, opt_y + 45), letter, font_opt_letter, letter_fill)
        
        # Draw Option Text
        opt_lines = wrap_text(opt_text, font_opt, w - right_margin - 200)
        line_y = opt_y + 40 if len(opt_lines) == 1 else opt_y + 25
        for line in opt_lines[:2]:
            draw_rich_math_text(draw, (140, line_y), line, font_opt, text_fill)
            line_y += 30
            
        # Draw dynamic status icons
        if draw_x_mark:
            draw.line([(w - right_margin - 60, opt_y + 40), (w - right_margin - 20, opt_y + 80)], fill="#EF4444", width=4)
            draw.line([(w - right_margin - 20, opt_y + 40), (w - right_margin - 60, opt_y + 80)], fill="#EF4444", width=4)
        elif draw_check_mark:
            draw.line([(w - right_margin - 55, opt_y + 60), (w - right_margin - 40, opt_y + 75)], fill="#22C55E", width=5)
            draw.line([(w - right_margin - 40, opt_y + 75), (w - right_margin - 20, opt_y + 45)], fill="#22C55E", width=5)
            
        opt_y += 140
        
    # 4. Draw explanation if reveal
    if is_reveal:
        explanation = format_math_for_pillow(visual_data.get("explanation") or "")
        if explanation:
            exp_lines = wrap_text(explanation, font_exp, w - right_margin - 80)
            exp_y = 810
            draw.rounded_rectangle([40, 790, w - right_margin, h - 40], radius=10, fill="#ECFDF5", outline="#34D399", width=2)
            
            if is_none_of_above:
                font_exp_bold = get_font(20, bold=True)
                draw_rich_math_text(draw, (60, exp_y), "Correct Answer: None of the above", font_exp_bold, "#047857")
                exp_y += 30
                
            for line in exp_lines[:4]:
                draw_rich_math_text(draw, (60, exp_y), line, font_exp, "#065F46")
                exp_y += 25
                
    # ─── TONY CARTOON AVATAR OVERLAY ─────────────────────────
    if has_tony:
        try:
            print(f"   [tony-mcq] compositing {os.path.basename(tony_pose_path)} onto MCQ slide")
            with Image.open(tony_pose_path) as pose:
                pose = pose.convert("RGBA")
                # Scale Tony to fit in the right-side vertical column
                # Vertical column: x = 760 to 1004 (width 244), y = 220 to 980
                target_w, target_h = 240, 360
                pose.thumbnail((target_w, target_h), Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.ANTIALIAS)
                
                overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
                actual_w, actual_h = pose.size
                
                # Center horizontally in the 240px slot (slot starts at x = 760)
                x = 760 + (240 - actual_w) // 2
                # Align bottom with the bottom of the card content (y = 980)
                y = 980 - actual_h
                
                print(f"   [tony-mcq] pasting at ({x}, {y}) size {pose.size}")
                overlay.paste(pose, (x, y))
                
                img_rgba = img.convert("RGBA")
                img = Image.alpha_composite(img_rgba, overlay).convert("RGB")
        except Exception as e:
            print(f"⚠️ [tony-mcq] failed to composite Tony: {e}")

    img.save(output_path)
    print(f"✅ Handcrafted MCQ slide ({visual_type}) rendered successfully to {output_path}")


def apply_logo_watermark(img_path: str, pose_name: str = None):
    """
    Pastes either the EaseToLearn logo or the resolved Tony AI pose variant
    as a semi-transparent brand watermark in the corner of the slide.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    watermark_path = None
    
    # 1. Contextual Lookup: Check if a specific Tony AI pose was resolved for this scene
    if pose_name:
        p_name = pose_name.lower().strip()
        if not p_name.startswith("tony_"):
            p_name = f"tony_{p_name}"
        if not p_name.endswith(".png"):
            p_name = f"{p_name}.png"
            
        candidate_path = os.path.join(base_dir, "tony_avatars_poses", p_name)
        if os.path.exists(candidate_path):
            watermark_path = candidate_path
            
    # 2. Fallback: Load standard high-DPI transparent logo
    if not watermark_path:
        watermark_path = os.path.join(base_dir, "assets", "logo.png")
        
    if not os.path.exists(watermark_path):
        return
        
    try:
        slide_img = Image.open(img_path).convert("RGBA")
        wt_img = Image.open(watermark_path).convert("RGBA")
        
        is_pose = "tony_" in os.path.basename(watermark_path)
        
        # Widescreen branding watermark sizing (miniature 90px for avatar bugs, 140px for logo bugs)
        target_width = 90 if is_pose else 140
        w_percent = (target_width / float(wt_img.size[0]))
        target_height = int((float(wt_img.size[1]) * float(w_percent)))
        wt_resized = wt_img.resize((target_width, target_height), Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.ANTIALIAS)
        
        # Reduce alpha channel for subtle, high-class broadcast watermarking
        r, g, b, a = wt_resized.split()
        a = a.point(lambda p: int(p * 0.45 if is_pose else p * 0.80))
        wt_resized = Image.merge("RGBA", (r, g, b, a))
        
        # Position logo: Top Right corner with 30px padding
        slide_w, slide_h = slide_img.size
        pos_x = slide_w - target_width - 30
        pos_y = 30
        
        # Paste logo using its alpha channel as a mask for perfect transparency rendering
        slide_img.paste(wt_resized, (pos_x, pos_y), wt_resized)
        
        # Save back as RGB
        slide_img.convert("RGB").save(img_path)
        print(f"💧 Context Watermark ({os.path.basename(watermark_path)}) successfully applied to: {os.path.basename(img_path)}")
    except Exception as e:
        print(f"⚠️ Failed to apply watermark to {img_path}: {e}")


def composite_tony_pose_whiteboard(
    base: Image.Image,
    pose_path: str,
    layout_type: str = "whiteboard"
) -> Image.Image:
    """
    Composites the Tony RGBA pose onto a square 1024x1024 whiteboard slide.
    Places him in the bottom-right corner (or bottom-left depending on layout).
    """
    if not pose_path or not os.path.exists(pose_path):
        return base
    
    # By default, for whiteboard slides, we place Tony in the bottom right corner.
    # W: 1024, H: 1024.
    # Tony should be about 250-280px wide and 300-320px high.
    # Bottom right: x = 1024 - 280 - 40 = 704, y = 1024 - 320 - 40 = 664.
    pos = (700, 660)
    size = (280, 320)
    
    if layout_type == "chaos_chapter":
        pos = (40, 660) # Bottom left
    
    try:
        print(f"   [tony] attempting whiteboard composite {os.path.basename(pose_path)} for layout {layout_type}")
        with Image.open(pose_path) as pose:
            pose = pose.convert("RGBA")
            # Resize keeping aspect ratio
            w, h = size
            pose.thumbnail((w, h), Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.ANTIALIAS)
            
            # Create transparent overlay same size as base
            overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
            
            # Center the thumbnail in the reserved slot
            actual_w, actual_h = pose.size
            x, y = pos
            # Adjust y to keep it on the bottom floor
            adjusted_y = y + (h - actual_h)
            
            print(f"   [tony] placing at ({x}, {adjusted_y}) with size {pose.size}")
            overlay.paste(pose, (x, adjusted_y))
            
            # Alpha composite onto base
            base_rgba = base.convert("RGBA")
            combined = Image.alpha_composite(base_rgba, overlay)
            return combined.convert("RGB")
    except Exception as e:
        print(f"   ❌ [tony] error in whiteboard composite: {e}")
        return base


def generate_explainer_slides_video(
    scenes: list, 
    output_dir: str, 
    topic: str, 
    job_id: str = None, 
    use_elevenlabs: bool = True, 
    subject: str = "default",
    avatar_type: str = None,
    with_avatar: bool = False
) -> tuple[str, dict]:
    """
    Explainer Slides Engine v2.0
    Generates a premium, numbered whiteboard sequence synced to ElevenLabs narration.
    """
    print(f"🎬 [Explainer Slides] Building premium whiteboard sequences for: {topic} (Subject: {subject})")
    
    clips = []
    audio_clips = []
    
    ledger = {
        "elevenlabs_chars": 0,
        "dalle_calls": 0
    }
    
    try:
        for i, scene in enumerate(scenes):
            v_type = scene["visual_type"]
            v_data = scene["visual_data"]
            narration = scene["narration_text"]
            
            # 1. Generate narration audio for timing
            print(f"   🎙️ Generating audio for slide {i+1}...")
            audio_path, char_count = generate_audio(narration, f"slide_{i}", output_dir=output_dir, job_id=job_id, use_elevenlabs=use_elevenlabs)
            audio_clip = AudioFileClip(audio_path)
            audio_clips.append(audio_clip)
            dur = audio_clip.duration
            ledger["elevenlabs_chars"] += char_count
            
            # 2. Build visual asset for this slide
            print(f"   🎨 Generating image for slide {i+1} ({v_type})...")
            img_filename = f"slide_{i}.png"
            img_path = os.path.join(output_dir, img_filename)
            
            # MCQ options-analysis visual types are drawn locally via Pillow for high legibility
            if v_type in ["mcq_layout", "option_highlight", "cross_out", "answer_reveal"]:
                # Resolve Tony pose path to pass directly to render_explainer_mcq_slide
                tony_pose_path = None
                if avatar_type == "tony_cartoon" and with_avatar:
                    pose_name = scene.get("tony_pose")
                    if pose_name:
                        if not pose_name.endswith(".png"):
                            pose_name = f"tony_{pose_name}.png"
                        tony_pose_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tony_avatars_poses", pose_name)
                        if not os.path.exists(tony_pose_path):
                            tony_pose_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tony_avatars_poses", "tony_desk_happy.png")
                    else:
                        tony_pose_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tony_avatars_poses", "tony_desk_happy.png")
                
                render_explainer_mcq_slide(v_type, v_data, img_path, avatar_type=avatar_type, with_avatar=with_avatar, tony_pose_path=tony_pose_path)
            else:
                # Core whiteboard slide contents
                title = v_data.get("title") or v_data.get("heading") or topic
                subtitle = v_data.get("subtitle", "")
                bullets = v_data.get("bullets", [])
                objects = v_data.get("objects", [])
                
                # Check for starts-with numeral sequence (e.g. "1. Systolic", "2. Diastolic")
                numeral = ""
                num_match = re.match(r"^(\d+)\.", title)
                if num_match:
                    numeral = num_match.group(1)
                
                slide_content = f"Title: {title}"
                if subtitle:
                    slide_content += f"\nSubtitle: {subtitle}"
                if bullets:
                    slide_content += f"\nKey Points: {', '.join(bullets)}"
                if objects:
                    slide_content += f"\nInclude doodle icons of: {', '.join(objects)}"
                
                # Inject precise numeral layout guidance so DALL-E draws correct slide numbers sequentially
                if numeral:
                    slide_content += f"\nNote: The giant numeral on the left side MUST be strictly the single character '{numeral}'. Make it highly visible, bold, and stylized."
                elif v_type == "title_card":
                    slide_content += f"\nNote: There should be no numeral on the left side. Focus on a beautiful clean educational title card layout."
                else:
                    slide_content += f"\nNote: There should be no numeral on the left side. Instead, draw a large textbook-quality clinical illustration on the left."
                
                img_path = generate_concept_image(
                    topic=slide_content,
                    subject=f"whiteboard_doodle_{subject}",
                    output_dir=output_dir,
                    filename=img_filename,
                    job_id=job_id
                )
                ledger["dalle_calls"] += 1
                
                # Composite Tony character onto DALL-E AI slides if active
                if avatar_type == "tony_cartoon" and with_avatar:
                    pose_name = scene.get("tony_pose")
                    if pose_name:
                        if not pose_name.endswith(".png"):
                            pose_name = f"tony_{pose_name}.png"
                        tony_pose_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tony_avatars_poses", pose_name)
                        if not os.path.exists(tony_pose_path):
                            tony_pose_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tony_avatars_poses", "tony_desk_happy.png")
                    else:
                        tony_pose_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tony_avatars_poses", "tony_desk_happy.png")
                    
                    if os.path.exists(tony_pose_path):
                        try:
                            print(f"   [tony-dalle] compositing pose '{os.path.basename(tony_pose_path)}' onto AI slide {img_path}")
                            with Image.open(img_path) as base_img:
                                composited_img = composite_tony_pose_whiteboard(base_img, tony_pose_path, layout_type=v_type)
                                composited_img.save(img_path)
                        except Exception as e:
                            print(f"⚠️ [tony-dalle] failed to composite Tony: {e}")
            
            # Apply watermark dynamically
            apply_logo_watermark(img_path, pose_name=scene.get("tony_pose"))
            
            # 3. Create clip
            slide_clip = ImageClip(img_path).set_duration(dur).set_audio(audio_clip)
            clips.append(slide_clip)
            
        # 4. Final Stitching
        print(f"   🎞️ Stitching {len(clips)} slides into final video...")
        final_video = concatenate_videoclips(clips, method="compose")
        
        safe_topic = re.sub(r'[^a-zA-Z0-9_\-]', '_', topic.lower().strip())[:50]
        output_path = os.path.join(output_dir, f"{safe_topic}_explainer_slides.mp4")
        
        # Write file
        final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", threads=4, logger=None)
        
        return output_path, ledger
        
    except Exception as e:
        print(f"   ❌ Explainer Slides Gen Error: {e}")
        raise e
    finally:
        # Cleanup clips
        for c in clips:
            try: c.close()
            except Exception as e: print(f"⚠️ [explainer_slides] clip close error: {e}")
        for a in audio_clips:
            try: a.close()
            except Exception as e: print(f"⚠️ [explainer_slides] audio clip close error: {e}")
