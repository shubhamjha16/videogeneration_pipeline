import os
import re
import config
from moviepy.editor import (
    ImageClip, VideoFileClip, concatenate_videoclips, AudioFileClip, CompositeVideoClip
)
from tts_generator import generate_audio
from image_generator import generate_concept_image
from gemini_omni_slides_generator import (
    generate_gemini_omni_concept_video, format_math_for_pillow, 
    render_gemini_mcq_slide
)
from explainer_slides_generator import apply_logo_watermark
from manim_generator import generate_manim_video
from PIL import Image, ImageDraw, ImageFont

# Compatibility for Pillow 10.0+ 
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

def select_optimal_visual_type(
    title: str,
    subtitle: str,
    bullets: list,
    narration: str,
    subject: str
) -> str:
    """
    Invokes LLMFactory to dynamically choose the most natural and attentive visual style
    for the left slide panel based on cognitive psychology principles (Cognitive Load & Dual Coding).
    """
    try:
        from llm_factory import LLMFactory, clean_llm_json
        
        prompt = f"""
You are an expert in educational video design, human attention optimization, and cognitive psychology (specifically Dual Coding Theory and Cognitive Load Theory).
Your job is to decide the OPTIMAL visual style for the illustration panel on the left of an educational presentation slide, based on the slide's title, bullets, narration, and subject area.

Available Visual Options:
1. "manim": Step-by-step mathematical/algebraic equation derivations, physics coordinate vectors, mechanical forces, or geometric coordinate graphs in motion. Best for progressive logical reasoning to reduce cognitive load.
2. "omni": High-fidelity 3D educational clinical/anatomical animation, cellular mechanisms, physical spatial particle simulations, or premium 3D graphics in motion. Best for complex spatial processes.
3. "dalle": High-quality static educational diagrams, concept comparison maps, timelines, or semantic text hierarchies where static viewing is preferred over motion to prevent split-attention distraction.
4. "panning_whiteboard": Simple, clean, subtle educational whiteboard panning background. Best for introductory title slides, overview lists, or simple MCQ cards where complex moving visuals would cause attention splitting.

Slide Information:
- Subject: {subject}
- Title: {title}
- Subtitle: {subtitle}
- Bullet Points: {bullets}
- Narration: {narration}

Choose the single best option ("manim", "omni", "dalle", or "panning_whiteboard") that maximizes academic attention and cognitive retention. 
Return your decision strictly in JSON format as follows:
{{
  "optimal_visual": "option",
  "reasoning": "brief explanation based on cognitive psychology"
}}
"""
        messages = [{"role": "user", "content": prompt}]
        response_str = LLMFactory.get_completion(messages, json_mode=True, temperature=0.0)
        data = clean_llm_json(response_str)
        choice = data.get("optimal_visual", "dalle").strip().lower()
        reasoning = data.get("reasoning", "")
        print(f"🧠 [Cognitive Selector] Chosen visual: '{choice}' (Reason: {reasoning})")
        if choice in ["manim", "omni", "dalle", "panning_whiteboard"]:
            return choice
    except Exception as e:
        print(f"⚠️ [Cognitive Selector] LLM Selection failed: {e}. Using fallback heuristics...")
        
    # Heuristic fallback if LLM is offline/rate-limited
    if "derivation" in title.lower() or "equation" in title.lower() or subject in ["maths", "physics"]:
        return "manim"
    elif subject in ["medical", "chemistry"]:
        return "omni"
    return "dalle"


def render_hybrid_slide_template(
    title: str,
    subtitle: str,
    bullets: list,
    output_path: str,
    tony_pose_path: str = None
):
    """
    Renders a widescreen premium slide background and text card on the right,
    leaving the left side perfectly laid out for the dynamic clipped Gemini Omni / Manim video.
    """
    w, h = 1280, 720
    
    # 1. Background (Off-white grid background)
    img = Image.new("RGB", (w, h), "#F4F7F7")
    draw = ImageDraw.Draw(img)
    
    # Draw premium grid lines
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
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            ]
        for p in paths:
            if os.path.exists(p):
                try: return ImageFont.truetype(p, size)
                except Exception: continue
        return ImageFont.load_default()

        
    font_title = get_font(32, bold=True)
    font_sub = get_font(20, bold=False)
    font_bullet = get_font(18, bold=False)
    
    # 2. Draw Left Illustration Card Frame (to house the clipped Gemini Omni / Manim video)
    left_frame = [40, 40, 620, 680]
    draw.rounded_rectangle(left_frame, radius=12, fill="#EBF5F5", outline="#088A8F", width=2)
    
    # 3. Draw Right Content Card (rounded white card with text)
    right_card = [640, 40, 1240, 680]
    draw.rounded_rectangle(right_card, radius=12, fill="#FFFFFF", outline="#E2E8F0", width=2)
    
    # Word wrap text helper
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
 
    from gemini_omni_slides_generator import draw_rich_math_text
 
    # Draw Title
    title_text = format_math_for_pillow(title)
    title_lines = wrap_text(title_text, font_title, 540)
    curr_y = 70
    for line in title_lines[:2]:
        draw_rich_math_text(draw, (680, curr_y), line, font_title, "#088A8F")
        curr_y += 38
        
    # Draw Subtitle
    if subtitle:
        sub_text = format_math_for_pillow(subtitle)
        sub_lines = wrap_text(sub_text, font_sub, 540)
        curr_y += 5
        for line in sub_lines[:2]:
            draw_rich_math_text(draw, (680, curr_y), line, font_sub, "#4A5568")
            curr_y += 26
            
    curr_y += 20
    
    # Draw Bullet Points
    for bullet in bullets:
        if not bullet:
            continue
        bullet_text = format_math_for_pillow(bullet)
        bullet_lines = wrap_text(bullet_text, font_bullet, 500)
        
        # Draw a beautiful solid bullet point marker
        draw.ellipse([680, curr_y + 6, 690, curr_y + 16], fill="#088A8F", outline="#088A8F")
        
        for line in bullet_lines:
            draw_rich_math_text(draw, (710, curr_y), line, font_bullet, "#1E293B")
            curr_y += 26
        curr_y += 12
        
    # ─── TONY CARTOON AVATAR OVERLAY ─────────────────────────
    if tony_pose_path and os.path.exists(tony_pose_path):
        try:
            print(f"   [tony-hybrid] compositing {os.path.basename(tony_pose_path)} onto text card")
            with Image.open(tony_pose_path) as pose:
                pose = pose.convert("RGBA")
                # Tony should sit in the bottom right corner of the right content card
                # Right content card is [640, 40, 1240, 680].
                # We want Tony to be about 220px wide and 260px high.
                target_w, target_h = 220, 260
                pose.thumbnail((target_w, target_h), Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.ANTIALIAS)
                
                # Overlay on top of template
                overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
                
                actual_w, actual_h = pose.size
                # Place at the bottom right corner of the right card (x ≈ 1240 - actual_w - 20, y ≈ 680 - actual_h)
                x = 1240 - actual_w - 20
                y = 680 - actual_h
                
                overlay.paste(pose, (x, y))
                
                img_rgba = img.convert("RGBA")
                img = Image.alpha_composite(img_rgba, overlay).convert("RGB")
        except Exception as e:
            print(f"⚠️ [tony-hybrid] failed to composite Tony: {e}")

    img.save(output_path)
    pose_name = os.path.basename(tony_pose_path) if tony_pose_path else None
    apply_logo_watermark(output_path, pose_name=pose_name)
    print(f"✅ Premium Slide Card rendered locally: {output_path}")


def generate_explainer_gemini_hybrid_slides_video(
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
    Explainer Gemini Hybrid Slides Engine
    Combines:
      - Pristine Pillow-drawn slides with sharp academic content on the right.
      - Cognitive Psychology LLM Selector to decide the absolute best visual for each slide.
      - Dynamic Gemini Omni 3D animations OR Manim mathematical derivations/animations
        clipped inside the frame on the left.
      - Seamless fallback to ChatGPT DALL-E static diagram zooms inside the same frame.
      - High-quality ElevenLabs voiceover syncing.
    """
    print(f"🎬 [Hybrid Pipeline] Generating Explainer Gemini Hybrid Slides for: {topic} (Subject: {subject})")
    
    clips = []
    audio_clips = []
    
    ledger = {
        "elevenlabs_chars": 0,
        "dalle_calls": 0,
        "veo_calls": 0,
        "manim_calls": 0
    }
    
    try:
        for i, scene in enumerate(scenes):
            v_type = scene["visual_type"]
            v_data = scene["visual_data"]
            narration = scene["narration_text"]
            
            # 1. Synthesize narration audio
            print(f"   🎙️ Generating narration for slide {i+1}...")
            audio_path, char_count = generate_audio(
                narration, f"slide_{i}", output_dir=output_dir, job_id=job_id, use_elevenlabs=use_elevenlabs
            )
            audio_clip = AudioFileClip(audio_path)
            audio_clips.append(audio_clip)
            dur = audio_clip.duration
            ledger["elevenlabs_chars"] += char_count
            
            # 2. Build Slide Layout
            print(f"   🎨 Rendering slide card {i+1}...")
            slide_img_path = os.path.join(output_dir, f"slide_{i}_template.png")
            
            # If MCQ, let's render using the widescreen MCQ template directly!
            if v_type in ["mcq_layout", "option_highlight", "cross_out", "answer_reveal"]:
                render_gemini_mcq_slide(v_type, v_data, slide_img_path.replace(".png", ".mp4"), duration=dur)
                video_clip = VideoFileClip(slide_img_path.replace(".png", ".mp4")).set_duration(dur).set_audio(audio_clip)
                clips.append(video_clip)
                continue
            
            # Standard concept slides
            title = v_data.get("title") or v_data.get("heading") or topic
            subtitle = v_data.get("subtitle", "")
            bullets = v_data.get("bullets", [])
            objects = v_data.get("objects", [])
            
            # Determine Tony pose path
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

            # Render standard template with Pillow
            render_hybrid_slide_template(title, subtitle, bullets, slide_img_path, tony_pose_path=tony_pose_path)
            
            # Create base image clip from template
            base_clip = ImageClip(slide_img_path).set_duration(dur)
            
            # Inner frame dimensions on left side: x: 50 to 610, y: 50 to 670 (width: 560, height: 620)
            target_w = 560
            target_h = 620
            
            concept_clip = None
            omni_failed = False
            
            # Dynamic choice based on cognitive psychology principles
            chosen_visual_type = select_optimal_visual_type(
                title=title,
                subtitle=subtitle,
                bullets=bullets,
                narration=narration,
                subject=subject
            )
            
            # --- Visual Option 1: Manim Animation ---
            if chosen_visual_type == "manim":
                try:
                    print(f"   📐 Cognitive Decision: [Manim]. Rendering step-by-step mathematical derivation...")
                    manim_prompt = f"Topic: {title}. Visual elements to animate: {', '.join(bullets)}."
                    manim_video_path = generate_manim_video(manim_prompt, i, output_dir=output_dir)
                    
                    if manim_video_path and os.path.exists(manim_video_path):
                        ledger["manim_calls"] += 1
                        raw_manim = VideoFileClip(manim_video_path).without_audio()
                        
                        # Loop or adjust to narration duration
                        if raw_manim.duration < dur:
                            raw_manim = raw_manim.loop(duration=dur)
                        else:
                            raw_manim = raw_manim.set_duration(dur)
                            
                        # Crop and resize to exactly fill target_w x target_h
                        x1 = (raw_manim.w * target_h / raw_manim.h - target_w) / 2
                        concept_clip = raw_manim.resize(height=target_h).crop(x1=x1, x2=x1+target_w)
                        print(f"   ✅ Manim derivation overlay constructed successfully!")
                except Exception as ex:
                    print(f"   ⚠️ Manim rendering failed ({ex}) - falling back to Gemini Omni Video...")
            
            # --- Visual Option 2: Gemini Omni 3D Video ---
            if not concept_clip and chosen_visual_type in ["omni", "manim"]:
                try:
                    print(f"   🎬 Cognitive Decision: [Omni]. Requesting 3D spatial concept simulation...")
                    slide_content = f"Title: {title}\nShow 3D objects or visual assets representing: {', '.join(objects) if objects else topic}"
                    omni_video_path = os.path.join(output_dir, f"slide_{i}_omni.mp4")
                    
                    generate_gemini_omni_concept_video(
                        topic=slide_content,
                        subject=subject,
                        duration=dur,
                        output_dir=output_dir,
                        filename=f"slide_{i}_omni.mp4",
                        job_id=job_id
                    )
                    ledger["veo_calls"] += 1
                    
                    raw_omni = VideoFileClip(omni_video_path).without_audio().set_duration(dur)
                    # Crop and resize to exactly fill target_w x target_h
                    concept_clip = raw_omni.resize(height=target_h).crop(x1=(raw_omni.w * target_h / raw_omni.h - target_w)/2, x2=(raw_omni.w * target_h / raw_omni.h + target_w)/2)
                    
                except Exception as e:
                    print(f"   ⚠️ Gemini Omni failed or offline ({e}) - switching to ChatGPT DALL-E static diagram Zoom...")
                    omni_failed = True
                
            # --- Visual Option 3: ChatGPT DALL-E Static Diagram Zoom ---
            if not concept_clip or chosen_visual_type == "dalle" or omni_failed:
                try:
                    print(f"   🎨 Cognitive Decision: [DALL-E]. Requesting high-density conceptual diagram zoom...")
                    dalle_content = f"Whiteboard doodle detailing {topic}."
                    if objects:
                        dalle_content += f" Specifically showing: {', '.join(objects)}"
                    img_filename = f"slide_{i}_dalle.png"
                    
                    dalle_img_path = generate_concept_image(
                        topic=dalle_content,
                        subject=f"whiteboard_doodle_{subject}",
                        output_dir=output_dir,
                        filename=img_filename,
                        job_id=job_id
                    )
                    ledger["dalle_calls"] += 1
                    
                    # Create a premium zoom effect of the static DALL-E image
                    from explainer_generator import _create_zoom_clip
                    zoom_clip, zoom_to_close = _create_zoom_clip(dalle_img_path, dur)
                    # Resize/crop to fit left side card
                    concept_clip = zoom_clip.resize(height=target_h).crop(width=target_w, height=target_h)
                except Exception as ex:
                    print(f"   ⚠️ DALL-E fallback failed too ({ex}) - using local grid placeholder...")
            
            # --- Visual Option 4: Panning Whiteboard (Simple overview slides / Fallback) ---
            if not concept_clip:
                # Ultimate fallback / simple card panning visual
                placeholder_path = os.path.join(output_dir, f"slide_{i}_placeholder.png")
                placeholder_img = Image.new("RGB", (target_w, target_h), "#EBF5F5")
                placeholder_img.save(placeholder_path)
                concept_clip = ImageClip(placeholder_path).set_duration(dur)
            
            # Position concept_clip on left frame: starts at x=50, y=50
            positioned_concept = concept_clip.set_position((50, 50))
            
            # Staged composite: base slide card with the positioned dynamic visual
            composite_slide = CompositeVideoClip([base_clip, positioned_concept]).set_duration(dur).set_audio(audio_clip)
            clips.append(composite_slide)
            
        # 4. Final Video Compilation
        print(f"   🎞️ Stitching {len(clips)} slides into final Explainer Gemini Hybrid Slides Video...")
        final_video = concatenate_videoclips(clips, method="compose")
        
        safe_topic = re.sub(r'[^a-zA-Z0-9_\-]', '_', topic.lower().strip())[:50]
        output_path = os.path.join(output_dir, f"{safe_topic}_explainer_gemini_hybrid_slides.mp4")
        
        final_video.write_videofile(
            output_path, fps=24, codec="libx264", audio_codec="aac", threads=4, logger=None
        )
        
        return output_path, ledger
        
    except Exception as e:
        print(f"   ❌ Hybrid Slide production failed: {e}")
        raise e
    finally:
        for c in clips:
            try: c.close()
            except Exception: pass
        for a in audio_clips:
            try: a.close()
            except Exception: pass
