import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from template_renderer import build_manim_script, tex

def test_wrapping():
    print("🧪 Testing Smart LaTeX Wrapping...")
    long_text = "This is a very long sentence that should definitely be wrapped into multiple lines by the industrial layout engine to prevent it from going off the edges of the screen."
    wrapped_code = tex(long_text, width=40)
    print(f"Input length: {len(long_text)}")
    print(f"Generated Code Sample:\n{wrapped_code[:200]}...")
    
    if "VGroup" in wrapped_code and "arrange(DOWN" in wrapped_code:
        print("✅ SUCCESS: Wrapping logic triggered VGroup layout.")
    else:
        print("❌ FAILURE: Wrapping logic did not trigger.")

def test_sync():
    print("\n🧪 Testing Proportional Sync logic...")
    scenes = [
        {
            "visual_type": "formula_display",
            "visual_data": {
                "formula": "E=mc^2",
                "label": "Einstein's Mass-Energy Equivalence",
                "duration": 10.0
            }
        }
    ]
    
    script_path = build_manim_script(scenes, None, "Sync Test", "scratch/sync_test.py")
    
    with open(script_path, 'r') as f:
        content = f.read()
        # Look for run_time calculations
        if "run_time=4.0" in content: # 40% of 10.0
             print("✅ SUCCESS: run_time correctly scaled to 4.0s (40% of 10s).")
        else:
             print("❌ FAILURE: run_time did not match expected 4.0s.")

if __name__ == "__main__":
    test_wrapping()
    test_sync()
