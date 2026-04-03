from manim import *

class InternalIliacArteryMasterclass(Scene):
    def construct(self):
        # 1. Title & Aesthetics
        self.camera.background_color = "#121212"
        title = Tex("Internal Iliac Artery", color=BLUE_D).scale(1.5).to_edge(UP)
        subtitle = Tex("The Vascular Hub of the Pelvis", font_size=32).next_to(title, DOWN)
        
        self.play(Write(title), FadeIn(subtitle))
        self.wait(2)
        self.play(FadeOut(title), FadeOut(subtitle))

        # 2. Key Concept: Origins
        origin_text = Tex(r"Origin: \textbf{Common Iliac Artery}", font_size=40).shift(UP*2)
        divisions = VGroup(
            MathTex(r"\text{Anterior Division}", color=ORANGE),
            MathTex(r"\text{Posterior Division}", color=ORANGE)
        ).arrange(RIGHT, buff=2).next_to(origin_text, DOWN, buff=1)

        self.play(Write(origin_text))
        self.play(Create(divisions))
        self.wait(3)
        self.play(FadeOut(origin_text), FadeOut(divisions))

        # 3. Option Analysis (The Core Question)
        question = Tex(r"Which of the following is \textbf{NOT} a branch of the internal iliac artery?", font_size=36).to_edge(UP)
        options = VGroup(
            MathTex(r"\text{A. Ovarian Artery}", color=WHITE),
            MathTex(r"\text{B. Superior Vesical Artery}", color=WHITE),
            MathTex(r"\text{C. Uterine Artery}", color=WHITE),
            MathTex(r"\text{D. Internal Pudendal Artery}", color=WHITE)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.5).scale(0.8)

        self.play(Write(question))
        self.play(FadeIn(options, shift=RIGHT))
        self.wait(5)

        # 4. Detailed Analysis & Correct Answer
        rect = SurroundingRectangle(options[0], color=RED)
        explanation = Tex(r"Correct: \textbf{Ovarian Artery}", color=RED).shift(DOWN*2)
        secondary_note = Tex(r"Origin: Directly from Abdominal Aorta", font_size=28, color=YELLOW).next_to(explanation, DOWN)

        self.play(Create(rect), Write(explanation))
        self.play(FadeIn(secondary_note))
        self.wait(4)

        # 5. Final Key Points Summary
        self.play(FadeOut(question), FadeOut(options), FadeOut(rect), FadeOut(explanation), FadeOut(secondary_note))
        summary_title = Tex("Key Branches", color=BLUE).to_edge(UP)
        branches = VGroup(
            MathTex(r"\bullet \text{ Superior Vesical Artery}"),
            MathTex(r"\bullet \text{ Obturator Artery}"),
            MathTex(r"\bullet \text{ Uterine Artery}"),
            MathTex(r"\bullet \text{ Internal Pudendal Artery}")
        ).arrange(DOWN, aligned_edge=LEFT).shift(LEFT*2)

        self.play(Write(summary_title))
        self.play(Write(branches))
        self.wait(5)
