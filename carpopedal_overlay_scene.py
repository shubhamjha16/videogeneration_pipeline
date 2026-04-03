from manim import *
import numpy as np

class CarpopedalMechanism(Scene):
    def construct(self):
        # 1. Background Image
        img_path = "/Users/apple/.gemini/antigravity/brain/14b870ab-bc4a-490d-ba67-0467257e2e4a/carpopedal_spasm_mechanism_diagram_1775120994594.png"
        bg = ImageMobject(img_path).scale_to_fit_height(config.frame_height - 0.5)
        self.add(bg)

        # 2. Title Overlay
        title = Text("Ask Tony: MCQ Explanation", color="#00BFFF").to_edge(UP).scale(0.6)
        title_bg = BackgroundRectangle(title, color=BLACK, fill_opacity=0.8)
        self.play(FadeIn(title_bg), Write(title))
        self.wait(1)

        # 3. Label: Alkalosis
        alkalosis_pos = np.array([2.5, -0.8, 0])
        alk_arrow = Arrow(start=alkalosis_pos + np.array([1, 0.5, 0]), end=alkalosis_pos, color=BLUE)
        alk_text = Text("pH RISING (ALKALOSIS)", color=BLUE).next_to(alk_arrow, UP).scale(0.4)
        
        self.play(Create(alk_arrow))
        self.play(FadeIn(alk_text))
        self.wait(2)

        # 4. Label: Calcium Binding
        bind_pos = np.array([-1.5, -2.5, 0])
        bind_arrow = Arrow(start=bind_pos + np.array([-1, 1, 0]), end=bind_pos, color=YELLOW)
        bind_text = Text("CALCIUM BINDING TO PROTEIN", color=YELLOW).next_to(bind_arrow, LEFT).scale(0.4)

        self.play(Create(bind_arrow))
        self.play(FadeIn(bind_text))
        self.wait(3)

        # 5. Summary Text
        summary = Text("CORRECT OPTION: C", color=GREEN).to_edge(DOWN).scale(0.7)
        sum_bg = BackgroundRectangle(summary, color=BLACK, fill_opacity=0.9)
        self.play(FadeIn(sum_bg), FadeIn(summary))
        self.wait(3)
