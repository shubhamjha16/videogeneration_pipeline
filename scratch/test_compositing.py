import os
import sys

# Ensure parent directory is in path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PIL import Image
from utils.image_compositing import (
    reduce_opacity, 
    apply_blur, 
    composite_atmospheric, 
    composite_accent, 
    find_empty_corner
)

atmo_path = "output/job_test_ambient_001/ambient/atmospheric_0.png"
accent_path = "output/job_test_ambient_001/ambient/accent_0.png"

if not os.path.exists(atmo_path) or not os.path.exists(accent_path):
    print(f"Error: Missing test assets in {os.path.dirname(atmo_path)}")
    sys.exit(1)

# Create cream base
base = Image.new("RGB", (1920, 1080), "#FFF9E6")

# Test 1 - atmospheric only
step1 = composite_atmospheric(base, atmo_path)
step1.save("scratch/composite_test_atmo_only.png")

# Test 2 - accent only at big_statement position
rule = find_empty_corner("big_statement")
step2_only = composite_accent(base, accent_path, rule[0], rule[1])
step2_only.save("scratch/composite_test_accent_only.png")

# Test 3 - both layered
step3 = composite_accent(step1, accent_path, rule[0], rule[1])
step3.save("scratch/composite_test_combined.png")

for f in ["composite_test_atmo_only.png", "composite_test_accent_only.png", "composite_test_combined.png"]:
    path = f"scratch/{f}"
    assert os.path.exists(path), f"MISSING: {path}"
    print(f"{f}: {os.path.getsize(path)} bytes")

print("All 3 composites passed verification")
