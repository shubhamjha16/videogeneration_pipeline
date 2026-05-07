from template_renderer import build_manim_script
import os

# Manually construct a 10-step derivation scene
scenes = [
    {
        "visual_type": "formula_step_list",
        "visual_data": {
            "heading": "The Grand 10-Step Calculus Chain",
            "steps": [
                "f(x) = x^{10}",
                "f'(x) = 10x^9",
                "f''(x) = 90x^8",
                "f^{(3)}(x) = 720x^7",
                "f^{(4)}(x) = 5040x^6",
                "f^{(5)}(x) = 30240x^5",
                "f^{(6)}(x) = 151200x^4",
                "f^{(7)}(x) = 604800x^3",
                "f^{(8)}(x) = 1814400x^2",
                "f^{(9)}(x) = 3628800x"
            ],
            "duration": 15.0
        }
    }
]

output_path = "scratch/test_long_derivation.py"
build_manim_script(
    scenes=scenes,
    image_path=None,
    topic="Long Derivation Test",
    output_path=output_path
)

print(f"✅ Generated long derivation script at: {output_path}")

# Peek at the generated code for scaling
with open(output_path, 'r') as f:
    lines = f.readlines()
    for line in lines[60:150]:
        print(line, end="")
