import argparse
import os
import sys
import shutil
from moviepy.editor import VideoFileClip, concatenate_videoclips
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("GEMINI_API_KEY"):
    # Try absolute path
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

if os.getenv("GEMINI_API_KEY"):
    print("✅ GEMINI_API_KEY loaded.")
else:
    print("❌ GEMINI_API_KEY NOT FOUND in environment.")

def detect_mode(text):
    text_lower = text.lower().strip()
    
    # Explicit Tags have highest priority
    if text_lower.startswith("[p]") or text_lower.startswith("[presentation]"):
        return "presentation"
    if text_lower.startswith("[m]") or text_lower.startswith("[math]"):
        return "math"

    math_keywords = [
        "integral", "derivative", "differentiate", "solve for", 
        "acceleration", "velocity", "force", "mass", "d/dx", "lim "
    ]
    for kw in math_keywords:
        if kw in text_lower:
            return "math"
    return "presentation"

def run_presentation_stage(text, topic, avatar, job_dir):
    print(f"🎬 [Stage: PRESENTATION] {topic}")
    from tony_pipeline import run_tony_pipeline
    return run_tony_pipeline(text, topic, avatar, output_dir=job_dir)

def run_math_stage(text, topic, avatar, job_dir, script_path=None):
    print(f"📐 [Stage: MATH] {topic}")
    os.makedirs(job_dir, exist_ok=True)
    
    # Handle auto-math when no script is provided
    if not script_path:
        print(f"🤖 AI Technical Director: Brainstorming animation for topic '{topic}'...")
        from manim_ai_generator import generate_manim_script
        script_code = generate_manim_script(text, topic)
        
        if script_code.startswith("Error"):
            print(f"❌ AI Script Generation Failed: {script_code}")
            return None

        script_path = os.path.join(job_dir, "ai_directed_script.py")
        with open(script_path, "w") as f:
            f.write(script_code)
        print(f"✅ AI Script Generated: {script_path}")

    # 1. Generate audio if text is provided
    print(f"🎙️ Generating narration for math stage...")
    from tts_generator import generate_audio
    # Convert text to single line for math narration if needed, or handle lines
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.strip():
            generate_audio(line.strip(), i, output_dir=job_dir)
    
    # 2. Render Manim
    print(f"📐 Rendering Manim Animation: {script_path}...")
    import shlex
    import re
    # Sanitize class name for Manim (alphanumeric only)
    class_name = re.sub(r'[^a-zA-Z0-9]', '', topic)
    safe_script = shlex.quote(script_path)
    render_cmd = f"./venv/bin/manim -ql {safe_script} {class_name} -o {class_name}.mp4"
    os.system(render_cmd)

    # 3. Stitch
    from stitch_math_video import run_math_stitcher
    manim_video = f"media/videos/{os.path.basename(script_path).replace('.py','')}/480p15/{class_name}.mp4"
    return run_math_stitcher(topic, manim_video, avatar, job_dir=job_dir)

def main():
    parser = argparse.ArgumentParser(description="EaseToLearn Unified Video Generation Pipeline")
    parser.add_argument("--mode", choices=["presentation", "math", "explainer", "auto", "combo"], required=True, help="Generation mode")
    parser.add_argument("--topic", required=True, help="Topic name for the video")
    parser.add_argument("--script", help="Path to Manim script")
    parser.add_argument("--inline-script", help="Raw Manim code (string)")
    parser.add_argument("--text", help="Path to narration text file")
    parser.add_argument("--avatar", choices=["logo", "human"], default="human", help="Avatar style")

    args = parser.parse_args()

    # Load text content
    raw_text = ""
    if args.text and os.path.exists(args.text):
        with open(args.text, 'r') as f:
            raw_text = f.read()

    sanitized_topic = args.topic.lower().replace(' ', '_').replace('&', 'and').replace('(', '').replace(')', '')
    job_dir = os.path.join("output", f"job_{sanitized_topic}")
    if os.path.exists(job_dir):
        # Wipe media files to start fresh
        for f in os.listdir(job_dir):
            if f.endswith(".m4a") or f.endswith(".mp3") or f.endswith(".mp4") or f.endswith("_slide.png"):
                os.remove(os.path.join(job_dir, f))
        print(f"🧹 Cleaned existing job directory: {job_dir}")
    else:
        os.makedirs(job_dir, exist_ok=True)

    mode = args.mode
    if mode == "auto":
        mode = detect_mode(raw_text)
        print(f"🕵️ Auto-Discovery: Detected {mode.upper()} mode.")

    print(f"🚀 Initializing EaseToLearn Pipeline [Mode: {mode.upper()}]")
    
    if mode == "combo":
        chunks = raw_text.split("---")
        part_videos = []
        for i, chunk in enumerate(chunks):
            chunk = chunk.strip()
            if not chunk: continue
            
            chunk_topic = f"{args.topic} Part {i+1}"
            chunk_mode = detect_mode(chunk)
            part_job_dir = os.path.join(job_dir, f"part_{i+1}")
            
            # Check for manually injected or previously generated scripts
            existing_script = os.path.join(job_dir, "ai_directed_script.py")
            script_to_use = existing_script if os.path.exists(existing_script) else None
            
            if chunk_mode == "presentation":
                video = run_presentation_stage(chunk, chunk_topic, args.avatar, part_job_dir)
            else:
                video = run_math_stage(chunk, chunk_topic, args.avatar, part_job_dir, script_path=script_to_use)
            
            if video and os.path.exists(video):
                part_videos.append(video)
        
        if part_videos:
            print(f"🔗 Stitching {len(part_videos)} parts into final video...")
            clips = [VideoFileClip(v) for v in part_videos]
            final_clip = concatenate_videoclips(clips)
            final_output = os.path.join(job_dir, f"combo_{args.topic.lower().replace(' ', '_')}.mp4")
            final_clip.write_videofile(final_output, fps=15, codec="libx264")
            print(f"✅ COMBO SUCCESS! Final video at: {final_output}")

    elif mode == "presentation":
        run_presentation_stage(raw_text, args.topic, args.avatar, job_dir)

    elif mode == "math":
        run_math_stage(raw_text, args.topic, args.avatar, job_dir, args.script)

    elif mode == "explainer":
        print("🚧 Explainer Mode is under development.")

if __name__ == "__main__":
    main()
