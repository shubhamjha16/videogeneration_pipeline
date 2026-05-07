from manim import *
import numpy as np

class MathCapture(Scene):
    def construct(self):
        steps = [
            r"EF = \frac{SV}{EDV}",
            r"EF = \frac{120 - 50}{120}",
            r"EF = 0.583"
        ]
        
        for i, step in enumerate(steps):
            tex = MathTex(step).scale(2)
            self.add(tex)
            self.wait(0.1)
            self.renderer.file_writer.output_file = f"math_frame_{i}.png"
            self.renderer.save_static_frame(self)
            self.remove(tex)

