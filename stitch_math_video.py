import os
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip
from PIL import Image
# Fix for MoviePy/Pillow 10+ compatibility
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

def run_math_stitcher(job_name, manim_video_path, avatar_mode="logo", job_dir=None):
    if not job_dir:
        job_dir = os.path.join("output", f"job_{job_name.lower().replace(' ', '_')}")
    os.makedirs(job_dir, exist_ok=True)
    
    output_path = os.path.join(job_dir, f"final_{job_name.lower().replace(' ', '_')}.mp4")
    avatar_path = os.path.join(job_dir, "scene_100_avatar.mp4")

    # 1. Load Assets
    if not os.path.exists(manim_video_path):
        print(f"Error: Manim video not found at {manim_video_path}")
        return None

    manim_clip = VideoFileClip(manim_video_path)
    
    # Concatenate all available audio files in order
    from moviepy.editor import concatenate_audioclips
    # Only pick up narration files (scene_0, scene_1, etc.) and exclude reference/avatar helper files
    import re
    audio_files = [f for f in os.listdir(job_dir) if f.endswith(".m4a") and re.match(r"scene_\d+\.m4a", f)]
    # Exclude scene_9999 which is our reference audio for avatar generation
    audio_files = sorted([f for f in audio_files if "9999" not in f])
    if not audio_files:
        print("Error: No audio files found in job directory.")
        return None
        
    print(f"Concatenating {len(audio_files)} audio files...")
    audio_clips = [AudioFileClip(os.path.join(job_dir, f)) for f in audio_files]
    final_audio = concatenate_audioclips(audio_clips)

    # 2. Adjust Timing
    if final_audio.duration > manim_clip.duration:
        from moviepy.editor import concatenate_videoclips
        last_frame = manim_clip.to_ImageClip(t=manim_clip.duration - 0.5).set_duration(final_audio.duration - manim_clip.duration)
        manim_clip = concatenate_videoclips([manim_clip, last_frame])
    else:
        manim_clip = manim_clip.subclip(0, final_audio.duration)

    manim_clip = manim_clip.set_audio(final_audio)

    # 3. Handle Avatar
    if avatar_mode == "none":
        final_clip = manim_clip
    else:
        from moviepy.video.fx.all import loop as fx_loop
        # Generate avatar if it doesn't exist
        if not os.path.exists(avatar_path):
            from avatar_generator import generate_avatar_video
            from tts_generator import generate_audio
            # Use a unique name to avoid overwriting real scene audio
            _ref = generate_audio("Reference", 9999, output_dir=job_dir)
            avatar_path = generate_avatar_video("", _ref, 100, output_dir=job_dir, avatar_type=avatar_mode)

        avatar_clip = VideoFileClip(avatar_path).resize(height=100)
        avatar_clip = fx_loop(avatar_clip, duration=manim_clip.duration)
        avatar_clip = avatar_clip.set_position(("right", "bottom"))
        final_clip = CompositeVideoClip([manim_clip, avatar_clip])

    final_clip.write_videofile(output_path, fps=15, codec="libx264")
    print(f"Successfully created: {output_path}")
    return output_path

if __name__ == "__main__":
    # For backward compatibility
    run_math_stitcher("calculus_kinematics", "media/videos/kinematics_scene/480p15/KinematicsScene.mp4")
