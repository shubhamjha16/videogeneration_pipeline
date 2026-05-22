import os
import re
import config
from moviepy.editor import (
    ImageClip, concatenate_videoclips, AudioFileClip
)
from tts_generator import generate_audio
from image_generator import generate_concept_image
from PIL import Image, ImageDraw, ImageFont

def render_explainer_mcq_slide(
    visual_type: str,
    visual_data: dict,
    output_path: str
):
    """
    Renders high-contrast, premium, 100% correct MCQ Option Analysis slides
    locally using Pillow. This ensures absolute readability, mathematical accuracy,
    and a wowed academic/clinical interface matching the provided templates.
    """
    w, h = 1024, 1024
    
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
    
    # Load fonts
    def get_font(size, bold=False):
        paths = []
        if bold:
            paths = [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/Library/Fonts/Arial Bold.ttf",
                "/System/Library/Fonts/HelveticaNeue.dfont",
            ]
        else:
            paths = [
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/Library/Fonts/Arial.ttf",
                "/System/Library/Fonts/Helvetica.dfont",
            ]
        for p in paths:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except:
                    pass
        return ImageFont.load_default()
        
    font_q = get_font(28, bold=True)
    font_opt = get_font(20, bold=False)
    font_opt_letter = get_font(24, bold=True)
    font_exp = get_font(18, bold=False)
    
    # 2. Get Question
    question = visual_data.get("question") or "Review the options below:"
    
    # Word wrap question
    def wrap_text(text, font, max_width):
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            test_line = " ".join(current_line + [word])
            try:
                tw = draw.textlength(test_line, font=font)
            except:
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
    
    # Draw question card
    draw.rounded_rectangle([40, 40, w - 40, 200], radius=15, fill="#EBF5F5", outline="#0D7A7F", width=2)
    q_y = 65
    for line in q_lines[:3]: # limit to 3 lines
        draw.text((60, q_y), line, fill="#0D7A7F", font=font_q)
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
        opt_text = options.get(letter, f"Option {letter}")
        
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
        card_box = [40, opt_y, w - 40, opt_y + 120]
        draw.rounded_rectangle(card_box, radius=12, fill=card_fill, outline=card_outline, width=card_border_w)
        
        # Draw Letter Circle
        circle_box = [60, opt_y + 35, 110, opt_y + 85]
        draw.ellipse(circle_box, fill="#CBD5E1" if letter_fill == "#94A3B8" else "#EBF5F5", outline=card_outline)
        draw.text((77, opt_y + 45), letter, fill=letter_fill, font=font_opt_letter)
        
        # Draw Option Text
        opt_lines = wrap_text(opt_text, font_opt, w - 240)
        line_y = opt_y + 40 if len(opt_lines) == 1 else opt_y + 25
        for line in opt_lines[:2]:
            draw.text((140, line_y), line, fill=text_fill, font=font_opt)
            line_y += 30
            
        # Draw dynamic status icons
        if draw_x_mark:
            draw.line([(w - 100, opt_y + 40), (w - 60, opt_y + 80)], fill="#EF4444", width=4)
            draw.line([(w - 60, opt_y + 40), (w - 100, opt_y + 80)], fill="#EF4444", width=4)
        elif draw_check_mark:
            draw.line([(w - 95, opt_y + 60), (w - 80, opt_y + 75)], fill="#22C55E", width=5)
            draw.line([(w - 80, opt_y + 75), (w - 60, opt_y + 45)], fill="#22C55E", width=5)
            
        opt_y += 140
        
    # 4. Draw explanation if reveal
    if is_reveal:
        explanation = visual_data.get("explanation") or ""
        if explanation:
            exp_lines = wrap_text(explanation, font_exp, w - 80)
            exp_y = 810
            draw.rounded_rectangle([40, 790, w - 40, h - 40], radius=10, fill="#ECFDF5", outline="#34D399", width=2)
            
            if is_none_of_above:
                font_exp_bold = get_font(20, bold=True)
                draw.text((60, exp_y), "Correct Answer: None of the above", fill="#047857", font=font_exp_bold)
                exp_y += 30
                
            for line in exp_lines[:4]:
                draw.text((60, exp_y), line, fill="#065F46", font=font_exp)
                exp_y += 25
                
    img.save(output_path)
    print(f"✅ Handcrafted MCQ slide ({visual_type}) rendered successfully to {output_path}")


def generate_explainer_slides_video(scenes: list, output_dir: str, topic: str, job_id: str = None, use_elevenlabs: bool = True) -> tuple[str, dict]:
    """
    Explainer Slides Engine v2.0
    Generates a premium, numbered whiteboard sequence synced to ElevenLabs narration.
    """
    print(f"🎬 [Explainer Slides] Building premium whiteboard sequences for: {topic}")
    
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
                render_explainer_mcq_slide(v_type, v_data, img_path)
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
                    subject="whiteboard_doodle",
                    output_dir=output_dir,
                    filename=img_filename,
                    job_id=job_id
                )
                ledger["dalle_calls"] += 1
            
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
            except: pass
        for a in audio_clips:
            try: a.close()
            except: pass
