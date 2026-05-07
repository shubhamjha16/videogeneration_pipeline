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

    def _add_formula_with_overflow(self, formula, arrow=None, threshold=6.0, buff=0.4):
        """
        Industrial Overflow Handler:
        Vertical-stacks math formulas. If threshold exceeded, slides oldest out.
        """
        if not hasattr(self, "_stack_group"):
            self._stack_group = VGroup()
            self._stack_data = [] # List of (formula, arrow_above_it)
            self._target_y = 2.5 # Starting top position

        # 1. Position the new elements
        if not self._stack_data:
            # First item
            formula.move_to(np.array([0, self._target_y, 0]))
        else:
            # Position relative to last formula
            last_f, _ = self._stack_data[-1]
            if arrow:
                arrow.next_to(last_f, DOWN, buff=buff*0.5)
                formula.next_to(arrow, DOWN, buff=buff*0.5)
            else:
                formula.next_to(last_f, DOWN, buff=buff)

        # 2. Check for overflow before playing
        # Threshold check: Is the bottom of the new formula too low?
        if formula.get_bottom()[1] < -3.0: # -3.0 is ~80% of 4.0 (half-height)
            if self._stack_data:
                old_f, old_a = self._stack_data.pop(0)
                
                # Calculate shift distance: enough to put the next formula where the old one was
                # Or just shift by the height of the removed block
                removed_height = old_f.height + buff
                if old_a: removed_height += old_a.height # Though usually first has no arrow above it
                # Actually, the arrow BELOW it is what matters. 
                # Let's fix the data structure: (formula, arrow_below)
                
        # Better logic:
        # Each entry is (formula, arrow_below_it)
        
        # --- REVISED SLIDE LOGIC ---
        if formula.get_bottom()[1] < -3.0 and len(self._stack_data) > 1:
            old_f, old_a_below = self._stack_data.pop(0)
            
            # Distance to shift: height of the first formula + the arrow below it + buffer
            shift_dist = old_f.get_top()[1] - self._stack_data[0][0].get_top()[1]
            shift_vec = UP * shift_dist
            
            self.play(
                FadeOut(old_f, shift=UP*0.5),
                *([FadeOut(old_a_below, shift=UP*0.5)] if old_a_below else []),
                self._stack_group.animate.shift(shift_vec),
                formula.animate.shift(shift_vec), # Move the currently-being-positioned formula too
                *([arrow.animate.shift(shift_vec)] if arrow else []),
                run_time=0.6
            )
            self._stack_group.remove(old_f)
            if old_a_below: self._stack_group.remove(old_a_below)

        # 3. Render
        if arrow:
            self.play(FadeIn(arrow), run_time=0.2)
            self._stack_group.add(arrow)
        
        self.play(Write(formula), run_time=0.4)
        self._stack_group.add(formula)
        
        # Update stack data: we need to know the arrow BELOW the previous formula
        # So we update the PREVIOUS entry's arrow_below when we add an arrow here
        if len(self._stack_data) > 0 and arrow:
            # This arrow is below the previous formula
            prev_f, _ = self._stack_data[-1]
            self._stack_data[-1] = (prev_f, arrow)
            
        self._stack_data.append((formula, None)) # New formula has no arrow below it yet

    def _clear_keep_image(self):
        """Fade out all mobjects except background ImageMobject."""
        fos = [FadeOut(m) for m in self.mobjects if not isinstance(m, ImageMobject)]
        if fos:
            self.play(*fos)

    def construct(self):
        # Industrial 3b1b Canvas: Absolute Black
        # DesignTokens are available as a global class in this script.
        self.camera.background_color = DesignTokens.BLACK

        # Scene 0: formula_step_list (Sliding Overflow)
        self._clear()
        heading_0 = Tex(r"\text{Test: 7step}", tex_template=my_template)
        heading_0.scale(0.9).set_color(DesignTokens.YELLOW).to_edge(UP, buff=0.5)
        self.play(Write(heading_0), run_time=1.0)
        f_0_0 = MathTex(r"Step 1", tex_template=my_template).scale(0.9)
        if f_0_0.width > DesignTokens.MAX_WIDTH: f_0_0.set_width(DesignTokens.MAX_WIDTH)
        self._add_formula_with_overflow(f_0_0)
        f_0_1 = MathTex(r"Step 2", tex_template=my_template).scale(0.9)
        if f_0_1.width > DesignTokens.MAX_WIDTH: f_0_1.set_width(DesignTokens.MAX_WIDTH)
        a_0_1 = MathTex(r"\downarrow", tex_template=my_template).scale(0.7).set_color(DesignTokens.GRAY)
        self._add_formula_with_overflow(f_0_1, arrow=a_0_1)
        f_0_2 = MathTex(r"Step 3", tex_template=my_template).scale(0.9)
        if f_0_2.width > DesignTokens.MAX_WIDTH: f_0_2.set_width(DesignTokens.MAX_WIDTH)
        a_0_2 = MathTex(r"\downarrow", tex_template=my_template).scale(0.7).set_color(DesignTokens.GRAY)
        self._add_formula_with_overflow(f_0_2, arrow=a_0_2)
        f_0_3 = MathTex(r"Step 4", tex_template=my_template).scale(0.9)
        if f_0_3.width > DesignTokens.MAX_WIDTH: f_0_3.set_width(DesignTokens.MAX_WIDTH)
        a_0_3 = MathTex(r"\downarrow", tex_template=my_template).scale(0.7).set_color(DesignTokens.GRAY)
        self._add_formula_with_overflow(f_0_3, arrow=a_0_3)
        f_0_4 = MathTex(r"Step 5", tex_template=my_template).scale(0.9)
        if f_0_4.width > DesignTokens.MAX_WIDTH: f_0_4.set_width(DesignTokens.MAX_WIDTH)
        a_0_4 = MathTex(r"\downarrow", tex_template=my_template).scale(0.7).set_color(DesignTokens.GRAY)
        self._add_formula_with_overflow(f_0_4, arrow=a_0_4)
        f_0_5 = MathTex(r"Step 6", tex_template=my_template).scale(0.9)
        if f_0_5.width > DesignTokens.MAX_WIDTH: f_0_5.set_width(DesignTokens.MAX_WIDTH)
        a_0_5 = MathTex(r"\downarrow", tex_template=my_template).scale(0.7).set_color(DesignTokens.GRAY)
        self._add_formula_with_overflow(f_0_5, arrow=a_0_5)
        f_0_6 = MathTex(r"Step 7", tex_template=my_template).scale(0.9)
        if f_0_6.width > DesignTokens.MAX_WIDTH: f_0_6.set_width(DesignTokens.MAX_WIDTH)
        a_0_6 = MathTex(r"\downarrow", tex_template=my_template).scale(0.7).set_color(DesignTokens.GRAY)
        self._add_formula_with_overflow(f_0_6, arrow=a_0_6)
        self.wait(2.0)
        self._clear()
        self.wait(1)
