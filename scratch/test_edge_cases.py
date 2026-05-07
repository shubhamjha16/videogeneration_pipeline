from template_renderer import build_manim_script
import subprocess

scenes = [
    {
      "visual_type": "formula_derivation",
      "visual_data": {
        "heading": "Edge Case 1: Notation Change",
        "steps": ["\\frac{a}{b} = c", "a/b = c"],
        "duration": 4.0
      },
      "narration_text": "Notation change"
    },
    {
      "visual_type": "formula_derivation",
      "visual_data": {
        "heading": "Edge Case 2: Variable Introduction",
        "steps": ["x = 5", "x + y = 5 + y"],
        "duration": 4.0
      },
      "narration_text": "Variable intro"
    },
    {
      "visual_type": "formula_derivation",
      "visual_data": {
        "heading": "Edge Case 3: Fraction Simplification",
        "steps": ["\\frac{70}{120} = x", "0.583 = x"],
        "duration": 4.0
      },
      "narration_text": "Simplification"
    }
]

output_path = "scratch/test_edge_cases_script.py"

build_manim_script(
    scenes=scenes,
    image_path=None,
    topic="Edge Cases Test",
    output_path=output_path
)

print("Script written. Rendering...")
subprocess.run(["manim", "-ql", output_path, "EaseToLearnScene"], check=True)
