from manim import *

class IntegrationScene(Scene):
    def construct(self):
        # 1. Title
        title = Text("Calculus: Definite Integral", font_size=36, color=YELLOW)
        title.to_edge(UP)
        self.play(Write(title))
        self.wait(1)

        # 2. Create Axes (smaller and shifted)
        axes = Axes(
            x_range=[0, 4, 1],
            y_range=[0, 8, 2],
            axis_config={"color": BLUE},
            x_length=5,
            y_length=4
        ).to_edge(LEFT, buff=0.5).shift(DOWN*0.5)
        
        x_label = Text("x", font_size=20).next_to(axes.x_axis, RIGHT)
        y_label = Text("f(x)", font_size=20).next_to(axes.y_axis, UP)
        labels = VGroup(x_label, y_label)

        # 3. Define the function f(x) = 2x
        func = axes.plot(lambda x: 2 * x, color=YELLOW, x_range=[0, 3.5])
        func_label = Text("f(x) = 2x", font_size=18).next_to(axes.c2p(2, 4), UP + LEFT)
        area = axes.get_area(func, x_range=[0, 3], color=GREEN, opacity=0.3)

        # 4. Step-by-Step Derivation (Right Side)
        steps = VGroup(
            Text("Find:  ∫₀³ 2x dx", font_size=28),
            Text("= 2 * [x²/2]₀³", font_size=28),
            Text("= [x²]₀³", font_size=28),
            Text("= 3² - 0²", font_size=28),
            Text("= 9", font_size=32, color=YELLOW)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.4).to_edge(RIGHT, buff=1)

        # 5. Animation Sequence
        self.play(Create(axes), Write(labels))
        self.play(Create(func), Write(func_label))
        self.wait(1)
        
        # Animate steps along with area
        self.play(Write(steps[0]))
        self.play(FadeIn(area))
        self.wait(1)
        
        for i in range(1, len(steps)):
            self.play(Write(steps[i]))
            self.wait(1)

        self.wait(3)
