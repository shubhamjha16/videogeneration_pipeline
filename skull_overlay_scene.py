from manim import *
import os

class SkullAnatomyOverlay(Scene):
    def construct(self):
        # 1. Load the Generated Image
        img_path = "/Users/apple/.gemini/antigravity/brain/14b870ab-bc4a-490d-ba67-0467257e2e4a/human_skull_diagram_base_1775118723665.png"
        bg_image = ImageMobject(img_path).scale_to_fit_height(config.frame_height - 1)
        self.add(bg_image)
        
        # 2. Title
        title = Text("Cranial Anatomy: The Human Skull", color="#00BFFF").to_edge(UP).scale(0.7)
        bg_rect = BackgroundRectangle(title, color=BLACK, fill_opacity=0.7)
        self.play(FadeIn(bg_rect), Write(title))
        self.wait(1)

        # 3. Label: Frontal Bone
        fb_pos = np.array([-1.0, 2.0, 0])
        fb_arrow = Arrow(start=fb_pos + np.array([-1.5, 0.5, 0]), end=fb_pos, color=RED, stroke_width=4)
        fb_label = Text("FRONTAL BONE", color=RED).next_to(fb_arrow, LEFT).scale(0.5)
        
        self.play(Create(fb_arrow))
        self.play(FadeIn(fb_label))
        self.wait(2)
        
        # 4. Label: Mandible
        mand_pos = np.array([-1.2, -1.8, 0])
        mand_arrow = Arrow(start=mand_pos + np.array([-1.5, -0.5, 0]), end=mand_pos, color=GREEN, stroke_width=4)
        mand_label = Text("MANDIBLE", color=GREEN).next_to(mand_arrow, LEFT).scale(0.5)

        self.play(Create(mand_arrow))
        self.play(FadeIn(mand_label))
        self.wait(2)

        # 5. Label: Zygomatic Arch
        zygo_pos = np.array([0.5, -0.2, 0])
        zygo_arrow = Arrow(start=zygo_pos + np.array([1.5, 0.5, 0]), end=zygo_pos, color=YELLOW, stroke_width=4)
        zygo_label = Text("ZYGOMATIC ARCH", color=YELLOW).next_to(zygo_arrow, RIGHT).scale(0.5)

        self.play(Create(zygo_arrow))
        self.play(FadeIn(zygo_label))
        self.wait(3)

        # 6. Conclusion
        self.play(FadeOut(fb_arrow), FadeOut(fb_label),
                  FadeOut(mand_arrow), FadeOut(mand_label),
                  FadeOut(zygo_arrow), FadeOut(zygo_label))
        self.play(FadeIn(Text("Anatomy Session Complete", color=YELLOW).scale(0.8)))
        self.wait(2)
