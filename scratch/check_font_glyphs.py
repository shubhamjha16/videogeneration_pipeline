import os
from PIL import Image, ImageFont, ImageDraw

def test_font_chars(font_path, chars):
    if not os.path.exists(font_path):
        print(f"Font does not exist: {font_path}")
        return
    
    font = ImageFont.truetype(font_path, 20)
    
    # Missing glyph character
    missing_char = "\uFFFF"
    missing_mask = font.getmask(missing_char)
    missing_bbox = missing_mask.getbbox()
    
    missing_pixels = list(missing_mask) if missing_bbox else []
    
    print(f"\nFont: {font_path}")
    missing_count = 0
    for char in chars:
        mask = font.getmask(char)
        bbox = mask.getbbox()
        
        if not bbox:
            print(f"  ❌ Missing glyph (No bbox): '{char}' ({hex(ord(char))})")
            missing_count += 1
            continue
            
        pixels = list(mask)
        # If the mask is identical to the missing glyph mask, it's missing/fallback box
        if pixels == missing_pixels:
            print(f"  ❌ Missing glyph (Fallback box): '{char}' ({hex(ord(char))})")
            missing_count += 1
            
    if missing_count == 0:
        print("  ✅ All characters are fully supported!")

fonts_to_test = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Apple Symbols.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]

test_chars = "∫₁₂₃₄₅₆₇₈₉ₓₙ⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱˣʸ"

for f in fonts_to_test:
    test_font_chars(f, test_chars)
