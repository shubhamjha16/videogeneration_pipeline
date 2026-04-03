from manim import *
import os

class InternalIliacArteryMasterclass(Scene):
    def construct(self):
        # PART 1: CONCEPT (0-15s)
        img_path = "/Users/apple/.gemini/antigravity/brain/14b870ab-bc4a-490d-ba67-0467257e2e4a/iliac_artery_branches_diagram_1775190481600.png"
        bg_image = ImageMobject(img_path).scale(1.2)
        
        title = Text("Internal Iliac Artery", color=BLUE).scale(1.2).to_edge(UP).set_stroke(BLACK, width=2, background=True)
        
        self.play(FadeIn(bg_image))
        self.play(Write(title))
        self.wait(10)

        # PART 2: MECHANISM (15-35s)
        # Highlight the Ovarian Artery (The Trap)
        ovarian_circle = Circle(radius=0.8, color=YELLOW).shift(UP*1.5 + LEFT*2.5)
        warning = Text("NOT from Internal Iliac!", color=YELLOW, font_size=32).to_edge(DOWN).set_stroke(BLACK, width=2, background=True)
        arrow = Arrow(start=warning.get_top(), end=ovarian_circle.get_bottom(), color=YELLOW)

        self.play(Create(ovarian_circle))
        self.play(Write(warning), GrowArrow(arrow))
        self.wait(15)
        self.play(FadeOut(ovarian_circle), FadeOut(warning), FadeOut(arrow))

        # PART 3: MCQ (35-50s)
        question_bg = Rectangle(width=10, height=4, color=BLACK, fill_opacity=0.8).to_edge(DOWN)
        question = Text("Which is NOT a branch of the Internal Iliac?", font_size=28).move_to(question_bg.get_top()).shift(DOWN*0.5)
        
        options = VGroup(
            Text("A. Ovarian Artery", color=YELLOW, font_size=24),
            Text("B. Superior Vesical", font_size=24),
            Text("C. Uterine Artery", font_size=24),
            Text("D. Internal Pudendal", font_size=24)
        ).arrange(DOWN, aligned_edge=LEFT).next_to(question, DOWN, buff=0.3).shift(RIGHT*1)
        
        ans_box = SurroundingRectangle(options[0], color=GREEN)

        self.play(FadeIn(question_bg))
        self.play(Write(question))
        self.play(Write(options))
        self.wait(5)
        self.play(Create(ans_box))
        self.wait(10)
