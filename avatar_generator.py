import os
import math
import numpy as np
import config
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoClip, AudioFileClip, VideoFileClip

# Fix for MoviePy/Pillow 10+ compatibility
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

def generate_avatar_video(text: str, audio_file: str, scene_idx: int, output_dir: str = ".", avatar_type: str = config.DEFAULT_AVATAR) -> str:
    """
    Generates a dynamic animated Avatar video clip.
    avatar_type: 
      - "logo": Branded infinity logo with blinking eyes (Local render)
      - "human": Static photo with logic-based mouth overlay (Local, fast)
      - "pro": Real AI Lip-Sync using ElevenLabs API (Requires tutor_face.png)
      - "user": Your real face from camera! (Requires media/user_face.mp4)
    """
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    avatar_video_path = os.path.join(output_dir, f"scene_{scene_idx}_avatar.mp4")
    width, height = 320, 240

    # --- PRO / USER MODES: ElevenLabs Lip-Sync API ---
    # Ensure ElevenLabs key is loaded from config if not in env
    api_key = config.ELEVENLABS_API_KEY
    if api_key and avatar_type in ["pro", "user"]:
        from eleven_lip_sync import generate_lip_sync
        
        # Determine base video
        if avatar_type == "user":
            base_video = "user_face.mp4"
            if not os.path.exists(base_video):
                base_video = "media/user_face.mp4"
        else:
            base_video = os.path.join(os.path.dirname(output_dir), "base_avatar.mp4")
            if not os.path.exists(base_video):
                base_video = "media/base_avatar.mp4"

        if os.path.exists(base_video):
            if config.ELEVENLABS_API_KEY:
                print(f"🚀 Calling ElevenLabs Lip-Sync API for scene {scene_idx}...")
                try:
                    audio_clip = AudioFileClip(audio_file)
                    dur = audio_clip.duration
                    audio_clip.close()
                    
                    result = generate_lip_sync(base_video, audio_file, avatar_video_path)
                    if result:
                        return result, dur
                    else:
                        if avatar_type == "user":
                            print(f"⚠️ ElevenLabs API Error. Generating local Simulated Lip-Sync...")
                            return create_talking_video_local(base_video, audio_file, avatar_video_path)
                        avatar_type = "human"
                except Exception as e:
                    print(f"❌ Lip-Sync System Error: {e}")
                    if avatar_type == "user":
                        return create_talking_video_local(base_video, audio_file, avatar_video_path)
                    avatar_type = "human"
                if avatar_type == "user":
                    print(f"⚠️ ELEVENLABS_API_KEY not found. Generating local Simulated Lip-Sync...")
                    return create_talking_video_local(base_video, audio_file, avatar_video_path)
                avatar_type = "human"
        else:
            if avatar_type == "user":
                print(f"⚠️ User video not found: {base_video}. Falling back to logo.")
                avatar_type = "logo"
            else:
                avatar_type = "human"

    # --- LOCAL RENDERING MODES ---
    face_img = None
    if avatar_type == "human" or avatar_type == "pro":
        face_path = "tutor_face.png"
        if os.path.exists(face_path):
            face_img = Image.open(face_path).convert("RGB")
            # Headshot crop: Image is already a headshot, so we just zoom in slightly
            w, h = face_img.size
            crop_w = int(w * 0.85) # High quality zoom
            crop_h = int(crop_w * (240/320))
            left = (w - crop_w) // 2
            top = int(h * 0.02) # Keep top of head
            face_img = face_img.crop((left, top, left + crop_w, top + crop_h))
            face_img = face_img.resize((320, 240))

    def make_frame(t):
        if (avatar_type == "human" or avatar_type == "pro") and face_img:
            img = face_img.copy()
        else:
            img = Image.new('RGB', (width, height), color=(30, 30, 30))
            
        d = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        if avatar_type == "logo" or not face_img:
            # Logo Drawing Logic
            spacing, radius, thickness = width // 5, width // 6, width // 20
            lc = (cx - spacing // 2, cy)
            rc = (cx + spacing // 2, cy)
            d.arc([(lc[0]-radius, lc[1]-radius), (lc[0]+radius, lc[1]+radius)], 45, 315, fill=(0, 110, 255), width=thickness)
            d.arc([(rc[0]-radius, rc[1]-radius), (rc[0]+radius, rc[1]+radius)], 225, 135, fill=(0, 110, 255), width=thickness)
            d.line([(lc[0], lc[1]-radius), (rc[0], rc[1]+radius)], fill=(0, 110, 255), width=thickness)
            d.line([(lc[0], lc[1]+radius), (rc[0], rc[1]-radius)], fill=(0, 110, 255), width=thickness)
        
        # Eyes & Blinking
        eye_y = int(height * 0.35) if face_img else cy - (width // 12)
        eye_offset = width // 10
        is_blinking = (t % 3.0) < 0.2
        
        if not face_img: # Only draw eyes for logo
            if is_blinking:
                d.line([(cx - eye_offset - 10, eye_y), (cx - eye_offset + 10, eye_y)], fill=(255, 255, 255), width=2)
                d.line([(cx + eye_offset - 10, eye_y), (cx + eye_offset + 10, eye_y)], fill=(255, 255, 255), width=2)
            else:
                d.ellipse([(cx - eye_offset - 10, eye_y-8), (cx - eye_offset + 10, eye_y+8)], fill=(255, 255, 255))
                d.ellipse([(cx + eye_offset - 10, eye_y-8), (cx + eye_offset + 10, eye_y+8)], fill=(255, 255, 255))
        
        # Mouth Animation
        mouth_open = abs(math.sin(t * 12) + math.sin(t * 8)) / 2 
        if face_img:
            # Position mouth based on HEADSHOT crop (usually 65% down)
            mouth_y = int(height * 0.65)
            mw, mh = 42, 6 + (16 * mouth_open)
            d.ellipse([(cx-mw//2, mouth_y-mh//2), (cx+mw//2, mouth_y+mh//2)], fill=(0, 0, 0, 160))
        else:
            mh, my = 5 + (20 * mouth_open), cy + (width // 18)
            d.ellipse([(cx-(width//10), my-mh//2), (cx+(width//10), my+mh//2)], fill=(255, 255, 255))
                  
        return np.array(img)
    
    # Render logic: render a fixed 30s of animation (high-fidelity logo idling)
    # This ensures we never need to loop short segments, avoiding MoviePy seeking bugs.
    audio = AudioFileClip(audio_file)
    dur = audio.duration
    animated_clip = VideoClip(make_frame, duration=dur)
    final = animated_clip.set_audio(audio)
    try:
        final.write_videofile(avatar_video_path, fps=24, codec="libx264")
    finally:
        audio.close()
        animated_clip.close()
        final.close()
    return avatar_video_path, dur

def create_talking_video_local(video_input, audio_input, output_path):
    """
    Creates a simulated lip-sync by overlaying a moving mouth on a video.
    """
    from moviepy.editor import VideoFileClip, AudioFileClip
    from moviepy.video.fx.all import loop as fx_loop
    import numpy as np

    print(f"🎬 Creating local Simulated Lip-Sync: {output_path}")
    aud = AudioFileClip(audio_input)
    dur = aud.duration
    
    # Load and loop base video
    base = VideoFileClip(video_input).without_audio()
    base = fx_loop(base, duration=dur)
    
    def add_mouth_filter(get_frame, t):
        frame = get_frame(t)
        img = Image.fromarray(frame)
        d = ImageDraw.Draw(img)
        w, h = img.size
        
        # Audio-reactive animation
        # Simple oscillation for now, can be improved with soundarray
        mouth_open = abs(math.sin(t * 12) + math.sin(t * 8)) / 2 
        
        cx, cy = w // 2, int(h * 0.72)
        rw, rh = int(w * 0.08), int(h * 0.05 * mouth_open)
        
        if rh > 2:
            # Draw a dark mouth ellipse
            d.ellipse([cx-rw, cy-rh, cx+rw, cy+rh], fill=(20, 0, 0))
            
        return np.array(img)

    talking = base.fl(add_mouth_filter)
    talking = talking.set_audio(aud)
    
    # Use low bitrate for speed
    try:
        talking.write_videofile(output_path, fps=12, codec="libx264", audio_codec="aac", bitrate="500k")
    finally:
        aud.close()
        base.close()
        talking.close()
    return output_path, dur

if __name__ == "__main__":
    pass
