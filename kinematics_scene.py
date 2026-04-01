from manim import *
import os

# Mock watchdog and screeninfo if they are missing
try:
    import watchdog
except ImportError:
    class Mock:
        pass
    import sys
    sys.modules["watchdog"] = Mock()
    sys.modules["watchdog.events"] = Mock()
    sys.modules["watchdog.observers"] = Mock()

try:
    import screeninfo
except ImportError:
    import sys
    class Mock:
        def get_monitors(self): return []
    sys.modules["screeninfo"] = Mock()

class KinematicsScene(Scene):
    def construct(self):
        # 1. Title
        title = Text("Kinematics + Calculus", font_size=36, color=YELLOW)
        title.to_edge(UP)
        self.play(Write(title))
        self.wait(1)

        # 2. Velocity Function
        v_text = Text("v(t) = 3t² - 6t + 2", font_size=30, color=BLUE)
        v_text.shift(UP * 2)
        self.play(Write(v_text))
        self.wait(1)

        # 3. Part A: Acceleration = 0
        part_a = Text("A) Find t when a(t) = 0", font_size=24, color=YELLOW)
        part_a.next_to(v_text, DOWN, buff=0.5)
        self.play(Write(part_a))
        
        calc_a = VGroup(
            Text("a(t) = v'(t) = 6t - 6", font_size=24),
            Text("6t - 6 = 0", font_size=24),
            Text("t = 1 s", font_size=28, color=GREEN)
        ).arrange(DOWN, aligned_edge=LEFT).next_to(part_a, DOWN, buff=0.3)
        
        for step in calc_a:
            self.play(Write(step))
            self.wait(1)
        
        self.wait(2)
        self.play(FadeOut(part_a), FadeOut(calc_a))

        # 4. Part B: Displacement (Integral)
        part_b = Text("B) Displacement (0 ≤ t ≤ 3)", font_size=24, color=YELLOW)
        part_b.next_to(v_text, DOWN, buff=0.5)
        self.play(Write(part_b))

        # Create Axes for graph
        axes = Axes(
            x_range=[0, 4, 1],
            y_range=[-2, 10, 2],
            axis_config={"color": BLUE},
            x_length=5,
            y_length=4
        ).to_edge(LEFT, buff=0.5).shift(DOWN*0.5)
        
        x_label = Text("t", font_size=18).next_to(axes.x_axis, RIGHT)
        y_label = Text("v(t)", font_size=18).next_to(axes.y_axis, UP)
        labels = VGroup(x_label, y_label)
        
        func = axes.plot(lambda t: 3*t**2 - 6*t + 2, color=YELLOW, x_range=[0, 3.2])
        area = axes.get_area(func, x_range=[0, 3], color=GREEN, opacity=0.3)

        calc_b = VGroup(
            Text("s = ∫₀³ (3t² - 6t + 2) dt", font_size=22),
            Text("= [t³ - 3t² + 2t]₀³", font_size=22),
            Text("= (27 - 27 + 6) - 0", font_size=22),
            Text("= 6 m", font_size=28, color=GREEN)
        ).arrange(DOWN, aligned_edge=LEFT).to_edge(RIGHT, buff=0.5).shift(DOWN*0.5)

        self.play(Create(axes), FadeIn(labels))
        self.play(Create(func))
        self.wait(1)
        
        self.play(Write(calc_b[0]))
        self.play(FadeIn(area))
        self.wait(1)
        
        for i in range(1, len(calc_b)):
            self.play(Write(calc_b[i]))
            self.wait(1)

        self.wait(3)
