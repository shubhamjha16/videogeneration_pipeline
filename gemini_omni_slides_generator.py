import os
import re
import time
import base64
import config
from moviepy.editor import (
    VideoFileClip, concatenate_videoclips, AudioFileClip, ColorClip, ImageClip
)
from tts_generator import generate_audio
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

# ── Gemini prompts per subject (Premium NotebookLM 3D Video Style) ──────────

_GEMINI_PROMPTS = {
    "medical": (
        "A premium, cinematic 3D medical animation of {topic} in continuous motion. "
        "The scene features a beautiful, clean, muted off-white presentation whiteboard with a soft grid pattern. "
        "On the left, a highly detailed, glossy 3D clinical model of the anatomical structures dynamically pulsing, "
        "showing cellular flow, molecular bindings, or biological mechanisms in high fidelity. "
        "On the right, an elegant white rectangular card with rounded corners and a soft drop shadow displays crisp, "
        "legible academic text labels and dynamic guiding hand-drawn arrows. "
        "NotebookLM explainer video style, photorealistic 3D rendering, smooth camera zoom and pan, extremely clean, no watermarks."
    ),
    "physics": (
        "A premium 3D physics simulation video explaining {topic}. "
        "Clean off-white whiteboard background with a subtle coordinate grid. "
        "On the left, a photorealistic 3D physics demonstration in motion — electric fields flowing, particles colliding, "
        "or mechanical gears spinning with glossy textures and shiny directional vector arrows. "
        "On the right, a rounded academic card presenting neat equations and structures. "
        "3Blue1Brown aesthetic in motion, smooth fluid animation, cinematic 3D render, no watermarks."
    ),
    "maths": (
        "A stunning 3D advanced mathematical animation of {topic}. "
        "Muted off-white grid paper background. "
        "On the left, a beautiful 3D function shape or geometric structure rotating smoothly in space, "
        "revealing mathematical volumes and intersections with glossy gradient colors. "
        "On the right, perfectly legible formulas and integrals on a clean white card. "
        "Smooth rotating camera motion, photorealistic 3D render, textbook clarity, no watermarks."
    ),
    "chemistry": (
        "A cinematic 3D molecular reaction animation showing {topic}. "
        "Muted teal grid slate background. "
        "On the left, atoms and molecules smoothly combining, bonds forming with shiny covalent visual effects, "
        "and gloss-finished orbital spheres in dynamic rotation. "
        "On the right, a rounded card showing balanced equations and molecular symbols. "
        "High-fidelity chemistry simulation, smooth slow-motion camera, glossy 3D visuals, no watermarks."
    ),
    "default": (
        "A premium, professional 3D educational animation explaining {topic}. "
        "Muted off-white grid whiteboard background. "
        "On the left, a beautiful, highly detailed 3D infographic model showing the concept in motion, "
        "with smooth panning visuals and vibrant academic accent colors. "
        "On the right, a rounded card displays large, bold titles and clear guide arrows. "
        "NotebookLM podcast-style explainer video, smooth 3D render, high contrast, clean graphics, no watermarks."
    )
}


def _create_fallback_video(prompt: str, output_path: str, duration: float = 5.0):
    """Generates a high-quality fallback video clip with a dynamic pan effect if Gemini Video is unavailable."""
    w, h = 1280, 720
    img = Image.new("RGB", (w * 2, h), "#FAFBFB") # Create double-width canvas for pan effect
    draw = ImageDraw.Draw(img)

    # Grid
    grid_spacing = 40
    for x in range(0, w * 2, grid_spacing):
        draw.line([(x, 0), (x, h)], fill="#F0F4F4", width=1)
    for y in range(0, h, grid_spacing):
        draw.line([(0, y), (w * 2, y)], fill="#F0F4F4", width=1)

    def get_font(size, bold=False):
        paths = []
        if bold:
            paths = [
                "/Library/Fonts/Arial Unicode.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/Library/Fonts/Arial Bold.ttf",
            ]
        else:
            paths = [
                "/Library/Fonts/Arial Unicode.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/Library/Fonts/Arial.ttf",
            ]
        for p in paths:
            if os.path.exists(p):
                try: return ImageFont.truetype(p, size)
                except Exception: continue
        return ImageFont.load_default()

    font_title = get_font(42, bold=True)
    font_body = get_font(24, bold=False)

    title = "Educational Concept"
    title_match = re.search(r"Title:\s*(.*?)(?=\n|$)", prompt, re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()

    # Draw elements on first half
    draw.rounded_rectangle([40, 40, w - 40, 130], radius=12, fill="#EDF6F6", outline="#088A8F", width=2)
    draw.text((60, 60), title, fill="#1A3335", font=font_title)
    draw.rounded_rectangle([60, 180, 480, 600], radius=15, fill="#E6EEEE", outline="#088A8F", width=2)
    draw.ellipse([220, 320, 320, 420], fill="#FF8D3B", outline="#E25C00", width=3)
    draw.text((120, 480), "[ 3D Video Metaphor ]\n  (Generation fallback)", fill="#0D7A7F", font=get_font(24, bold=True))
    draw.rounded_rectangle([520, 180, w - 60, 600], radius=15, fill="#FFFFFF", outline="#E2E8F0", width=2)
    draw.text((550, 220), "NotebookLM Dynamic Slide", fill="#088A8F", font=get_font(28, bold=True))

    # Draw panned elements on second half
    draw.rounded_rectangle([w + 40, 40, w * 2 - 40, 130], radius=12, fill="#EDF6F6", outline="#088A8F", width=2)
    draw.text((w + 60, 60), title + " (Deep Dive)", fill="#1A3335", font=font_title)
    draw.rounded_rectangle([w + 60, 180, w + 480, 600], radius=15, fill="#E6EEEE", outline="#088A8F", width=2)
    draw.rectangle([w + 220, 320, w + 320, 420], fill="#3B82F6", outline="#1D4ED8", width=3) # Blue cube
    draw.text((w + 140, 480), "[ Dynamic 3D Detail ]", fill="#1D4ED8", font=get_font(24, bold=True))
    draw.rounded_rectangle([w + 520, 180, w * 2 - 60, 600], radius=15, fill="#FFFFFF", outline="#E2E8F0", width=2)
    draw.text((w + 550, 220), "Legible Textbook Formulas", fill="#059669", font=get_font(28, bold=True))

    temp_img_path = output_path.replace(".mp4", "_pano.png")
    img.save(temp_img_path)

    # Generate a sliding-window panning MP4 using MoviePy
    try:
        pano_clip = ImageClip(temp_img_path)
        # Create a dynamic pan from left to right over the duration of the audio
        def make_frame(t):
            x_offset = int((w / duration) * t)
            frame = pano_clip.get_frame(t)
            return frame[:, x_offset:x_offset + w, :]
        
        from moviepy.video.VideoClip import VideoClip
        pan_video = VideoClip(make_frame, duration=duration)
        pan_video.write_videofile(output_path, fps=24, codec="libx264", logger=None)
        pan_video.close()
        pano_clip.close()
    except Exception as e:
        print(f"⚠️ [explainer_slides] pano video generation failed: {e}, using static color fallback")
        fallback = ColorClip(size=(w, h), color=(15, 30, 60)).set_duration(duration)
        fallback.write_videofile(output_path, fps=24, codec="libx264", logger=None)
        fallback.close()

    if os.path.exists(temp_img_path):
        os.remove(temp_img_path)
    print(f"🎥 Dynamic sliding whiteboard fallback video saved: {output_path}")


def generate_gemini_omni_concept_video(
    topic: str,
    subject: str = "default",
    duration: float = 5.0,
    output_dir: str = ".",
    filename: str = None,
    job_id: str = None
) -> str:
    """
    Invokes Google's Gemini Omni video generation API (Omni) asynchronously
    to synthesize a dynamic 3D educational animation with custom duration.
    Falls back gracefully to a dynamic pan slide video on rate limit / failure.
    """
    template = _GEMINI_PROMPTS.get(subject, _GEMINI_PROMPTS["default"])
    prompt = template.format(topic=topic)

    os.makedirs(output_dir, exist_ok=True)
    safe_name = filename or (
        re.sub(r'[^a-zA-Z0-9_\-]', '_', topic.lower().strip())[:50]
        + "_gemini_omni.mp4"
    )
    output_path = os.path.join(output_dir, safe_name)

    api_key = config.GEMINI_API_KEY
    if not api_key:
        print("   ⚠️  GEMINI_API_KEY not configured. Falling back to dynamic local panning whiteboard...")
        _create_fallback_video(prompt, output_path, duration)
        return os.path.abspath(output_path)

    try:
        from google import genai
        from google.genai import types

        # Initialize client with v1alpha api_version to support Gemini Veo/Omni long-running video generation
        client = genai.Client(api_key=api_key, http_options={'api_version': 'v1alpha'})
        
        # Multi-model fallback list: try gemini-omni-flash first, fallback to veo-3.1-lite, veo-3.1-lite-preview, and veo-3.0-fast-generate-001
        candidate_models = ["gemini-omni-flash", "veo-3.1-lite", "veo-3.1-lite-preview", "veo-3.0-fast-generate-001"]
        operation = None
        last_err = None

        for model_name in candidate_models:
            try:
                print(f"   🎬 Requesting Gemini video generation via {model_name}...")
                operation = client.models.generate_videos(
                    model=model_name,
                    prompt=prompt,
                    config=types.GenerateVideosConfig(
                        aspect_ratio="16:9",
                        duration_seconds=int(max(4, min(duration, 8))), # clamp between 4s and 8s for API limits
                    ),
                )
                print(f"   ✅ Successfully scheduled operation with {model_name}!")
                break
            except Exception as e:
                err_msg = str(e)
                if "404" in err_msg or "NOT_FOUND" in err_msg or "not found" in err_msg.lower():
                    print(f"   ⚠️  Model {model_name} is not available/found. Trying next candidate...")
                    last_err = e
                    continue
                else:
                    raise e

        if not operation:
            if last_err:
                raise last_err
            else:
                raise RuntimeError("No suitable video generation model could be scheduled.")

        print(f"   ⏳ Video generation operation started. Polling for completion (Job: {job_id or 'local'})...")
        
        max_polls = 40
        for poll in range(max_polls):
            time.sleep(10)
            operation = client.operations.get(operation)
            if operation.done:
                break
            print(f"   ⏳ [Poll {poll+1}/{max_polls}] Generating video in progress...")

        if not operation.done or not operation.response or not operation.response.generated_videos:
            raise RuntimeError("Gemini Omni Video operation timed out or returned no video")

        video_uri = operation.response.generated_videos[0].video.uri
        video_bytes = operation.response.generated_videos[0].video.video_bytes
        if not video_bytes and video_uri:
            print(f"   📥 Downloading generated video from URI: {video_uri}...")
            import requests
            download_url = video_uri
            if "key=" not in download_url:
                separator = "&" if "?" in download_url else "?"
                download_url = f"{download_url}{separator}key={api_key}"
            resp = requests.get(download_url)
            resp.raise_for_status()
            video_bytes = resp.content

        if not video_bytes:
            raise RuntimeError("Failed to retrieve video bytes from operation response")

        with open(output_path, "wb") as f:
            f.write(video_bytes)

        print(f"✅ Gemini Omni 3D Explainer Video saved: {output_path}")

        # Record Cost entry for Gemini Omni Video Generation
        try:
            from cost_tracker import LedgerManager
            LedgerManager.record_veo_call(job_id, duration, model_name)
        except Exception as e:
            print(f"⚠️ Failed to record cost for Gemini Video call: {e}")


        return os.path.abspath(output_path)

    except Exception as e:
        print(f"   ⚠️ Gemini Omni Video Generation failed ({e}) — activating fallback panning animation")
        _create_fallback_video(prompt, output_path, duration)
        return os.path.abspath(output_path)


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
    text = re.sub(r'\^\s*\{([^}]+)\}', replace_superscript, text)
    text = re.sub(r'_\s*\{([^}]+)\}', replace_subscript, text)

    # Resolve simple words/consecutive letters: x^2 or x_1 or x^10 or x_n
    text = re.sub(r'\^\s*([0-9a-zA-Z]+)', replace_superscript, text)
    text = re.sub(r'_\s*([0-9a-zA-Z]+)', replace_subscript, text)

    # Clean up standard LaTeX inline math delimiters ($) if present
    text = text.replace("$", "")
    text = text.replace(r"\(", "").replace(r"\)", "")
    
    return text


def render_gemini_mcq_slide(
    visual_type: str,
    visual_data: dict,
    output_path: str,
    duration: float = 5.0
):
    """
    Renders high-contrast, premium MCQ Option Analysis slides matching the
    aesthetic structure of the NotebookLM whiteboard presentation layout.
    """
    w, h = 1280, 720 # Wide-screen aspect ratio standard
    
    # 1. Background (Teal slate background)
    img = Image.new("RGB", (w, h), "#F4F7F7")
    draw = ImageDraw.Draw(img)
    
    grid_spacing = 40
    for x in range(0, w, grid_spacing):
        draw.line([(x, 0), (x, h)], fill="#EBF2F2", width=1)
    for y in range(0, h, grid_spacing):
        draw.line([(0, y), (w, y)], fill="#EBF2F2", width=1)
        
    # Dark teal border frame
    draw.rounded_rectangle([20, 20, w - 20, h - 20], radius=15, outline="#088A8F", width=4)
    
    def get_font(size, bold=False):
        paths = []
        if bold:
            paths = [
                "/Library/Fonts/Arial Unicode.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/Library/Fonts/Arial Bold.ttf",
            ]
        else:
            paths = [
                "/Library/Fonts/Arial Unicode.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/Library/Fonts/Arial.ttf",
            ]
        for p in paths:
            if os.path.exists(p):
                try: return ImageFont.truetype(p, size)
                except Exception: continue
        return ImageFont.load_default()
        
    font_q = get_font(28, bold=True)
    font_opt = get_font(20, bold=False)
    font_opt_letter = get_font(24, bold=True)
    font_exp = get_font(18, bold=False)
    
    # 2. Get Question
    question = format_math_for_pillow(visual_data.get("question") or "Review the options below:")
    
    def wrap_text(text, font, max_width):
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            test_line = " ".join(current_line + [word])
            try:
                tw = draw.textlength(test_line, font=font)
            except Exception:
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
        
    q_lines = wrap_text(question, font_q, w - 120)
    
    # Draw question header card
    draw.rounded_rectangle([40, 40, w - 40, 160], radius=15, fill="#E5F4F4", outline="#088A8F", width=2)
    q_y = 55
    for line in q_lines[:3]:
        draw_rich_math_text(draw, (60, q_y), line, font_q, "#088A8F")
        q_y += 35
        
    # 3. Process Options
    raw_options = visual_data.get("options", {}) or {"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"}
    options = {}
    mapping = {"1": "A", "2": "B", "3": "C", "4": "D", "A": "A", "B": "B", "C": "C", "D": "D"}
    for k, v in raw_options.items():
        k_str = str(k).upper()
        options[mapping.get(k_str, k_str)] = v
        
    opt_keys = ["A", "B", "C", "D"]
    highlight_letter = str(visual_data.get("letter", "")).upper()
    cross_out_letters = [str(l).upper() for l in (visual_data.get("letters") or [])]
    if not cross_out_letters and visual_type == "cross_out":
        single_cross = str(visual_data.get("letter", "")).upper()
        if single_cross:
            cross_out_letters = [single_cross]
            
    is_reveal = (visual_type == "answer_reveal")
    correct_ans_val = str(visual_data.get("correct_answer", "")).strip().lower()
    explanation_val = str(visual_data.get("explanation", "")).strip().lower()
    
    is_none_of_above = False
    if is_reveal and ("none of the above" in explanation_val or correct_ans_val in ["none", "none of the above"]):
        is_none_of_above = True
        
    correct_letter = str(visual_data.get("letter", "")).upper() if (is_reveal and not is_none_of_above) else ""
    
    # 2x2 grid layout for widescreen options
    grid_positions = [
        (40, 180, 620, 360),    # A
        (660, 180, 1240, 360),  # B
        (40, 390, 620, 570),    # C
        (660, 390, 1240, 570)   # D
    ]
    
    for idx, letter in enumerate(opt_keys):
        opt_text = format_math_for_pillow(options.get(letter, f"Option {letter}"))
        pos = grid_positions[idx]
        
        card_fill = "#FFFFFF"
        card_outline = "#E2E8F0"
        card_border_w = 2
        text_fill = "#1E293B"
        letter_fill = "#088A8F"
        draw_x_mark = False
        draw_check_mark = False
        
        if visual_type == "option_highlight" and letter == highlight_letter:
            card_fill = "#FFFDF2"
            card_outline = "#FCD34D"
            card_border_w = 3
            letter_fill = "#D97706"
            text_fill = "#92400E"
            
        elif letter in cross_out_letters:
            card_fill = "#F1F5F9"
            card_outline = "#E2E8F0"
            card_border_w = 1
            letter_fill = "#94A3B8"
            text_fill = "#94A3B8"
            draw_x_mark = True
            
        elif is_reveal and letter == correct_letter:
            card_fill = "#ECFDF5"
            card_outline = "#34D399"
            card_border_w = 4
            letter_fill = "#059669"
            text_fill = "#064E3B"
            draw_check_mark = True
            
        elif is_reveal and letter != correct_letter:
            card_fill = "#F1F5F9"
            card_outline = "#E2E8F0"
            card_border_w = 1
            letter_fill = "#94A3B8"
            text_fill = "#94A3B8"
            draw_x_mark = True
            
        # Draw option card
        draw.rounded_rectangle(pos, radius=12, fill=card_fill, outline=card_outline, width=card_border_w)
        
        # Circle letter
        circle_box = [pos[0] + 20, pos[1] + 35, pos[0] + 70, pos[1] + 85]
        draw.ellipse(circle_box, fill="#E2E8F0" if letter_fill == "#94A3B8" else "#E5F4F4", outline=card_outline)
        draw_rich_math_text(draw, (pos[0] + 37, pos[1] + 45), letter, font_opt_letter, letter_fill)
        
        # Wrapped text
        opt_lines = wrap_text(opt_text, font_opt, pos[2] - pos[0] - 180)
        line_y = pos[1] + 40 if len(opt_lines) == 1 else pos[1] + 25
        for line in opt_lines[:2]:
            draw_rich_math_text(draw, (pos[0] + 90, line_y), line, font_opt, text_fill)
            line_y += 30
            
        # Draw markers
        if draw_x_mark:
            draw.line([(pos[2] - 60, pos[1] + 40), (pos[2] - 30, pos[1] + 70)], fill="#F87171", width=4)
            draw.line([(pos[2] - 30, pos[1] + 40), (pos[2] - 60, pos[1] + 70)], fill="#F87171", width=4)
        elif draw_check_mark:
            draw.line([(pos[2] - 55, pos[1] + 55), (pos[2] - 45, pos[1] + 65)], fill="#34D399", width=5)
            draw.line([(pos[2] - 45, pos[1] + 65), (pos[2] - 30, pos[1] + 35)], fill="#34D399", width=5)
            
    # 4. Explanation at the bottom
    temp_img_path = output_path.replace(".mp4", "_static.png")
    if is_reveal:
        explanation = format_math_for_pillow(visual_data.get("explanation") or "")
        if explanation:
            exp_lines = wrap_text(explanation, font_exp, w - 240)
            draw.rounded_rectangle([40, 590, w - 40, h - 30], radius=10, fill="#ECFDF5", outline="#34D399", width=2)
            exp_y = 605
            
            if is_none_of_above:
                font_exp_bold = get_font(20, bold=True)
                draw_rich_math_text(draw, (60, exp_y), "Correct Answer: None of the above", font_exp_bold, "#047857")
                exp_y += 25
                
            for line in exp_lines[:2]: # limit to 2 lines for widescreen bottom
                draw_rich_math_text(draw, (60, exp_y), line, font_exp, "#065F46")
                exp_y += 22
                
    img.save(temp_img_path)
    apply_logo_watermark(temp_img_path)
    
    # Save as static MP4 clip using MoviePy
    try:
        static_clip = ImageClip(temp_img_path).set_duration(duration)
        static_clip.write_videofile(output_path, fps=24, codec="libx264", logger=None)
        static_clip.close()
    except Exception as e:
        print(f"⚠️ [explainer_slides] static slide render failed: {e}")
        
    if os.path.exists(temp_img_path):
        os.remove(temp_img_path)
    print(f"✅ NotebookLM MCQ slide video saved successfully: {output_path}")


def apply_logo_watermark(img_path: str):
    """Pastes the EaseToLearn transparent logo at the bottom-right corner of the slide."""
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.png")
    if not os.path.exists(logo_path):
        return
        
    try:
        slide_img = Image.open(img_path).convert("RGBA")
        logo_img = Image.open(logo_path).convert("RGBA")
        
        # Resize logo to standard watermark size (140px width, keeping aspect ratio)
        target_width = 140
        w_percent = (target_width / float(logo_img.size[0]))
        target_height = int((float(logo_img.size[1]) * float(w_percent)))
        logo_resized = logo_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        # Position logo: Bottom Right corner with 30px padding
        slide_w, slide_h = slide_img.size
        pos_x = slide_w - target_width - 30
        pos_y = slide_h - target_height - 30
        
        # Paste logo using its alpha channel as a mask for perfect transparency rendering
        slide_img.paste(logo_resized, (pos_x, pos_y), logo_resized)
        
        # Save back as RGB
        slide_img.convert("RGB").save(img_path)
        print(f"💧 Successfully applied watermark to: {os.path.basename(img_path)}")
    except Exception as e:
        print(f"⚠️ Failed to apply watermark to {img_path}: {e}")


# ── 7th Pipeline Master Entry Point ───────────────────────────────────────────

def generate_gemini_omni_slides_video(
    scenes: list,
    output_dir: str,
    topic: str,
    job_id: str = None,
    use_elevenlabs: bool = True
) -> tuple[str, dict]:
    """
    7th Pipeline — Gemini Omni 3D Slides Video Generator
    Creates highly accurate, premium 3D visual explanation videos (NotebookLM style)
    leveraging Gemini's Imagen 4.0/Veo Video API for diagrams and ElevenLabs for narration.
    """
    print(f"🎬 [7th Pipeline] Generating Gemini Omni 3D dynamic videos for: {topic}")
    
    clips = []
    audio_clips = []
    
    ledger = {
        "elevenlabs_chars": 0,
        "imagen_calls": 0,
        "veo_calls": 0
    }
    
    try:
        for i, scene in enumerate(scenes):
            v_type = scene["visual_type"]
            v_data = scene["visual_data"]
            narration = scene["narration_text"]
            
            # 1. Synthesize scene narration audio
            print(f"   🎙️ Generating narration for slide {i+1}...")
            audio_path, char_count = generate_audio(
                narration, f"slide_{i}", output_dir=output_dir, job_id=job_id, use_elevenlabs=use_elevenlabs
            )
            audio_clip = AudioFileClip(audio_path)
            audio_clips.append(audio_clip)
            dur = audio_clip.duration
            ledger["elevenlabs_chars"] += char_count
            
            # 2. Build Slide Visuals (Generative Video or pillow)
            print(f"   🎨 Generating Gemini Omni visual clip for slide {i+1} ({v_type})...")
            clip_filename = f"slide_{i}.mp4"
            clip_path = os.path.join(output_dir, clip_filename)
            
            if v_type in ["mcq_layout", "option_highlight", "cross_out", "answer_reveal"]:
                # Option analysis is drawn locally via Pillow for high legibility
                render_gemini_mcq_slide(v_type, v_data, clip_path, duration=dur)
            else:
                # Core 3D concept slide generated via Google Veo / Gemini Video API
                title = v_data.get("title") or v_data.get("heading") or topic
                subtitle = v_data.get("subtitle", "")
                bullets = v_data.get("bullets", [])
                objects = v_data.get("objects", [])
                
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
                    slide_content += f"\nShow 3D objects or visual assets representing: {', '.join(objects)}"
                
                if numeral:
                    slide_content += f"\nNote: The slide number '{numeral}' should be displayed as a giant, glossy, highly polished 3D numeral on the left side."
                elif v_type == "title_card":
                    slide_content += f"\nNote: Focus on a premium, clean 3D academic title cover layout in cinematic motion."
                else:
                    slide_content += f"\nNote: Focus on a beautiful, textbook-quality 3D clinical model or mechanical scientific structure in continuous slow-motion movement on the left side."
                
                clip_path = generate_gemini_omni_concept_video(
                    topic=slide_content,
                    subject="medical" if "medical" in topic.lower() else "default",
                    duration=dur,
                    output_dir=output_dir,
                    filename=clip_filename,
                    job_id=job_id
                )
                ledger["veo_calls"] += 1
            
            # 3. Create clip mapped to audio duration
            video_clip = VideoFileClip(clip_path).set_duration(dur).set_audio(audio_clip)
            clips.append(video_clip)
            
        # 4. Final Video Compilation
        print(f"   🎞️ Stitching {len(clips)} slide videos into final Gemini Omni MP4...")
        final_video = concatenate_videoclips(clips, method="compose")
        
        safe_topic = re.sub(r'[^a-zA-Z0-9_\-]', '_', topic.lower().strip())[:50]
        output_path = os.path.join(output_dir, f"{safe_topic}_gemini_omni_slides.mp4")
        
        final_video.write_videofile(
            output_path, fps=24, codec="libx264", audio_codec="aac", threads=4, logger=None
        )
        
        return output_path, ledger
        
    except Exception as e:
        print(f"   ❌ Gemini Omni Video Slides generation failed: {e}")
        raise e
    finally:
        for c in clips:
            try: c.close()
            except Exception: pass
        for a in audio_clips:
            try: a.close()
            except Exception: pass

