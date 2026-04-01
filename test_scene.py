from manim import *
class SquareToCircle(Scene):
    def construct(self):
        circle = Circle()
        self.play(Create(circle))
