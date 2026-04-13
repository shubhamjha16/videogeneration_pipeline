import os
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy.editor import ImageClip

def create_text_clip(text, fontsize=70, color='white', font_path=None, stroke_width=0, stroke_color='black', size=(1280, 720), duration=2):
    """
    ImageMagick-free replacement for TextClip using Pillow.
    Returns a transparent MoviePy ImageClip.
    """
    # Industrial Discovery Loop: Try multiple standard system fonts
    if not font_path:
        # Standardize candidates to avoid path mismatches in Docker
        font_candidates = [
            # Linux Paths (Priority for ECS)
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            # Standard Assets Path
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts", "Inter-Bold.ttf"),
            # Mac Fallbacks
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
        ]

    else:
        font_candidates = [font_path]
    
    font = None
    for candidate in font_candidates:
        try:
            font = ImageFont.truetype(candidate, fontsize)
            break
        except Exception:
            continue
            
    if not font:
        print("⚠️  Warning: No preferred fonts found. Using basic PIL fallback.")
        font = ImageFont.load_default()

    # Create transparent image
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Calculate text position (center)
    # PIL 10.0+ uses getbbox
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    pos = ((size[0] - text_w) // 2, (size[1] - text_h) // 2)
    
    # Draw stroke if requested
    if stroke_width > 0:
        draw.text(pos, text, font=font, fill=stroke_color, 
                  stroke_width=stroke_width, stroke_fill=stroke_color)
    
    # Draw main text
    draw.text(pos, text, font=font, fill=color)
    
    # Convert to numpy array for MoviePy
    img_np = np.array(img)
    
    return ImageClip(img_np).set_duration(duration)

if __name__ == "__main__":
    # Quick visual verification
    clip = create_text_clip("IMAGE MAGICK FREE", fontsize=100, stroke_width=2)
    clip.save_frame("test_text.png")
    print("✅ Text renderer verified: test_text.png created.")
