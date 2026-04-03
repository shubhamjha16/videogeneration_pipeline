from manim import *
import numpy as np

class CarpopedalFullMastery(Scene):
    def construct(self):
        # --- PART 1: THE CONCEPT ---
        title = Text("Understanding Carpopedal Spasm", color="#00BFFF").to_edge(UP).scale(0.8)
        self.play(Write(title))
        self.wait(1)
        
        concept_text = VGroup(
            Text("• Respiratory Alkalosis", color=WHITE),
            Text("• Caused by Hyperventilation", color=WHITE),
            Text("• Increased blood pH (>7.45)", color=YELLOW)
        ).arrange(DOWN, aligned_edge=LEFT).scale(0.6).next_to(title, DOWN, buff=1)
        
        self.play(FadeIn(concept_text))
        self.wait(4)
        self.play(FadeOut(concept_text), FadeOut(title))

        # --- PART 2: THE MECHANISM (VISUAL) ---
        img_path = "/Users/apple/.gemini/antigravity/brain/14b870ab-bc4a-490d-ba67-0467257e2e4a/carpopedal_spasm_mechanism_diagram_1775120994594.png"
        mechanism_img = ImageMobject(img_path).scale_to_fit_height(config.frame_height - 1)
        self.play(FadeIn(mechanism_img))
        self.wait(2)

        # Mechanism Overlays
        alk_label = Text("pH RISING (ALKALOSIS)", color=BLUE).to_edge(UP).scale(0.6)
        alk_rect = BackgroundRectangle(alk_label, color=BLACK, fill_opacity=0.7)
        self.play(FadeIn(alk_rect), Write(alk_label))
        self.wait(3)

        bind_label = Text("PROTEIN BINDS CA++", color=RED).to_edge(DOWN).scale(0.6)
        bind_rect = BackgroundRectangle(bind_label, color=BLACK, fill_opacity=0.7)
        self.play(FadeIn(bind_rect), Write(bind_label))
        self.wait(4)

        self.play(FadeOut(alk_label), FadeOut(alk_rect), FadeOut(bind_label), FadeOut(bind_rect), FadeOut(mechanism_img))

        # --- PART 3: THE MCQ ---
        q_text = Text("MCQ Analysis", color=YELLOW).to_edge(UP).scale(0.7)
        question = Text("Carpopedal spasm in hyperventilation occurs because?", color=WHITE).scale(0.5).next_to(q_text, DOWN, buff=0.5)
        
        options = VGroup(
            Text("A. Muscle calcium uptake", color=WHITE),
            Text("B. Bone calcium uptake", color=WHITE),
            Text("C. Increased calcium binding to plasma protein", color=GREEN),
            Text("D. Urinary calcium excretion", color=WHITE)
        ).arrange(DOWN, aligned_edge=LEFT).scale(0.5).next_to(question, DOWN, buff=0.8)

        self.play(Write(q_text))
        self.play(FadeIn(question))
        self.wait(2)
        self.play(FadeIn(options))
        self.wait(3)
        
        # Highlight Correct
        rect = SurroundingRectangle(options[2], color=GREEN, buff=0.1)
        self.play(Create(rect))
        self.wait(4)

        # Outro
        self.play(FadeOut(VGroup(q_text, question, options, rect)))
        self.play(FadeIn(Text("Ask Tony: Medical Mastery", color=BLUE).scale(0.8)))
        self.wait(2)
