from manim import *
import os

class CalciumVisualMasterclass(Scene):
    def construct(self):
        # 1. THE CONCEPT + PHOTO (DETAILED)
        concept_title = Text("Concept: Calcium Gluconate", color=BLUE_B).scale(0.8).to_edge(UP)
        self.play(Write(concept_title))

        # Load and Display the Clinical Diagram (The "Photo")
        try:
            photo = ImageMobject("CalciumGluconate_diagram.png").scale(1.2).to_edge(LEFT, buff=0.5)
            photo_label = Text("Clinical Model", font_size=16, color=GREY_A).next_to(photo, DOWN)
            self.play(FadeIn(photo, shift=UP), FadeIn(photo_label))
        except:
            photo = Square().scale(1.5).to_edge(LEFT) # Fallback

        concept_desc = Text(
            "Stabilizes cardiac membranes\n"
            "during electrolyte emergencies.",
            font_size=24, line_spacing=1.5
        ).next_to(photo, RIGHT, buff=1).shift(UP*0.5)
        
        toxic_detail = Text(
            "Reverses toxic effects of\n"
            "High Potassium (K+) and\n"
            "Low Calcium (Ca2+).",
            color=BLUE_A, font_size=20
        ).next_to(concept_desc, DOWN, buff=0.5)
        
        self.play(Write(concept_desc))
        self.play(FadeIn(toxic_detail))
        self.wait(5)
        
        # Cleanup for Analysis
        self.play(FadeOut(concept_desc), FadeOut(toxic_detail))

        # 2. ANALYSIS OF OPTIONS (SIDE-BY-SIDE WITH PHOTO)
        analysis_title = Text("Clinical Indications Analysis:", color=YELLOW, font_size=28).to_edge(RIGHT, buff=0.5).shift(UP*2)
        self.play(FadeIn(analysis_title))

        opt_a = MathTex(r"\text{A. Hypocalcemia (Indications)} \rightarrow Ca^{2+} \downarrow").scale(0.6)
        opt_c = MathTex(r"\text{C. Hyperkalemia (Cardioprotection)} \rightarrow K^+ \uparrow").scale(0.6)
        opt_d = Text("D. CCB Toxicity (Antagonism)", font_size=18)
        
        indications = VGroup(opt_a, opt_c, opt_d).arrange(DOWN, aligned_edge=LEFT).next_to(analysis_title, DOWN, buff=0.5)

        for item in indications:
            self.play(FadeIn(item, shift=RIGHT))
            self.wait(2)

        # 3. THE EXCEPTION (B - HYPOKALEMIA)
        self.play(FadeOut(indications), FadeOut(analysis_title))
        
        b_header = Text("B. Hypokalemia (Low K+)", color=RED, font_size=28).to_edge(RIGHT, buff=1).shift(UP*1)
        b_reason = Text(
            "NOT an indication. Needs K+,\n"
            "not Calcium stabilization.",
            color=RED_A, font_size=20
        ).next_to(b_header, DOWN, buff=0.5)
        
        cross = Cross(b_header)
        
        self.play(Write(b_header))
        self.play(Create(cross))
        self.play(FadeIn(b_reason, shift=UP))
        self.wait(4)

        # 4. FINAL VERDICT
        self.play(FadeOut(photo), FadeOut(photo_label), FadeOut(b_header), FadeOut(b_reason), FadeOut(cross))
        verdict = Text("Correct Answer: B", color=GREEN).scale(1.5).move_to(ORIGIN)
        
        # References
        refs = Text("References: Tintinalli's & Rosen's Emergency Med (9th Ed)", 
                  font_size=16, color=GREY_B).to_edge(DOWN, buff=0.5)
        
        self.play(FadeIn(verdict))
        self.play(FadeIn(refs))
        self.wait(5)
        self.play(FadeOut(VGroup(concept_title, verdict, refs)))
