from manim import *

class LaTeXTest(Scene):
    def construct(self):
        equation = MathTex(r"e^{i\pi} + 1 = 0")
        self.play(Write(equation))
        self.wait(2)
