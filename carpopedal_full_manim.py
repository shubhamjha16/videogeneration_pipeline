from manim import *
import numpy as np

class CarpopedalSpasmLesson(Scene):
    def construct(self):
        # 1. Question Slide
        question_text = Text("Q1) Carpopedal spasm in hyperventilation occurs because -", color=WHITE).scale(0.6)
        options = VGroup(
            Text("A. Increased calcium uptake by muscles", color=WHITE),
            Text("B. Increased calcium uptake by bones", color=WHITE),
            Text("C. Increased calcium binding to plasma protein", color=YELLOW),
            Text("D. Increased urinary excretion of calcium", color=WHITE)
        ).arrange(DOWN, aligned_edge=LEFT).scale(0.5).next_to(question_text, DOWN, buff=0.5)
        
        self.play(Write(question_text))
        self.play(FadeIn(options))
        self.wait(2)
        self.play(FadeOut(question_text), FadeOut(options))

        # 2. Conceptual Image Intro
        img_path = "/Users/apple/.gemini/antigravity/brain/14b870ab-bc4a-490d-ba67-0467257e2e4a/carpopedal_spasm_mechanism_diagram_1775120994594.png"
        mechanism_img = ImageMobject(img_path).scale_to_fit_height(config.frame_height - 1)
        self.play(FadeIn(mechanism_img))
        self.wait(1)

        # 3. Mechanism Overlay: pH Rising
        ph_label = Text("pH RISING (ALKALOSIS)", color=BLUE).to_edge(UP).scale(0.6)
        ph_rect = BackgroundRectangle(ph_label, color=BLACK, fill_opacity=0.7)
        ph_arrow = Arrow(start=[2.5, 1, 0], end=[2.5, -0.5, 0], color=BLUE)
        
        self.play(FadeIn(ph_rect), Write(ph_label))
        self.play(Create(ph_arrow))
        self.wait(2)

        # 4. Mechanism Overlay: Calcium Binding
        ca_label = Text("CA++ BINDS TO ALBUMIN", color=RED).to_edge(DOWN).scale(0.6)
        ca_rect = BackgroundRectangle(ca_label, color=BLACK, fill_opacity=0.7)
        ca_arrow = Arrow(start=[-1.0, -1.0, 0], end=[-1.5, -2.5, 0], color=RED)

        self.play(FadeIn(ca_rect), Write(ca_label))
        self.play(Create(ca_arrow))
        self.wait(3)

        # 5. Conclusion
        self.play(FadeOut(ph_label), FadeOut(ph_rect), FadeOut(ph_arrow),
                  FadeOut(ca_label), FadeOut(ca_rect), FadeOut(ca_arrow))
        
        final_answer = Text("CORRECT OPTION: C", color=YELLOW).scale(0.8)
        self.play(GrowFromCenter(final_answer))
        self.wait(3)
