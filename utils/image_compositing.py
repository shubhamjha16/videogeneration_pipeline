"""
utils/image_compositing.py

Standalone image manipulation and compositing helpers for the ambient visual system.
Provides tools to add faded background (atmospheric) imagery and sharp accent illustrations
to base presentation slides using PIL.
"""

from PIL import Image, ImageFilter, ImageChops, ImageEnhance
from typing import Optional, Tuple
import os

PLACEMENT_RULES = {
    "chaos_chapter":   {"pos": (1500, 750),  "size": (320, 280)},
    "title_card":      {"pos": (1550, 780),  "size": (280, 250)},
    "big_statement":   {"pos": (1550, 780),  "size": (280, 250)},
    "key_highlight":   {"pos": (80,   780),  "size": (280, 250)},
    "bullets":         None,
    "two_column":      None,
    "stats_dashboard": None,
    "summary":         None,
    "steps":           None,
    "quote_card":      None,
    "definition_card": None,
    "before_after":    None,
    "callout_box":     None,
    "ranking_list":    None,
    "image_hero":      None,
    "timeline":        None,
}

ATMOSPHERIC_LAYOUTS = {"chaos_chapter", "title_card", "big_statement", "key_highlight"}

def _enhance_for_multiply(img: Image.Image) -> Image.Image:
    """Boosts contrast and brightness so cream backgrounds become white (invisible in Multiply)."""
    # 1. Boost Contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.5)
    # 2. Boost Brightness
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.1)
    return img

def reduce_opacity(image: Image.Image, alpha: float) -> Image.Image:
    """Reduces the alpha channel by the given multiplier."""
    if not (0.0 <= alpha <= 1.0):
        raise ValueError("Alpha must be between 0.0 and 1.0")
    img = image.convert('RGBA')
    r, g, b, a = img.split()
    a = a.point(lambda p: p * alpha)
    return Image.merge('RGBA', (r, g, b, a))

def apply_blur(image: Image.Image, radius: float = 3.0) -> Image.Image:
    return image.filter(ImageFilter.GaussianBlur(radius=radius))

def composite_atmospheric(
    base: Image.Image, 
    atmospheric_path: Optional[str], 
    opacity: float = 0.12, 
    blur_radius: float = 5.0
) -> Image.Image:
    if not atmospheric_path or not os.path.exists(atmospheric_path):
        return base.copy()
    try:
        with Image.open(atmospheric_path) as atmo:
            atmo = atmo.convert("RGB")
            atmo = _enhance_for_multiply(atmo)
            atmo_resized = atmo.resize(base.size, Image.LANCZOS)
            atmo_blurred = apply_blur(atmo_resized, blur_radius)
            
            # For atmospheric, we blend toward white based on opacity
            # so that when multiplied, it is faint.
            white = Image.new("RGB", base.size, (255, 255, 255))
            atmo_faded = Image.blend(white, atmo_blurred, opacity)
            
            # Use Multiply to composite
            return ImageChops.multiply(base.convert("RGB"), atmo_faded)
    except Exception as e:
        print(f"Warning: Failed to composite atmospheric image: {e}")
        return base.copy()

def composite_accent(
    base: Image.Image, 
    accent_path: Optional[str],
    position: Tuple[int, int], 
    size: Tuple[int, int]
) -> Image.Image:
    if not accent_path or not os.path.exists(accent_path):
        return base.copy()
    try:
        with Image.open(accent_path) as accent:
            accent = accent.convert("RGB")
            accent = _enhance_for_multiply(accent)
            accent_resized = accent.resize(size, Image.LANCZOS)
            
            # Create a full-size white canvas and paste the accent onto it
            overlay = Image.new("RGB", base.size, (255, 255, 255))
            overlay.paste(accent_resized, position)
            
            # Multiply onto base
            return ImageChops.multiply(base.convert("RGB"), overlay)
    except Exception as e:
        print(f"Warning: Failed to composite accent image: {e}")
        return base.copy()

def find_empty_corner(layout_type: str) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """
    Looks up the placement coordinates and size for an accent image based on layout type.
    
    Args:
        layout_type: String identifier of the slide layout.
        
    Returns:
        Tuple of ((x, y), (width, height)) or None if layout not supported.
    """
    rule = PLACEMENT_RULES.get(layout_type)
    if rule is None:
        return None
    return (rule["pos"], rule["size"])

def should_apply_atmospheric(layout_type: str) -> bool:
    """
    Determines if a layout should receive the atmospheric background treatment.
    
    Args:
        layout_type: String identifier of the slide layout.
        
    Returns:
        Boolean indicating if atmospheric layer should be applied.
    """
    return layout_type in ATMOSPHERIC_LAYOUTS

# ─── TONY CARTOON CHARACTER PLACEMENT ──────────────────────────────────────────

TONY_PLACEMENT_RULES = {
    "chaos_chapter":   {"pos": (50, 600),   "size": (450, 450)}, # Bottom left
    "title_card":      {"pos": (1450, 550),  "size": (400, 450)}, # Bottom right
    "big_statement":   {"pos": (1450, 550),  "size": (400, 450)}, # Bottom right
    "key_highlight":   {"pos": (1450, 550),  "size": (400, 450)}, # Bottom right
    "bullets":         {"pos": (1480, 580),  "size": (380, 420)}, # Bottom right
    "two_column":      {"pos": (760, 600),   "size": (400, 420)}, # Middle bottom
    "summary":         {"pos": (1450, 550),  "size": (400, 450)}, # Bottom right
    "steps":           {"pos": (1450, 550),  "size": (400, 450)}, # Bottom right
    "quote_card":      {"pos": (1450, 650),  "size": (350, 380)}, # Bottom right
}

def composite_tony_pose(
    base: Image.Image, 
    pose_path: Optional[str],
    layout_type: str
) -> Image.Image:
    """Composites the Tony RGBA pose onto the slide based on layout rules."""
    if not pose_path or not os.path.exists(pose_path):
        return base
    
    rule = TONY_PLACEMENT_RULES.get(layout_type)
    if not rule:
        # Fallback to general corner if layout not defined
        rule = {"pos": (1450, 550), "size": (400, 450)}

    try:
        print(f"   [tony] attempting to composite {os.path.basename(pose_path)} for layout {layout_type}")
        with Image.open(pose_path) as pose:
            pose = pose.convert("RGBA")
            # Resize keeping aspect ratio
            w, h = rule["size"]
            pose.thumbnail((w, h), Image.LANCZOS)
            
            # Create transparent overlay same size as base
            overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
            
            # Center the thumbnail in the reserved slot
            actual_w, actual_h = pose.size
            x, y = rule["pos"]
            # Adjust y if it's smaller than the slot to keep it on the floor
            adjusted_y = y + (h - actual_h)
            
            print(f"   [tony] placing at ({x}, {adjusted_y}) with size {pose.size}")
            overlay.paste(pose, (x, adjusted_y))
            
            # Alpha composite onto base
            base_rgba = base.convert("RGBA")
            combined = Image.alpha_composite(base_rgba, overlay)
            return combined.convert("RGB")
    except Exception as e:
        print(f"   ❌ [tony] error: {e}")
        return base

