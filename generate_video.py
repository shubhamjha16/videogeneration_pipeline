import os
import sys
import re
from openai import OpenAI
from tts_generator import generate_audio
from slide_generator import generate_slide_image
from avatar_generator import generate_avatar_video

# --- CONFIG ---
client = OpenAI() # Assumes OPENAI_API_KEY is set in environment

def get_dynamic_script(topic):
    print(f"🤖 AI is writing a script for: {topic}...")
    prompt = f"""
    Explain '{topic}' for a high school student. 
    Output exactly 5 items, one per line.
    Each line should be a self-contained sentence for a presentation slide.
    Keep sentences under 20 words. No numbering, no intro, no outro.
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    lines = response.choices[0].message.content.strip().split('\n')
    return [l.strip() for l in lines if l.strip()][:5]

def run_pipeline(topic, avatar_type="human"):
    job_id = f"job_{topic.replace(' ', '_').lower()}"
    job_dir = os.path.join("output", job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    script = get_dynamic_script(topic)
    
    print(f"\n🎭 Pre-rendering shared avatars...")
    _ref_audio = generate_audio("Reference", 0, output_dir=job_dir)
    logo_av = generate_avatar_video("", _ref_audio, 100, output_dir=job_dir, avatar_type="logo")
    human_av = generate_avatar_video("", _ref_audio, 101, output_dir=job_dir, avatar_type="human")

    scenes = []
    for i, line in enumerate(script):
        av_path = logo_av if i % 2 == 0 else human_av
        scenes.append({
            "scene": i + 1,
            "text": line,
            "avatar": av_path,
            "layout": "side_avatar" if i % 2 == 0 else "ppt_presentation"
        })

    for scene in scenes:
        print(f"Processing Scene {scene['scene']}...")
        scene["audio"] = generate_audio(scene["text"], scene["scene"], output_dir=job_dir)
        scene["slide"] = generate_slide_image(scene["text"], scene["scene"], output_dir=job_dir)

    # --- Composition ---
    from moviepy.editor import ImageClip, AudioFileClip, VideoFileClip, concatenate_videoclips, CompositeVideoClip, ColorClip
    from moviepy.video.fx.all import loop as fx_loop
    
    OUT_W, OUT_H = 854, 480
    clips = []

    for scene in scenes:
        audio_clip = AudioFileClip(scene["audio"])
        duration = audio_clip.duration
        slide_clip = ImageClip(scene["slide"]).set_duration(duration)
        avatar_clip = fx_loop(VideoFileClip(scene["avatar"]), duration=duration)

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
    output_v = os.path.join(job_dir, "final_video.mp4")
    final.write_videofile(output_v, fps=24, codec="libx264")
    print(f"\n✅ Done! Video saved at: {output_v}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_pipeline(sys.argv[1])
    else:
        print("Usage: python generate_video.py 'Topic Name'")
