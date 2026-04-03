from manim import *
import os

class HeartAnatomyOverlay(Scene):
    def construct(self):
        # 1. Load the Generated Image
        img_path = "/Users/apple/.gemini/antigravity/brain/14b870ab-bc4a-490d-ba67-0467257e2e4a/medical_heart_diagram_base_1775118643747.png"
        bg_image = ImageMobject(img_path).scale_to_fit_height(config.frame_height - 1)
        self.add(bg_image)
        
        # 2. Title
        title = Text("Cardiac Anatomy: The Human Heart", color="#00BFFF").to_edge(UP).scale(0.7)
        bg_rect = BackgroundRectangle(title, color=BLACK, fill_opacity=0.7)
        self.play(FadeIn(bg_rect), Write(title))
        self.wait(1)

        # 3. Label: Aorta
        aorta_pos = [0.2, 1.8, 0] # Rough aortic arch
        aorta_arrow = Arrow(start=aorta_pos + [2, 0.5, 0], end=aorta_pos, color=RED, stroke_width=4)
        aorta_label = Text("AORTA", color=RED).next_to(aorta_arrow, RIGHT).scale(0.5)
        
        self.play(Create(aorta_arrow))
        self.play(FadeIn(aorta_label))
        self.wait(2)
        
        # 4. Label: Left Ventricle
        lv_pos = [1.0, -1.5, 0]
        lv_arrow = Arrow(start=lv_pos + [2, -0.5, 0], end=lv_pos, color=GREEN, stroke_width=4)
        lv_label = Text("LEFT VENTRICLE", color=GREEN).next_to(lv_arrow, RIGHT).scale(0.5)

        self.play(Create(lv_arrow))
        self.play(FadeIn(lv_label))
        self.wait(2)

        # 5. Label: Right Atrium
        ra_pos = [-1.5, 0.5, 0]
        ra_arrow = Arrow(start=ra_pos + [-1.5, 0.5, 0], end=ra_pos, color=BLUE, stroke_width=4)
        ra_label = Text("RIGHT ATRIUM", color=BLUE).next_to(ra_arrow, LEFT).scale(0.5)

        self.play(Create(ra_arrow))
        self.play(FadeIn(ra_label))
        self.wait(3)

        # 6. Conclusion
        self.play(FadeOut(aorta_arrow), FadeOut(aorta_label),
                  FadeOut(lv_arrow), FadeOut(lv_label),
                  FadeOut(ra_arrow), FadeOut(ra_label))
        self.play(FadeIn(Text("Masterclass Complete", color=YELLOW).scale(0.8)))
        self.wait(2)
