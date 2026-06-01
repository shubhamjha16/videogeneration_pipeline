import os
from PIL import Image
from collections import Counter

path = "/Users/apple/Desktop/easetolearn.videogeneration/tony_avatars_poses/tony_standing_point_up.png"

with Image.open(path) as img:
    img = img.convert("RGB")
    width, height = img.size
    
    # Let's collect colors from the 4 edges of the image (first/last 10 rows and columns)
    edge_colors = []
    
    # Top and bottom rows
    for x in range(width):
        for y in range(min(15, height)):
            edge_colors.append(img.getpixel((x, y)))
        for y in range(max(0, height - 15), height):
            edge_colors.append(img.getpixel((x, y)))
            
    # Left and right columns
    for y in range(height):
        for x in range(min(15, width)):
            edge_colors.append(img.getpixel((x, y)))
        for x in range(max(0, width - 15), width):
            edge_colors.append(img.getpixel((x, y)))
            
    color_counter = Counter(edge_colors)
    print(f"Total edge pixels sampled: {len(edge_colors)}")
    print("Most common edge colors:")
    for color, count in color_counter.most_common(20):
        print(f"  Color: {color} | Count: {count} ({count/len(edge_colors)*100:.2f}%)")
