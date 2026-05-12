import os
import sys
from PIL import Image

# Ensure parent directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.image_compositing import composite_atmospheric, composite_accent
from ppt_engine.slide_generator import _base_canvas, _layout_big_statement
from PIL import ImageDraw

# Use existing assets from job 79b99b3a-bc9
job_id = "79b99b3a-bc9"
atmo_path = f"output/job_{job_id}/ambient/atmospheric_0.png"
accent_path = f"output/job_{job_id}/ambient/accent_0.png"

# Load a base slide (scene_1 is big_statement)
W, H = 1920, 1080
img, draw = _base_canvas(seed=1)

# Apply updated atmospheric
img = composite_atmospheric(img, atmo_path, opacity=0.15, blur_radius=5.0)

# Apply layout
data = {
    "statement": "Iron loses electrons through oxidation,",
    "context": "while oxygen gains them through reduction."
}
img, draw = _layout_big_statement(ImageDraw.Draw(img), img, data)

# Apply updated accent
img = composite_accent(img, accent_path, position=(1550, 780), size=(280, 250))

# Save
os.makedirs("scratch", exist_ok=True)
output_path = "scratch/debug_multiply_composite.png"
img.save(output_path)
print(f"Debug image saved to {output_path}")
