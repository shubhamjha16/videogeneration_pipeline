from manim import *

class JEEPhysicsVTGraph(Scene):
    def construct(self):
        # 1. Setup Axes
        axes = Axes(
            x_range=[0, 10, 2],
            y_range=[0, 10, 2],
            axis_config={"color": BLUE},
            x_axis_config={"label_direction": DOWN},
            y_axis_config={"label_direction": LEFT},
        ).scale(0.8).to_edge(LEFT, buff=0.5)

        labels = axes.get_axis_labels(x_label=Text("Time (t)", font_size=20), y_label=Text("Velocity (v)", font_size=20))

        # 2. Draw Uniform Acceleration Graph (y = 0.75x + 2)
        graph = axes.plot(lambda x: 0.75*x + 2, x_range=[0, 8], color=YELLOW)
        
        # 3. Label Slope
        slope_label = Text("Slope = Acceleration (a)", font_size=24, color=YELLOW).next_to(graph, UP, buff=0.2)

        # 4. Draw Area (Trapezoid) using get_area on the graph object
        area = axes.get_area(graph, x_range=[0, 8], color=GREEN, opacity=0.3)
        area_label = Text("Area = Displacement (s)", font_size=24, color=GREEN).move_to(area.get_center())

        # 5. Equation
        eq = Text("s = ut + 1/2 at^2", font_size=32).to_corner(UR, buff=1)

        # Animations
        self.play(Create(axes), Write(labels))
        self.wait(1)
        self.play(Create(graph), Write(slope_label))
        self.wait(3)
        self.play(FadeIn(area), Write(area_label))
        self.wait(5)
        self.play(Write(eq))
        self.wait(5)
