import os
from template_renderer import build_manim_script
import subprocess

scenes = [
    {
      "visual_type": "formula_derivation",
      "visual_data": {
        "heading": "Ejection Fraction",
        "steps": [
          "EF = \\frac{SV}{EDV}",
          "EF = \\frac{EDV - ESV}{EDV}",
          "EF = \\frac{120 - 50}{120}",
          "EF = \\frac{70}{120}",
          "EF = 0.58"
        ],
        "duration": 8.0
      },
      "narration_text": "Observe."
    }
]

output_path = "scratch/test_derivation_script.py"

build_manim_script(
    scenes=scenes,
    image_path=None,
    topic="Ejection Fraction Test",
    output_path=output_path
)

print("Script written. Rendering...")
subprocess.run(["manim", "-ql", output_path, "IndustrialRender"], check=True)
