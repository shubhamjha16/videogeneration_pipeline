import os
from PIL import Image, ImageChops

source_path = "/Users/apple/Desktop/easetolearn.videogeneration/tony_avatars_poses/tony_standing_point_up.png"
output_path = "/Users/apple/Desktop/easetolearn.videogeneration/tony_avatars_poses/tony_standing_point_up_transparent.png"

with Image.open(source_path) as img:
    img = img.convert("RGBA")
    width, height = img.size
    
    # We will build a mask where 0 is background (transparent) and 255 is foreground (opaque)
    # Start with a mask fully white (opaque)
    mask = Image.new("L", (width, height), 255)
    
    # We will flood-fill from the four corners with 0 (transparent) on the mask
    # We use a tolerance. Pillow's ImageDraw.floodfill supports tolerance via comparison,
    # but a custom BFS/DFS in Python or using OpenCV would be fast. Since we want to be pure Python/Pillow
    # and fast, let's write a simple connectivity check or use a thresholding trick.
    # Wait, the background is very bright (RGB all > 235). Let's see if we can do a floodfill.
    # In Pillow, ImageDraw.floodfill(image, xy, value, thresh=...) can do this!
    # Let's import ImageDraw
    from PIL import ImageDraw
    
    # Let's make a copy of the image to use for flood filling
    flood_img = img.convert("RGB")
    
    # Flood fill from the corners on the mask
    # Seeds: (0,0), (width-1, 0), (0, height-1), (width-1, height-1)
    # We will fill the mask with 0 where flood fill matches background color
    corners = [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]
    
    # Let's do a flood fill on the mask
    # To floodfill with tolerance in Pillow, we can do it directly on the mask if we use flood_img as reference
    # Wait, ImageDraw.floodfill does not have a reference image option, it fills the image itself.
    # So we can fill flood_img with a special color (e.g. (255, 0, 255) magenta) starting from corners,
    # with a threshold/tolerance.
    # Let's see if we can floodfill on flood_img:
    for corner in corners:
        seed_color = flood_img.getpixel(corner)
        # Check if the corner is already filled (magenta)
        if flood_img.getpixel(corner) == (255, 0, 255):
            continue
        # Tolerance is 30. If we use threshold, we can use 25
        ImageDraw.floodfill(flood_img, corner, (255, 0, 255), thresh=30)
        
    # Now, any pixel in flood_img that is magenta (255, 0, 255) is background!
    # Let's update the alpha channel of our RGBA image
    rgba_pixels = list(img.getdata())
    flood_pixels = list(flood_img.getdata())
    
    new_pixels = []
    transparent_count = 0
    for rgba, flood in zip(rgba_pixels, flood_pixels):
        if flood == (255, 0, 255):
            new_pixels.append((rgba[0], rgba[1], rgba[2], 0))
            transparent_count += 1
        else:
            new_pixels.append(rgba)
            
    img.putdata(new_pixels)
    img.save(output_path)
    
    print(f"Processed image saved to: {output_path}")
    print(f"Total transparent pixels added: {transparent_count} ({transparent_count / (width * height) * 100:.2f}%)")
