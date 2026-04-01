from manim import *

class JEEMathIntegration(Scene):
    def construct(self):
        # 1. Title
        title = Text("Integration by Parts", font_size=40).to_edge(UP)
        problem = Text("Solve: Integral of ln(x) dx", font_size=32, color=BLUE).next_to(title, DOWN, buff=0.5)

        # 2. Formula
        formula = Text("Integral(u dv) = uv - Integral(v du)", font_size=28, color=YELLOW).to_edge(LEFT, buff=1)

        # 3. Substitutions
        sub_u = Text("u = ln(x)  =>  du = 1/x dx", font_size=24).next_to(formula, DOWN, buff=0.5, aligned_edge=LEFT)
        sub_v = Text("dv = dx    =>  v = x", font_size=24).next_to(sub_u, DOWN, buff=0.3, aligned_edge=LEFT)

        # 4. Steps
        step1 = Text("= x ln(x) - Integral(x * 1/x dx)", font_size=28).next_to(sub_v, DOWN, buff=0.8, aligned_edge=LEFT)
        step2 = Text("= x ln(x) - Integral(1 dx)", font_size=28).next_to(step1, DOWN, buff=0.3, aligned_edge=LEFT)
        final = Text("= x ln(x) - x + C", font_size=36, color=GREEN).next_to(step2, DOWN, buff=0.5, aligned_edge=LEFT)

        # Animations
        self.play(Write(title))
        self.play(Write(problem))
        self.wait(2)
        self.play(Write(formula))
        self.wait(2)
        self.play(Write(sub_u))
        self.play(Write(sub_v))
        self.wait(3)
        self.play(Write(step1))
        self.wait(2)
        self.play(Transform(step1.copy(), step2))
        self.wait(2)
        self.play(Write(final))
        self.wait(5)
