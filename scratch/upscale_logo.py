import os
from PIL import Image

logo_path = "/Users/apple/Desktop/easetolearn.videogeneration/assets/logo.png"
output_path = "/Users/apple/Desktop/easetolearn.videogeneration/assets/logo_upscaled.png"

with Image.open(logo_path) as img:
    # Original size is 121x50
    # Scale up by 8x to 968x400
    target_w, target_h = 968, 400
    
    # We use Lanczos filter for high quality upscaling
    resampling_filter = Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.ANTIALIAS
    upscaled = img.resize((target_w, target_h), resampling_filter)
    
    # Let's sharpen the alpha channel to make it extremely crisp instead of blurry/fuzzy
    # We load the pixels of the upscaled image
    pixels = upscaled.load()
    
    for y in range(target_h):
        for x in range(target_w):
            r, g, b, a = pixels[x, y]
            
            # If there is some transparency, we can sharpen the edge
            if 0 < a < 255:
                # If alpha is greater than 100, make it fully opaque, otherwise fully transparent,
                # or do a smooth step to keep smooth edges
                if a > 120:
                    pixels[x, y] = (r, g, b, 255)
                else:
                    pixels[x, y] = (r, g, b, 0)
                    
    upscaled.save(output_path)
    print(f"Upscaled crisp logo saved to: {output_path}")
