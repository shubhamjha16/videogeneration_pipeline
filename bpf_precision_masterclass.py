from manim import *
import os

class BronchopleuralFistulaMasterclass(Scene):
    def construct(self):
        # 1. Background & Title
        self.camera.background_color = "#121212"
        bg_image = ImageMobject("bpf_diagram.png").scale(1.3).to_edge(DOWN)
        title = Tex("Bronchopleural Fistula (BPF)", color=BLUE_D).scale(1.2).to_edge(UP)
        
        self.play(FadeIn(bg_image), Write(title))
        self.wait(5) # "communication between bronchial tree and pleural space"

        # 2. Pathophysiology Zoom (The Fistula)
        fistula_dot = Dot(point=[0.2, 0.5, 0], color=YELLOW, radius=0.1) 
        fistula_label = MathTex(r"\text{Fistulous Tract}", color=YELLOW).scale(0.8).next_to(fistula_dot, RIGHT)
        self.play(Indicate(fistula_dot), Write(fistula_label))
        self.wait(5) # "pathophysiology involves necrosis..."
        self.play(FadeOut(fistula_dot), FadeOut(fistula_label))

        # 3. Option Analysis (The Detective Phase)
        options = VGroup(
            MathTex(r"\text{A. Carcinoma bronchus}", color=WHITE),
            MathTex(r"\text{B. Bronchiectasis}", color=WHITE),
            MathTex(r"\text{C. Pulmonary TB}", color=WHITE),
            MathTex(r"\text{D. Bronchitis}", color=WHITE)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.4).scale(0.7).to_corner(UL).shift(DOWN*1.2)

        self.play(FadeIn(options, shift=RIGHT))
        self.wait(4) # "Identify the most common cause..."

        # Analyze A
        arrow_a = Arrow(start=options[0].get_right(), end=[1.5, 1.5, 0], color=ORANGE)
        self.play(options[0].animate.set_color(ORANGE), Create(arrow_a))
        self.wait(4) # "statistically less frequent..."
        self.play(FadeOut(arrow_a))

        # Analyze B
        arrow_b = Arrow(start=options[1].get_right(), end=[0.8, -0.5, 0], color=ORANGE)
        self.play(options[1].animate.set_color(ORANGE), Create(arrow_b))
        self.wait(4) # "rarely results in actual fistula..."
        self.play(FadeOut(arrow_b))

        # Analyze D
        arrow_d = Arrow(start=options[3].get_right(), end=[-0.5, 2.5, 0], color=ORANGE)
        self.play(options[3].animate.set_color(ORANGE), Create(arrow_d))
        self.wait(4) # "superficial inflammation..."
        self.play(FadeOut(arrow_d))

        # THE REVEAL: Analyze C
        self.play(options[2].animate.set_color(YELLOW))
        tb_cavity = Dot(point=[1.2, -1.2, 0], color=YELLOW, radius=0.12)
        arrow_c = Arrow(start=options[2].get_right(), end=tb_cavity.get_center(), color=YELLOW)
        note = Tex(r"Cavitary Necrosis", font_size=24, color=WHITE).next_to(options[2], RIGHT, buff=0.1)
        
        self.play(Create(arrow_c), Write(note), Indicate(tb_cavity))
        self.wait(8) # "most common etiology..."

        # 4. Final Conclusion
        rect = SurroundingRectangle(options[2], color=GREEN)
        conclusion = Tex(r"Correct Answer: \textbf{Option C}", color=GREEN).scale(1.1).to_edge(UP).shift(DOWN*1)
        
        self.play(FadeOut(title), Create(rect), Write(conclusion))
        self.play(options[2].animate.set_color(GREEN))
        self.wait(6)
