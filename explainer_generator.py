import os
import subprocess
import config
from PIL import Image
from moviepy.editor import (
    ColorClip, ImageClip, VideoFileClip, 
    concatenate_videoclips, AudioFileClip, CompositeVideoClip
)
from tts_generator import generate_audio
from higgsfield_generator import generate_higgsfield_video
from text_renderer import create_text_clip
import random

# Compatibility for Pillow 10.0+ 
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

def generate_explainer_video(scenes: list, image_paths: dict, output_dir: str, topic: str) -> str:
    """
    Multimodal Explainer Engine v5.0 (ImageMagick-Free)
    Stitches:
      - Higgsfield Generative AI Video (B-roll)
      - Imagen 3.0 Counting Metaphors (1-to-N logic)
      - Cinematic static image zooms
      - ElevenLabs narration
    """
    print(f"🎬 [Explainer Gen] Building Multimodal Metaphor Factory for: {topic}")
    
    clips = []
    audio_clips = []
    video_clips_to_close = []
    try:
        for i, scene in enumerate(scenes):
            v_type = scene["visual_type"]
            v_data = scene["visual_data"]
            narration = scene["narration_text"]
            
            # 1. Generate narration audio for timing
            audio_path = generate_audio(narration, f"explainer_{i}", output_dir=output_dir)
            audio_clip = AudioFileClip(audio_path)
            audio_clips.append(audio_clip)
            dur = audio_clip.duration
            
            # 2. Build visual asset for this scene
            scene_clip = None
            
            if v_type == "counting_metaphor":
                item_name = v_data.get("item_name", "item")
                count = v_data.get("count", 1)
                asset_id = f"counting_{i}_{item_name}"
                item_path = image_paths.get(asset_id)
                
                bg_id = f"counting_bg_{i}"
                bg_path = image_paths.get(bg_id)
                
                if item_path and os.path.exists(item_path):
                    scene_clip, sub_to_close = _create_counting_clip(item_path, count, dur, bg_path=bg_path)
                    video_clips_to_close.extend(sub_to_close)
                else:
                    scene_clip = _create_fallback_clip(f"Count: {count} {item_name}", dur)
            
            elif v_type == "generative_video":
                prompt = v_data.get("prompt", "Cinematic motion")
                video_path = os.path.join(output_dir, f"gen_video_{i}.mp4")
                try:
                    video_path = generate_higgsfield_video(prompt, video_path)
                    raw_orig = VideoFileClip(video_path)
                    raw_v = raw_orig.without_audio()
                    video_clips_to_close.extend([raw_orig, raw_v])
                    # Loop or stretch if video is shorter than narration (generative is usually 2s)
                    if raw_v.duration < dur:
                        scene_clip = raw_v.loop(duration=dur)
                    else:
                        scene_clip = raw_v.set_duration(dur)
                except Exception as e:
                    print(f"   ⚠️ Higgsfield failed: {e}")
                    scene_clip = _create_fallback_clip(prompt, dur)

            elif v_type == "b_roll_clip" or v_type == "concept_image":
                asset_id = f"metaphor_{i}"
                img_path = image_paths.get(asset_id)
                if img_path and os.path.exists(img_path):
                    scene_clip, sub_to_close = _create_zoom_clip(img_path, dur)
                    video_clips_to_close.extend(sub_to_close)
                else:
                    scene_clip = _create_fallback_clip("Educational visual", dur)
            
            else:
                scene_clip = _create_fallback_clip(f"Scene {i+1}", dur)

            # 3. Add scene-specific text overlay (optional)
            if v_type == "counting_metaphor":
                # Use PIL-based renderer instead of TextClip
                txt = create_text_clip(
                    str(v_data.get("count", "")), 
                    fontsize=120, 
                    color='white', 
                    stroke_width=2, 
                    stroke_color='black',
                    duration=dur
                ).set_position(('center', 0.8), relative=True)
                scene_clip = CompositeVideoClip([scene_clip, txt])

            scene_clip = scene_clip.set_audio(audio_clip)
            clips.append(scene_clip)

        # 4. Final Stitching with cross-fades
        final_video = concatenate_videoclips(clips, method="compose")
        output_path = os.path.join(output_dir, f"{topic.lower().replace(' ', '_')}_explainer.mp4")
        final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", threads=4)
        
        final_video.close()
            
    except Exception as e:
        print(f"   ❌ Explainer Gen Error: {e}")
        raise e
    finally:
        # Robust cleanup
        for c in clips:
            if c:
                try: c.close()
                except: pass
        for a in audio_clips:
            if a:
                try: a.close()
                except: pass
        for v in video_clips_to_close:
            if v:
                try: v.close()
                except: pass
    
    return output_path

def _create_zoom_clip(img_path, duration):
    """Applies a smooth randomized Ken Burns scale/pan effect."""
    # Choose a random "start" and "end" anchor to make it feel cinematic
    anchors = [
        ('center', 'center'), 
        ('left', 'top'), ('right', 'bottom'), 
        ('left', 'bottom'), ('right', 'top')
    ]
    start_pos, end_pos = random.sample(anchors, 2)
    
    clip = ImageClip(img_path).set_duration(duration).resize(width=1400) # Slightly larger for padding
    
    # Zoom from 1.0 to 1.1 over duration
    def zoom_fn(t):
        return 1.0 + 0.1 * (t / duration)
    
    final_clip = clip.resize(zoom_fn).set_position('center')
    return final_clip, [clip, final_clip]

def _create_counting_clip(item_path, count, duration, bg_path=None):
    """Composites items with a staggered kinetic pop-in effect over a cinematic background."""
    if bg_path and os.path.exists(bg_path):
        # Use existing zoom_clip logic for the background if it's an image
        if bg_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            bg = _create_zoom_clip(bg_path, duration)
        else:
            # Fallback for video backgrounds (if supported later)
            bg = VideoFileClip(bg_path).set_duration(duration).resize(height=720)
    else:
        bg = ColorClip(size=(1280, 720), color=(15, 15, 30), duration=duration)
    
    # Item template
    base_item = ImageClip(item_path).resize(height=180)
    to_close = [base_item]
    if isinstance(bg, (ImageClip, VideoFileClip)):
        to_close.append(bg)
    
    positions = [
        (0.5, 0.4), (0.4, 0.5), (0.6, 0.5), 
        (0.3, 0.3), (0.7, 0.3), (0.5, 0.65),
        (0.2, 0.6), (0.8, 0.6), (0.4, 0.2), (0.6, 0.2)
    ]
    
    layers = [bg]
    stagger_delay = 0.4 # Seconds between pops
    
    for i in range(min(count, 10)):
        start_t = i * stagger_delay
        if start_t >= duration: break
        
        pos = positions[i]
        
        # Create a "pop" animation: scale from 0 to 1 quickly
        pop_duration = 0.3
        def make_pop(t):
            if t < start_t: return 0.01 # Invisible
            progress = min((t - start_t) / pop_duration, 1.0)
            # Subtle overshoot for "snap" feel
            if progress < 0.8:
                return max(progress * 1.4, 0.01) # Increased snap, forced positive
            else:
                return 1.4 - (progress - 0.8) * 2.0 # Settles to 1.0
                
        animated_item = base_item.resize(make_pop).set_start(start_t).set_duration(duration - start_t).set_position(pos, relative=True)
        layers.append(animated_item)
        to_close.append(animated_item)
        
    final_comp = CompositeVideoClip(layers).set_duration(duration)
    to_close.append(final_comp)
    return final_comp, to_close

def _create_fallback_clip(text, duration):
    bg = ColorClip(size=(1280, 720), color=(20, 20, 40), duration=duration)
    # Use PIL-based renderer instead of TextClip
    txt = create_text_clip(
        text, 
        fontsize=40, 
        color='white',
        duration=duration
    ).set_position('center')
    return CompositeVideoClip([bg, txt])
