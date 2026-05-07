from manim import *
import numpy as np

class DesignTokens:
    BLUE   = "#58ADFF"
    YELLOW = "#FFFF66"
    WHITE  = "#FFFFFF"
    BLACK  = "#000000"

class MathMorphProof(Scene):
    def construct(self):
        # Data mirroring the factory's internal format
        heading = "Ejection Fraction Derivation"
        steps = [
            r"EF = \frac{SV}{EDV}",
            r"EF = \frac{EDV - ESV}{EDV}",
            r"EF = \frac{120 - 50}{120}",
            r"EF = \frac{70}{120}",
            r"EF = 0.583 = 58.3\%"
        ]
        duration = 10.0
        
        # ── Implementation of _scene_formula_derivation ──
        title = Tex(rf"\text{{{heading}}}")
        title.scale(1.2).set_color(DesignTokens.YELLOW).to_edge(UP, buff=0.8)
        self.play(Write(title))
        
        # Initial step
        current_tex = MathTex(steps[0]).scale(1.5).set_color(DesignTokens.WHITE)
        self.play(Write(current_tex))
        self.wait(duration / (len(steps) + 1))
        
        # Morphing loop (TransformMatchingTex)
        for i in range(1, len(steps)):
            next_tex = MathTex(steps[i]).scale(1.5).set_color(DesignTokens.WHITE)
            self.play(
                TransformMatchingTex(current_tex, next_tex, key_map={}),
                run_time=1.5
            )
            current_tex = next_tex
            self.wait(duration / (len(steps) + 1))
            
        self.wait(2)

