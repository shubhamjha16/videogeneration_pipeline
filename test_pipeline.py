from tts_generator import generate_audio
from slide_generator import generate_slide_image
from avatar_generator import generate_avatar_video
import os
import time

import PIL
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS


# Create a unique job folder for this request
job_id = f"job_{int(time.time())}"
job_dir = os.path.join("output", job_id)
os.makedirs(job_dir, exist_ok=True)
print(f"📁 Created job directory: {job_dir}")

print("🎬 Starting Test Pipeline - Simulating n8n request with basic static slides")

# This is the exact text from the User's Tony AI physics screenshot
tony_explanation = [
    "COVID-19 is caused by SARS-CoV-2, a novel coronavirus first identified in Wuhan, China in December 2019.",
    "The virus belongs to the Betacoronavirus genus and has a positive-sense single-stranded RNA genome of about 30 kilobases.",
    "SARS-CoV-2 enters human cells by binding its spike protein to the ACE2 receptor, found abundantly in lung, heart, and kidney cells.",
    "The virus spreads primarily through respiratory droplets and aerosols when an infected person coughs, sneezes, talks, or breathes.",
    "The immune response involves innate immunity triggering cytokines, and adaptive immunity producing antibodies via B-cells and killer T-cells.",
]

# 🎭 Pre-render shared avatars (one logo, one human)
print("\n🎭 Pre-rendering shared avatar clips (rendered ONCE each)...")
_ref_audio = generate_audio("Reference", 0, output_dir=job_dir)

logo_avatar_path  = generate_avatar_video("", _ref_audio, 100, output_dir=job_dir, avatar_type="logo")
human_avatar_path = generate_avatar_video("", _ref_audio, 101, output_dir=job_dir, avatar_type="human")

scenes = []
for i, line in enumerate(tony_explanation):
    # Alternate between logo and human avatars
    av_path = logo_avatar_path if i % 2 == 0 else human_avatar_path
    scenes.append({
        "scene": i + 1,
        "text": line,
        "audio": "",   # filled below
        "slide": "",   # filled below
        "avatar": av_path,
        "layout": "side_avatar" if i % 2 == 0 else "ppt_presentation"
    })

for scene in scenes:
    print(f"\nProcessing Scene {scene['scene']}...")
    audio_file = generate_audio(scene["text"], scene["scene"], output_dir=job_dir)
    slide_file = generate_slide_image(scene["text"], scene["scene"], output_dir=job_dir)
    scene["audio"] = audio_file
    scene["slide"] = slide_file

# --- Composition Logic ---
try:
    from moviepy.editor import ImageClip, AudioFileClip, VideoFileClip, concatenate_videoclips, CompositeVideoClip, ColorClip
    from moviepy.video.fx.all import loop as fx_loop
    clips = []

    OUT_W, OUT_H = 854, 480   # 480p

    for scene in scenes:
        layout_type = scene["layout"]
        audio_clip = AudioFileClip(scene["audio"])
        duration   = audio_clip.duration
        
        slide_clip = ImageClip(scene["slide"]).set_duration(duration)
        # Looping logic: the avatar is a 3s loop. We loop it to match audio duration.
        avatar_clip_source = VideoFileClip(scene["avatar"])
        avatar_clip = fx_loop(avatar_clip_source, duration=duration)

        print(f"Applying Layout: {layout_type} for Scene {scene['scene']}...")

        if layout_type == "side_avatar":
            SLIDE_W  = int(OUT_W * 0.70)
            AVATAR_W = OUT_W - SLIDE_W

            slide_scaled = slide_clip.resize(height=OUT_H)
            if slide_scaled.w > SLIDE_W:
                slide_scaled = slide_scaled.resize(width=SLIDE_W)

            right_bg      = ColorClip(size=(AVATAR_W, OUT_H), color=(20, 20, 20)).set_duration(duration)
            avatar_scaled = avatar_clip.resize(width=AVATAR_W)
            avatar_y      = (OUT_H - avatar_scaled.h) // 2

            final_scene_clip = CompositeVideoClip([
                slide_scaled.set_position((0, 0)),
                right_bg.set_position((SLIDE_W, 0)),
                avatar_scaled.set_position((SLIDE_W, avatar_y)),
            ], size=(OUT_W, OUT_H))
        
        else: # ppt_presentation (Full slide background + tiny avatar overlay bottom right)
            slide_scaled = slide_clip.resize(height=OUT_H)
            avatar_scaled = avatar_clip.resize(width=180) # Tiny avatar overlay
            
            final_scene_clip = CompositeVideoClip([
                slide_scaled.set_position(("center", "center")),
                avatar_scaled.set_position((OUT_W - 200, OUT_H - 160))
            ], size=(OUT_W, OUT_H))

        final_scene_clip = final_scene_clip.set_audio(audio_clip)
        clips.append(final_scene_clip)

    final_video = concatenate_videoclips(clips, method="compose")
    output_v = os.path.join(job_dir, "final_tony_sample_check.mp4")
    final_video.write_videofile(output_v, fps=24, codec="libx264")

    print(f"\n✅ SUCCESS! Your sample video is ready at: {output_v}")

except Exception as e:
    import traceback; traceback.print_exc()
    print(f"Error during video composition: {e}")
