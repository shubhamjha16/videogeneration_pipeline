print(f"   🚀 TEMPLATE_RENDERER LOADED FROM: {__file__}")

import numpy as np
from manim import *
import os

# ── LaTeX Template ─────────────────────────────────────────────────────────────
my_template = TexTemplate()
my_template.add_to_preamble(r"\usepackage{amsmath}")
my_template.add_to_preamble(r"\usepackage{amssymb}")

# ── 3Blue1Brown High-Fidelity Design System ──────────────────────────────────
class DesignTokens:
    BLUE   = "#58ADFF"
    GREEN  = "#77DD77"
    YELLOW = "#FFFF66"
    RED    = "#FF6666"
    PURPLE = "#C57AFF"
    WHITE  = "#FFFFFF"
    GRAY   = "#888888"
    BLACK  = "#000000"
    MAX_WIDTH = 12.0
    TITLE_SIZE = 1.4
    BODY_SIZE = 0.8
    SUBTITLE_SIZE = 0.7

config.background_color = DesignTokens.BLACK
config.pixel_height = 1080
config.pixel_width  = 1920

class EaseToLearnScene(Scene):

    def _clear(self):
        """Fade out all mobjects safely."""
        fos = [FadeOut(m) for m in self.mobjects]
        if fos:
            self.play(*fos)

    def _clear_keep_image(self):
        """Fade out all mobjects except background ImageMobject."""
        fos = [FadeOut(m) for m in self.mobjects if not isinstance(m, ImageMobject)]
        if fos:
            self.play(*fos)

    def construct(self):
        # Industrial 3b1b Canvas: Absolute Black
        # DesignTokens are available as a global class in this script.
        self.camera.background_color = DesignTokens.BLACK

        # Scene 0: formula_step_list (Long Derivation: 10 steps)
        self._clear()
        heading_0 = Tex(r"\text{The Grand 10-Step Calculus Chain}", tex_template=my_template)
        heading_0.scale(0.9).set_color(DesignTokens.YELLOW).to_edge(UP, buff=0.5)
        self.play(Write(heading_0), run_time=1.0)
        formula_0_0 = MathTex(r"f(x) = x^{10}", tex_template=my_template).scale(0.55).move_to(np.array([0, 1.2, 0]))
        if formula_0_0.width > DesignTokens.MAX_WIDTH: formula_0_0.set_width(DesignTokens.MAX_WIDTH)
        self.play(Write(formula_0_0), run_time=1.4)
        arrow_0_0 = MathTex(r"\downarrow", tex_template=my_template).scale(0.385).set_color(DesignTokens.GRAY)
        arrow_0_0.next_to(formula_0_0, DOWN, buff=0.09)
        self.play(FadeIn(arrow_0_0), run_time=0.3)
        formula_0_1 = MathTex(r"f'(x) = 10x^9", tex_template=my_template).scale(0.55).move_to(np.array([0, 0.6, 0]))
        if formula_0_1.width > DesignTokens.MAX_WIDTH: formula_0_1.set_width(DesignTokens.MAX_WIDTH)
        self.play(Write(formula_0_1), run_time=1.4)
        arrow_0_1 = MathTex(r"\downarrow", tex_template=my_template).scale(0.385).set_color(DesignTokens.GRAY)
        arrow_0_1.next_to(formula_0_1, DOWN, buff=0.09)
        self.play(FadeIn(arrow_0_1), run_time=0.3)
        formula_0_2 = MathTex(r"f''(x) = 90x^8", tex_template=my_template).scale(0.55).move_to(np.array([0, 0.0, 0]))
        if formula_0_2.width > DesignTokens.MAX_WIDTH: formula_0_2.set_width(DesignTokens.MAX_WIDTH)
        self.play(Write(formula_0_2), run_time=1.4)
        arrow_0_2 = MathTex(r"\downarrow", tex_template=my_template).scale(0.385).set_color(DesignTokens.GRAY)
        arrow_0_2.next_to(formula_0_2, DOWN, buff=0.09)
        self.play(FadeIn(arrow_0_2), run_time=0.3)
        formula_0_3 = MathTex(r"f^{(3)}(x) = 720x^7", tex_template=my_template).scale(0.55).move_to(np.array([0, -0.5999999999999999, 0]))
        if formula_0_3.width > DesignTokens.MAX_WIDTH: formula_0_3.set_width(DesignTokens.MAX_WIDTH)
        self.play(Write(formula_0_3), run_time=1.4)
        arrow_0_3 = MathTex(r"\downarrow", tex_template=my_template).scale(0.385).set_color(DesignTokens.GRAY)
        arrow_0_3.next_to(formula_0_3, DOWN, buff=0.09)
        self.play(FadeIn(arrow_0_3), run_time=0.3)
        formula_0_4 = MathTex(r"f^{(4)}(x) = 5040x^6", tex_template=my_template).scale(0.55).move_to(np.array([0, -1.2, 0]))
        if formula_0_4.width > DesignTokens.MAX_WIDTH: formula_0_4.set_width(DesignTokens.MAX_WIDTH)
        self.play(Write(formula_0_4), run_time=1.4)
        arrow_0_4 = MathTex(r"\downarrow", tex_template=my_template).scale(0.385).set_color(DesignTokens.GRAY)
        arrow_0_4.next_to(formula_0_4, DOWN, buff=0.09)
        self.play(FadeIn(arrow_0_4), run_time=0.3)
        formula_0_5 = MathTex(r"f^{(5)}(x) = 30240x^5", tex_template=my_template).scale(0.55).move_to(np.array([0, -1.8, 0]))
        if formula_0_5.width > DesignTokens.MAX_WIDTH: formula_0_5.set_width(DesignTokens.MAX_WIDTH)
        self.play(Write(formula_0_5), run_time=1.4)
        arrow_0_5 = MathTex(r"\downarrow", tex_template=my_template).scale(0.385).set_color(DesignTokens.GRAY)
        arrow_0_5.next_to(formula_0_5, DOWN, buff=0.09)
        self.play(FadeIn(arrow_0_5), run_time=0.3)
        formula_0_6 = MathTex(r"f^{(6)}(x) = 151200x^4", tex_template=my_template).scale(0.55).move_to(np.array([0, -2.3999999999999995, 0]))
        if formula_0_6.width > DesignTokens.MAX_WIDTH: formula_0_6.set_width(DesignTokens.MAX_WIDTH)
        self.play(Write(formula_0_6), run_time=1.4)
        arrow_0_6 = MathTex(r"\downarrow", tex_template=my_template).scale(0.385).set_color(DesignTokens.GRAY)
        arrow_0_6.next_to(formula_0_6, DOWN, buff=0.09)
        self.play(FadeIn(arrow_0_6), run_time=0.3)
        formula_0_7 = MathTex(r"f^{(7)}(x) = 604800x^3", tex_template=my_template).scale(0.55).move_to(np.array([0, -3.0, 0]))
        if formula_0_7.width > DesignTokens.MAX_WIDTH: formula_0_7.set_width(DesignTokens.MAX_WIDTH)
        self.play(Write(formula_0_7), run_time=1.4)
        arrow_0_7 = MathTex(r"\downarrow", tex_template=my_template).scale(0.385).set_color(DesignTokens.GRAY)
        arrow_0_7.next_to(formula_0_7, DOWN, buff=0.09)
        self.play(FadeIn(arrow_0_7), run_time=0.3)
        formula_0_8 = MathTex(r"f^{(8)}(x) = 1814400x^2", tex_template=my_template).scale(0.55).move_to(np.array([0, -3.5999999999999996, 0]))
        if formula_0_8.width > DesignTokens.MAX_WIDTH: formula_0_8.set_width(DesignTokens.MAX_WIDTH)
        self.play(Write(formula_0_8), run_time=1.4)
        arrow_0_8 = MathTex(r"\downarrow", tex_template=my_template).scale(0.385).set_color(DesignTokens.GRAY)
        arrow_0_8.next_to(formula_0_8, DOWN, buff=0.09)
        self.play(FadeIn(arrow_0_8), run_time=0.3)
        formula_0_9 = MathTex(r"f^{(9)}(x) = 3628800x", tex_template=my_template).scale(0.55).move_to(np.array([0, -4.199999999999999, 0]))
        if formula_0_9.width > DesignTokens.MAX_WIDTH: formula_0_9.set_width(DesignTokens.MAX_WIDTH)
        self.play(Write(formula_0_9), run_time=1.4)
        self.wait(1.0)
        self._clear()
        self.wait(1)
