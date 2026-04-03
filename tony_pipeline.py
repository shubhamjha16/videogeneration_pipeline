import os
import sys
import re
from PIL import Image
# Fix for MoviePy/Pillow 10+ compatibility
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS
from tts_generator import generate_audio
from slide_generator import generate_slide_image
from avatar_generator import generate_avatar_video

import config

def split_into_scenes(text):
    # Split by periods followed by space and capital letter (preserves initials)
    sentences = re.split(r'\.\s+(?=[A-Z])', text.strip())
    # Clean up and limit to 5-7 scenes for best pacing
    return [s.strip() + "." if not s.endswith(".") else s.strip() for s in sentences if len(s.strip()) > 10][:7]

def run_tony_pipeline(raw_text, topic_name="tony_ai_output", avatar_type=config.DEFAULT_AVATAR, output_dir=None, bg_image=None):
    if output_dir:
        job_dir = output_dir
    else:
        job_id = f"job_{topic_name.replace(' ', '_').lower()}"
        job_dir = os.path.join("output", job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    script = split_into_scenes(raw_text)
    print(f"📄 Processing {len(script)} scenes for {topic_name}...")

    # Pre-render shared avatars only if needed (for performance)
    logo_av, human_av = None, None
    part_suffix = output_dir.split("part_")[-1] if output_dir and "part_" in output_dir else "0"
    if avatar_type == "logo":
        print(f"\n🎭 Pre-rendering shared Logo avatar for part {part_suffix}...")
        _ref_audio = generate_audio("Reference Avatar Audio", f"ref_{part_suffix}", output_dir=job_dir)
        logo_av = generate_avatar_video("", _ref_audio, f"pre_{part_suffix}_logo", output_dir=job_dir, avatar_type="logo")
    elif avatar_type == "human":
        print(f"\n🎭 Pre-rendering shared Human avatar for part {part_suffix}...")
        _ref_audio = generate_audio("Reference Avatar Audio", f"ref_{part_suffix}", output_dir=job_dir)
        human_av = generate_avatar_video("", _ref_audio, f"pre_{part_suffix}_human", output_dir=job_dir, avatar_type="human")

    scenes = []
    for i, line in enumerate(script):
        print(f"🎬 Generating Scene {i+1}...")
        scene_audio = generate_audio(line, i+1, output_dir=job_dir)
        scene_slide = generate_slide_image(line, i+1, output_dir=job_dir, bg_image=bg_image)
        
        # Use the requested avatar type for ALL scenes (No more alternating)
        if avatar_type == "logo":
            av_path = logo_av
        elif avatar_type == "human":
            av_path = human_av
        else:
            # Complex modes (pro/user) generate per-scene
            av_path = generate_avatar_video(line, scene_audio, i+1, output_dir=job_dir, avatar_type=avatar_type)
            
        scenes.append({
            "scene": i + 1,
            "text": line,
            "avatar": av_path,
            "audio": scene_audio,
            "slide": scene_slide,
            "layout": "side_avatar" if i % 2 == 0 else "ppt_presentation"
        })

    # --- Composition Logic ---
    from moviepy.editor import ImageClip, AudioFileClip, VideoFileClip, concatenate_videoclips, CompositeVideoClip, ColorClip
    from moviepy.video.fx.all import loop as fx_loop
    
    OUT_W, OUT_H = 854, 480
    clips = []

    for scene in scenes:
        audio_clip = AudioFileClip(scene["audio"])
        duration = audio_clip.duration
        slide_clip = ImageClip(scene["slide"]).set_duration(duration)
        avatar_clip = fx_loop(VideoFileClip(scene["avatar"]).without_audio(), duration=duration)

        if scene["layout"] == "side_avatar":
            SW = int(OUT_W * 0.7)
            AW = OUT_W - SW
            slide_s = slide_clip.resize(height=OUT_H)
            if slide_s.w > SW: slide_s = slide_s.resize(width=SW)
            bg = ColorClip(size=(AW, OUT_H), color=(20, 20, 20)).set_duration(duration)
            av_s = avatar_clip.resize(width=AW)
            clips.append(CompositeVideoClip([
                slide_s.set_position((0,0)),
                bg.set_position((SW, 0)),
                av_s.set_position((SW, (OUT_H - av_s.h)//2))
            ], size=(OUT_W, OUT_H)).set_audio(audio_clip))
        else:
            slide_s = slide_clip.resize(height=OUT_H)
            av_s = avatar_clip.resize(width=180)
            clips.append(CompositeVideoClip([
                slide_s.set_position(("center","center")),
                av_s.set_position((OUT_W-200, OUT_H-160))
            ], size=(OUT_W, OUT_H)).set_audio(audio_clip))

    final = concatenate_videoclips(clips, method="compose")
    output_v = os.path.join(job_dir, "tony_ai_video.mp4")
    final.write_videofile(output_v, fps=24, codec="libx264")
    print(f"\n✅ SUCCESS! Video saved at: {output_v}")
    return output_v

if __name__ == "__main__":
    if len(sys.argv) > 2:
        file_path = sys.argv[1]
        topic = sys.argv[2]
        avatar_type = sys.argv[3] if len(sys.argv) > 3 else "human"
        
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                text = f.read()
            run_tony_pipeline(text, topic, avatar_type)
        else:
            print(f"File not found: {file_path}")
    else:
        sample_tony_text = """
        Newton's first law states that an object at rest stays at rest unless acted upon by a force.
        The second law explains that force equals mass times acceleration, or F equals M A.
        The third law famously says that for every action, there is an equal and opposite reaction.
        """
        run_tony_pipeline(sample_tony_text, "Newton Laws Test")
