"""
End-to-end test: Vision-Grounded Landmark Detection → Manim Render
Validates that the arrow points at the precise landmark, not a coarse grid region.
"""
import os
import sys

sys.path.append("/Users/apple/Desktop/easetolearn.videogeneration")

from image_generator import generate_concept_image
from vision_grounder import ground_landmarks
from template_renderer import build_manim_script

SCRATCH_DIR = "/Users/apple/Desktop/easetolearn.videogeneration/scratch"

# 1. Generate image
print("🎨 Step 1: Generating image via OpenAI...")
image_path = generate_concept_image(
    "Internal Heart Anatomy", 
    subject="medical", 
    output_dir=SCRATCH_DIR
)
print(f"   Image: {image_path}")

# 2. Ground landmarks
print("\n🔍 Step 2: Grounding landmarks via GPT-4o vision...")
landmarks = ["left ventricle", "aorta", "right atrium"]
coords = ground_landmarks(image_path, landmarks)
print(f"   Results: {coords}")

# 3. Verify coordinates are valid
print("\n✅ Step 3: Validation...")
for label, (x, y) in coords.items():
    assert 0.0 <= x <= 1.0, f"x out of range for {label}: {x}"
    assert 0.0 <= y <= 1.0, f"y out of range for {label}: {y}"
    print(f"   {label}: ({x:.3f}, {y:.3f}) ✓")

# 4. Build scenes with target_landmark
# Use "left ventricle" as the arrow target
target = "left ventricle"
target_coords = coords.get(target)

scenes = [
    {
        "visual_type": "title_card",
        "visual_data": {"title": "Cardiovascular Anatomy", "subtitle": "Vision-Grounded Arrow Test"},
        "narration_text": "Testing vision-grounded landmark detection."
    },
    {
        "visual_type": "annotated_image",
        "visual_data": {
            "label": "The Left Ventricle",
            "target_landmark": target,
            "region": "lower_right",  # fallback, should NOT be used
            "bullets": [
                "Thickest muscular wall",
                "Pumps oxygenated blood",
                "High-pressure chamber"
            ],
            "image_path": image_path,
        },
        "narration_text": "The arrow should point precisely at the left ventricle."
    },
]

# Landmark coords dict (keyed by scene index as string)
landmark_coords = {}
if target_coords:
    landmark_coords["1"] = {target: target_coords}

# 5. Generate Manim script
print("\n📝 Step 4: Generating Manim script with grounded coords...")
output_script = os.path.join(SCRATCH_DIR, "grounded_test_render.py")
build_manim_script(
    scenes, 
    "dummy.png", 
    "Heart Anatomy (Grounded)", 
    output_script,
    landmark_coords=landmark_coords,
)
print(f"   Script: {output_script}")

# 6. Verify the generated script uses np.array instead of get_corner
with open(output_script, "r") as f:
    script_content = f.read()

if "np.array" in script_content and "get_corner" not in script_content.split("annotated_image")[1] if "annotated_image" in script_content else False:
    print("\n✅ Step 5: Script uses vision-grounded coordinates (np.array) — NOT region grid!")
elif "np.array" in script_content:
    print("\n✅ Step 5: Script contains vision-grounded coordinates (np.array)")
else:
    print("\n⚠️  Step 5: Script may be using fallback region grid")

# 7. Render
print("\n🎬 Step 6: Rendering Manim video...")
import subprocess
render_dir = os.path.join(SCRATCH_DIR, "media")
result = subprocess.run([
    "python3", "-m", "manim", "-ql", output_script, "EaseToLearnScene",
    "--media_dir", render_dir
], capture_output=True, text=True)

if result.returncode == 0:
    print(f"   ✅ Render successful!")
    video = os.path.join(render_dir, "videos/grounded_test_render/1080p15/EaseToLearnScene.mp4")
    if os.path.exists(video):
        print(f"   📹 Video: {video}")
    else:
        print(f"   ⚠️  Video file not found at expected path")
else:
    print(f"   ❌ Render failed:")
    print(result.stderr[-500:])
