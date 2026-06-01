import os
from PIL import Image

poses_dir = "/Users/apple/Desktop/easetolearn.videogeneration/tony_avatars_poses"
files = [f for f in os.listdir(poses_dir) if f.endswith(".png")]

print(f"Inspecting {len(files)} files in {poses_dir}...\n")

for f in sorted(files):
    path = os.path.join(poses_dir, f)
    try:
        with Image.open(path) as img:
            mode = img.mode
            size = img.size
            
            # Check extrema for alpha channel
            extrema = img.getextrema()
            has_alpha = len(extrema) == 4
            
            min_a, max_a = None, None
            if has_alpha:
                min_a, max_a = extrema[3]
            elif mode == "LA":
                min_a, max_a = extrema[1]
                
            corners = [
                img.getpixel((0, 0)),
                img.getpixel((size[0]-1, 0)),
                img.getpixel((0, size[1]-1)),
                img.getpixel((size[0]-1, size[1]-1))
            ]
            
            print(f"File: {f}")
            print(f"  Format: {img.format} | Mode: {mode} | Size: {size}")
            print(f"  Alpha Extrema: min={min_a}, max={max_a}")
            print(f"  Corner colors: {corners}")
            print("-" * 50)
    except Exception as e:
        print(f"Error reading {f}: {e}")
