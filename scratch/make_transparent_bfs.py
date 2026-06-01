import os
from PIL import Image

source_path = "/Users/apple/Desktop/easetolearn.videogeneration/tony_avatars_poses/tony_standing_point_up.png"
output_path = "/Users/apple/Desktop/easetolearn.videogeneration/tony_avatars_poses/tony_standing_point_up_transparent.png"

with Image.open(source_path) as img:
    img = img.convert("RGBA")
    width, height = img.size
    
    # Load pixels
    # To get a 2D array of pixels or easily access them, let's load using img.load() which is extremely fast
    pixels_load = img.load()
    
    # We will do a BFS to find all background pixels
    # Queue will store (x, y) coordinates
    queue = []
    visited = set()
    
    # Threshold for background color: R, G, B > 200
    def is_background_color(x, y):
        r, g, b, a = pixels_load[x, y]
        return r > 200 and g > 200 and b > 200
        
    # Initialize queue with all border pixels that match background color criteria
    # Top and bottom borders
    for x in range(width):
        if is_background_color(x, 0):
            queue.append((x, 0))
            visited.add((x, 0))
        if is_background_color(x, height - 1):
            queue.append((x, height - 1))
            visited.add((x, height - 1))
            
    # Left and right borders
    for y in range(height):
        if is_background_color(0, y):
            queue.append((0, y))
            visited.add((0, y))
        if is_background_color(width - 1, y):
            queue.append((width - 1, y))
            visited.add((width - 1, y))
            
    print(f"BFS initialized with {len(queue)} seed border pixels.")
    
    # Perform BFS
    idx = 0
    while idx < len(queue):
        cx, cy = queue[idx]
        idx += 1
        
        # Check 4-way neighbors
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < width and 0 <= ny < height:
                if (nx, ny) not in visited:
                    if is_background_color(nx, ny):
                        visited.add((nx, ny))
                        queue.append((nx, ny))
                        
    print(f"BFS completed. Found {len(visited)} connected background pixels.")
    
    # Update transparency of visited pixels
    for x, y in visited:
        r, g, b, a = pixels_load[x, y]
        pixels_load[x, y] = (r, g, b, 0)
        
    # Save the processed image
    img.save(output_path)
    print(f"Processed transparent image saved to: {output_path}")
    print(f"Total transparent pixels: {len(visited)} ({len(visited) / (width * height) * 100:.2f}%)")
