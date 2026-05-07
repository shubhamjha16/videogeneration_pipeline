import os
import subprocess
import time
from template_renderer import build_manim_script

def run_test(name, steps, topic):
    print(f"\n🚀 Running Test: {name} ({len(steps)} steps)")
    scenes = [{
        "visual_type": "formula_step_list",
        "visual_data": {
            "heading": f"Test: {name}",
            "steps": steps,
            "duration": 5.0 + len(steps) * 1.5
        }
    }]
    
    script_path = f"scratch/test_{name}.py"
    build_manim_script(
        scenes=scenes,
        image_path=None,
        topic=topic,
        output_path=script_path
    )
    
    print(f"✅ Generated script: {script_path}")
    
    # Peek at the generated code to verify _add_formula_with_overflow calls
    with open(script_path, 'r') as f:
        content = f.read()
        if "_add_formula_with_overflow" in content:
            print("✅ Helper method found in script.")
        else:
            print("❌ Helper method MISSING from script!")

# 1. 3-step derivation
run_test("3step", ["A=B", "B=C", "A=C"], "3-Step Regression")

# 2. 7-step derivation
run_test("7step", [f"Step {i}" for i in range(1, 8)], "7-Step Overflow")

# 3. 12-step derivation
run_test("12step", [f"Deep Step {i}" for i in range(1, 13)], "12-Step Multi-Slide")

# 4. Pythagorean (3-4 steps)
run_test("pythag", ["a^2 + b^2 = c^2", "a^2 = c^2 - b^2", "a = \\sqrt{c^2 - b^2}"], "Pythagorean Regression")

# 5. Cardiac Output
run_test("cardiac", ["CO = HR \\times SV", "HR = 72", "SV = 70", "CO = 72 \\times 70", "CO = 5040 ml/min"], "Cardiac Output Regression")
