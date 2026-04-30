import os
import sys
import json

# Add project root to path
sys.path.append("/Users/apple/Desktop/easetolearn.videogeneration")

from template_renderer import build_manim_script
from image_generator import generate_concept_image
from tts_generator import generate_audio
import subprocess

# Generate the image using OpenAI (as requested)
print("🎨 Generating image using OpenAI...")
image_path = generate_concept_image("Internal Heart Anatomy", subject="medical", output_dir="/Users/apple/Desktop/easetolearn.videogeneration/scratch")
print(f"✅ Image generated at: {image_path}")

# Mock JSON Scenes
scenes = [
    {
        "visual_type": "title_card",
        "visual_data": {"title": "Cardiovascular Anatomy", "subtitle": "The Internal Structures of the Heart"},
        "narration_text": "Today we will examine the internal structures of the human heart."
    },
    {
        "visual_type": "annotated_image",
        "visual_data": {
            "label": "The Left Ventricle",
            "region": "lower_right",
            "bullets": [
                "Thickest muscular wall",
                "Pumps oxygenated blood to body",
                "High-pressure chamber"
            ],
            "image_path": image_path
        },
        "narration_text": "Notice the thick wall of the left ventricle, which allows it to pump blood against the high pressure of the systemic circulation."
    },
    {
        "visual_type": "mcq_layout",
        "visual_data": {
            "question": "Which heart valve prevents backflow into the left atrium?",
            "options": {
                "A": "Tricuspid Valve",
                "B": "Mitral Valve",
                "C": "Pulmonary Valve",
                "D": "Aortic Valve"
            }
        },
        "narration_text": "Let us test your knowledge. Which valve is responsible for preventing backflow into the left atrium?"
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "letter": "B",
            "reason": "The Mitral Valve (or Bicuspid) is located between the left atrium and left ventricle."
        },
        "narration_text": "The correct answer is B, the Mitral Valve."
    },
    {
        "visual_type": "cross_out",
        "visual_data": {
            "letters": ["A", "C", "D"]
        },
        "narration_text": "The other valves serve the right side of the heart or the great vessels."
    },
    {
        "visual_type": "answer_reveal",
        "visual_data": {
            "letter": "B",
            "text": "Mitral Valve"
        },
        "narration_text": "Therefore, B is the final answer."
    }
]

# 1. Generate Audio for each scene
print("🎤 Generating narration audio...")
audio_files = []
for i, scene in enumerate(scenes):
    text = scene.get("narration_text", "")
    if text:
        audio_path, _ = generate_audio(text, i, output_dir="/Users/apple/Desktop/easetolearn.videogeneration/scratch/audio")
        audio_files.append(audio_path)

# 2. Combine Audio
print("🎵 Combining audio files...")
combined_audio = "/Users/apple/Desktop/easetolearn.videogeneration/scratch/combined_audio.mp3"
with open("/Users/apple/Desktop/easetolearn.videogeneration/scratch/audio_list.txt", "w") as f:
    for af in audio_files:
        f.write(f"file '{af}'\n")

# Use ffmpeg to concatenate
subprocess.run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0", 
    "-i", "/Users/apple/Desktop/easetolearn.videogeneration/scratch/audio_list.txt", 
    "-c", "copy", combined_audio
], check=True)

# 3. Generate Manim script
output_script = "/Users/apple/Desktop/easetolearn.videogeneration/scratch/final_test_render.py"
build_manim_script(scenes, "dummy.png", "Heart Anatomy", output_script)
print(f"✅ Manim script generated at: {output_script}")

# 4. Render Manim video
print("🎬 Rendering Manim video...")
render_dir = "/Users/apple/Desktop/easetolearn.videogeneration/scratch/media"
subprocess.run([
    "python3", "-m", "manim", "-ql", output_script, "EaseToLearnScene", 
    "--media_dir", render_dir
], check=True)

# 5. Stitch Audio + Video
video_path = f"{render_dir}/videos/final_test_render/1080p15/EaseToLearnScene.mp4"
final_output = "/Users/apple/Desktop/easetolearn.videogeneration/scratch/final_video_with_sound.mp4"

print("🎞️ Stitching audio and video...")
subprocess.run([
    "ffmpeg", "-y", "-i", video_path, "-i", combined_audio, 
    "-c:v", "copy", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0", 
    "-shortest", final_output
], check=True)

print(f"🚀 FINAL VIDEO WITH SOUND: {final_output}")

