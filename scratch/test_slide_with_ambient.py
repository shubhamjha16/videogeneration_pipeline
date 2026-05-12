import os
import sys
from PIL import Image

# Ensure parent directory is in path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ppt_engine.slide_generator import generate_slide_image

atmo_path = "output/job_test_ambient_001/ambient/atmospheric_0.png"
accent_path = "output/job_test_ambient_001/ambient/accent_0.png"

# Ensure output directory exists
os.makedirs("scratch", exist_ok=True)

print("Generating test slide with ambient assets...")

output_path = generate_slide_image(
    text="98% of vehicles use the 4-stroke cycle",
    scene_idx=99,
    output_dir="scratch",
    layout="big_statement",
    layout_data={
        "statement": "98% of vehicles use the 4-stroke cycle",
        "context": "This widespread use is a testament to the efficiency of the design."
    },
    atmospheric_path=atmo_path,
    accent_path=accent_path
)

if os.path.exists(output_path):
    print(f"Success! Slide generated at: {output_path}")
    print(f"File size: {os.path.getsize(output_path)} bytes")
else:
    print(f"Error: Failed to generate slide at {output_path}")
    sys.exit(1)
