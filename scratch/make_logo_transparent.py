import os
from PIL import Image

logo_path = "/Users/apple/Desktop/easetolearn.videogeneration/assets/logo.png"
output_path = "/Users/apple/Desktop/easetolearn.videogeneration/assets/logo_transparent.png"

with Image.open(logo_path) as img:
    img = img.convert("RGBA")
    width, height = img.size
    pixels = img.load()
    
    transparent_count = 0
    
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            
            # Top row or bottom row (the borders)
            if y == 0 or y == height - 1:
                pixels[x, y] = (r, g, b, 0)
                transparent_count += 1
                continue
                
            # White or near-white background
            if r > 240 and g > 240 and b > 240:
                pixels[x, y] = (r, g, b, 0)
                transparent_count += 1
                continue
                
    img.save(output_path)
    print(f"Processed logo saved to: {output_path}")
    print(f"Total transparent pixels: {transparent_count} ({transparent_count / (width * height) * 100:.2f}%)")
