"""
Step 4: Template Renderer (Deterministic)
Converts Director scenes into a Manim script using fixed, tested patterns.

Rules:
  - ALL text uses Tex(r"\\text{...}") — LaTeX typography throughout
  - Math formulas use MathTex(r"...") — full LaTeX math rendering
  - Never use Text() — inconsistent font rendering
  - Each visual_type maps to one fixed Manim pattern, no LLM involved
  - Image (from Gemini Imagen) fills background in concept phase
  - Arrows and highlights are the primary teaching tool

Visual types handled:
  concept_image    → image fills screen, title fades in
  image_arrow      → arrow grows from center to image region, label appears
  mcq_layout       → 4 option boxes arranged in grid
  option_arrow     → arrow points to option box, color changes
  cross_out        → red X drawn over option box
  answer_reveal    → green SurroundingRectangle grows, tick appears
  formula_display  → MathTex centered, label below
  step_by_step     → steps appear one by one with Write()
  concept_bullets  → bullets appear with FadeIn, arrow indicates each
  graph_hint       → axes drawn, arrow traces key region
  summary          → points appear with checkmarks
  title_card       → topic title + subtitle fade in on dark background
"""

import os
import re
import textwrap
from llm_factory import LLMFactory


# ── Design System (3Blue1Brown High-Fidelity) ──────────────────────────────────

# ── Design System (3Blue1Brown High-Fidelity) ──────────────────────────────────

class DesignTokens:
    BLUE   = "#58ADFF"
    GREEN  = "#77DD77"
    YELLOW = "#FFFF66"
    RED    = "#FF6666"
    PURPLE = "#C57AFF"
    WHITE  = "#FFFFFF"
    GRAY   = "#888888"
    BLACK  = "#000000"
    
    # 3b1b 16:9 safe bounds
    MAX_WIDTH = 12.0
    TITLE_SIZE = 1.4
    BODY_SIZE = 0.8
    SUBTITLE_SIZE = 0.7

# ── LaTeX helpers ─────────────────────────────────────────────────────────────

def tex(text: str, width: int = 45) -> str:
    """
    Industrial Sentinel: Smart multi-line LaTeX wrapping.
    Prevents screen overflow by splitting long text into balanced 'VGroups'.
    """
    if not text or not text.strip():
        return f'Tex(r"\\text{{-}}", tex_template=my_template)'
    
    # Convert headers to bold
    text = re.sub(r'###\s*(.*)', r'**\1**', text)
    
    # Normalize explicit \textbf{...} to **...** so our state machine handles it safely
    text = re.sub(r'\\textbf\{(.*?)\}', r'**\1**', text)

    # 1. Sanitize for LaTeX (preserving **)
    escaped = (text
        .replace("\\", r"\\")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("$", r"\$")
        .replace("#", r"\#")
        .replace("_", r"\_")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("~", r"\textasciitilde{}")
        .replace("^", r"\textasciicircum{}")
    )
    
    # 2. Wrap text, then apply bold state
    lines = textwrap.wrap(escaped, width=width)
    latex_lines = []
    is_bold = False
    
    for line in lines:
        formatted_line = ""
        if is_bold:
            formatted_line += r'\textbf{'
            
        i = 0
        while i < len(line):
            if line[i:i+2] == '**':
                if not is_bold:
                    formatted_line += r'\textbf{'
                    is_bold = True
                else:
                    formatted_line += r'}'
                    is_bold = False
                i += 2
            else:
                formatted_line += line[i]
                i += 1
                
        if is_bold:
            formatted_line += r'}'
            
        latex_lines.append(formatted_line)

    if len(latex_lines) > 1:
        line_objs = [f'Tex(r"\\text{{{l}}}", tex_template=my_template)' for l in latex_lines]
        return f'VGroup({", ".join(line_objs)}).arrange(DOWN, aligned_edge=LEFT, buff=0.15)'
    
    return f'Tex(r"\\text{{{latex_lines[0]}}}", tex_template=my_template)'


def math(formula: str) -> str:
    """Wrap a formula in MathTex with high-contrast 3b1b coloring."""
    return f'MathTex(r"{formula}", tex_template=my_template, color=DesignTokens.WHITE).scale(1.2)'


def _region_to_coords(region: str) -> str:
    """Map region name to Manim coordinate."""
    regions = {
        "upper_left":    "np.array([-4,  2.5, 0])",
        "upper_center":  "np.array([ 0,  2.5, 0])",
        "upper_right":   "np.array([ 4,  2.5, 0])",
        "center_left":   "np.array([-4,  0,   0])",
        "center":        "np.array([ 0,  0,   0])",
        "center_right":  "np.array([ 4,  0,   0])",
        "lower_left":    "np.array([-4, -2.5, 0])",
        "lower_center":  "np.array([ 0, -2.5, 0])",
        "lower_right":   "np.array([ 4, -2.5, 0])",
    }
    return regions.get(region, "np.array([0, 0, 0])")


def _option_position(letter: str) -> str:
    """Fixed positions for MCQ option boxes in a 2x2 grid."""
    positions = {
        "A": "np.array([-3.2,  1.2, 0])", "1": "np.array([-3.2,  1.2, 0])",
        "B": "np.array([ 3.2,  1.2, 0])", "2": "np.array([ 3.2,  1.2, 0])",
        "C": "np.array([-3.2, -1.2, 0])", "3": "np.array([-3.2, -1.2, 0])",
        "D": "np.array([ 3.2, -1.2, 0])", "4": "np.array([ 3.2, -1.2, 0])",
    }
    return positions.get(letter.upper(), "np.array([0, 0, 0])")


def _safe_varname(text: str) -> str:
    """Convert text to a safe Python variable name."""
    return re.sub(r'[^a-z0-9_]', '_', text.lower())[:20]


# ── Scene code generators ─────────────────────────────────────────────────────

def _wait(duration: float, anim_time: float) -> str:
    """Return a self.wait() call with remaining time after animations."""
    remaining = max(round(duration - anim_time, 2), 0.1)
    return f"self.wait({remaining})"


def _scene_title_card(scene: dict, idx: int, topic: str = "EaseToLearn") -> str:
    d        = scene["visual_data"]
    title    = d.get("title") or d.get("name") or topic
    subtitle = d.get("subtitle", "").strip()
    duration = d.get("duration", 3.0)

    # 3b1b Proportional Sync: 30% entrance, 70% hold/read
    entrance_t = round(duration * 0.3, 2)
    hold_t     = round(duration * 0.7, 2)

    if subtitle:
        subtitle_code = f"""
        subtitle_{idx} = {tex(subtitle)}
        subtitle_{idx}.scale(DesignTokens.SUBTITLE_SIZE).set_color(DesignTokens.BLUE).next_to(title_{idx}, DOWN, buff=0.4)
        self.play(FadeIn(subtitle_{idx}), run_time={entrance_t})"""
        fadeout_sub = f", FadeOut(subtitle_{idx})"
    else:
        subtitle_code = ""
        fadeout_sub   = ""

    return f"""
        # Scene {idx}: title_card
        title_{idx} = {tex(title)}
        title_{idx}.scale(DesignTokens.TITLE_SIZE).set_color(DesignTokens.YELLOW).move_to(UP * 0.5)
        if title_{idx}.width > DesignTokens.MAX_WIDTH: title_{idx}.set_width(DesignTokens.MAX_WIDTH)

        self.play(Write(title_{idx}), run_time={entrance_t if not subtitle else entrance_t/2}){subtitle_code}
        self.wait({hold_t})
        self.play(FadeOut(title_{idx}){fadeout_sub})
"""


def _scene_concept_image(scene: dict, idx: int, image_path: str) -> str:
    d = scene["visual_data"]
    title    = d.get("title", "") or scene.get("narration_text", "")[:30] + "..."
    duration = d.get("duration", 3.0)

    if image_path and os.path.exists(image_path):
        # INDUSTRIAL FRAME: Shrink to 8.5 width to allow room for annotations
        img_line = f'img_{idx} = ImageMobject(r"{image_path}").scale_to_fit_width(8.5)'
    else:
        # Fallback: dark rectangle placeholder
        img_line = f'img_{idx} = Rectangle(width=8.5, height=4.8, color=DARK_GRAY, fill_opacity=0.3)'

    return f"""
        # Scene {idx}: concept_image (Premium Framed)
        {img_line}
        img_{idx}.move_to(ORIGIN)
        # Add a subtle glow frame
        frame_{idx} = SurroundingRectangle(img_{idx}, color=BLUE_E, buff=0.1, stroke_width=4)
        shadow_{idx} = frame_{idx}.copy().set_color(BLACK).set_opacity(0.5).shift(0.1*DOWN + 0.1*RIGHT)
        
        label_{idx} = {tex(title)}
        label_{idx}.scale(0.85).set_color(DesignTokens.YELLOW).to_edge(UP, buff=0.15)
        box_{idx} = BackgroundRectangle(label_{idx}, color=BLACK, fill_opacity=0.85, buff=0.15)
        
        self.play(FadeIn(shadow_{idx}), FadeIn(frame_{idx}), FadeIn(img_{idx}), run_time=1.2)
        self.play(FadeIn(box_{idx}), Write(label_{idx}))
        self.wait({duration})
"""


def _scene_image_arrow(scene: dict, idx: int, image_path: str = None) -> str:
    d        = scene["visual_data"]
    region   = d.get("region", "center")
    label    = d.get("label", "")
    duration = d.get("duration", 3.5)
    target   = _region_to_coords(region)

    return f"""
        # Scene {idx}: image_arrow — pointing to {region}
        target_{idx} = {target}
        # Premium Arrow Styling
        arrow_{idx} = Arrow(
            start=target_{idx} + np.array([1.5, -1.5, 0]), 
            end=target_{idx},
            buff=0.1, color=DesignTokens.BLUE, stroke_width=10, tip_length=0.4
        )
        glow_{idx} = arrow_{idx}.copy().set_stroke(DesignTokens.WHITE, opacity=0.3, width=15)
        
        label_v_{idx} = {tex(label)}
        label_v_{idx}.scale(0.8).set_color(DesignTokens.WHITE).next_to(arrow_{idx}.get_start(), DOWN + RIGHT, buff=0.1)
        bg_v_{idx} = BackgroundRectangle(label_v_{idx}, color=BLACK, fill_opacity=0.92, buff=0.2)

        self.play(Create(glow_{idx}), Create(arrow_{idx}), run_time=1.0)
        self.play(FadeIn(bg_v_{idx}), Write(label_v_{idx}))
        self.wait({duration})
        self.play(FadeOut(arrow_{idx}), FadeOut(glow_{idx}), FadeOut(label_v_{idx}), FadeOut(bg_v_{idx}))
"""


def _render_option_box(letter: str, name: str, idx: int, pos: str, is_ghost: bool = False) -> str:
    """
    Unified factory for MCQ option Mobjects. 
    Ensures 100% stylistic alignment between Layout, Highlight, Cross-Out, and Reveal.
    """
    vname = f"opt_{letter}_{idx}"
    op = 0.3 if is_ghost else 1.0
    
    return f"""
        {vname}_box = RoundedRectangle(width=5.8, height=1.5, corner_radius=0.15,
            color=DesignTokens.WHITE, stroke_width=2, stroke_opacity={op}).move_to({pos})
        {vname}_letter = {tex(letter + ".")}
        {vname}_letter.scale(0.85).set_color(DesignTokens.BLUE).move_to({pos} + np.array([-2.4, 0, 0])).set_opacity({op})
        {vname}_text = {tex(name, width=35)}
        {vname}_text.scale(0.65).set_color(DesignTokens.WHITE).move_to({pos} + np.array([0.3, 0, 0])).set_opacity({op})
        {vname}_grp = VGroup({vname}_box, {vname}_letter, {vname}_text)"""


def _scene_mcq_layout(scene: dict, idx: int) -> str:
    d       = scene["visual_data"]
    options = d.get("options", {})
    if isinstance(options, list):
        options = {
            item.get("letter", str(i)): item.get("name", str(item))
            for i, item in enumerate(options)
        }

    duration = d.get("duration", 2.0)

    # 3b1b Sync: 60% anim, 40% wait
    entrance_t = round(duration * 0.6, 2)
    hold_t     = round(duration * 0.4, 2)
    per_opt_t  = round(entrance_t / len(options), 2) if options else 0.5

    lines = [f"\n        # Scene {idx}: mcq_layout — draw 4 option boxes"]
    lines.append(f"        self._clear()")

    for letter, name in options.items():
        option_text = name if (name and str(name).strip() and str(name) != "-") else f"Option {letter}"
        pos = _option_position(letter)
        lines.append(_render_option_box(letter, option_text, idx, pos, is_ghost=False))
        lines.append(f"        self.play(FadeIn(opt_{letter}_{idx}_grp), run_time={per_opt_t})")

    lines.append(f"        self.wait({hold_t})")
    return "\n".join(lines)


def _scene_option_arrow(scene: dict, idx: int) -> str:
    d       = scene["visual_data"]
    letter  = d.get("letter", "A")
    verdict  = d.get("verdict") or d.get("color", "neutral")
    duration = d.get("duration", 3.0)

    # 3b1b Color Logic
    color = "DesignTokens.GREEN" if verdict in ["correct", "likely"] else ("DesignTokens.RED" if verdict == "wrong" else "DesignTokens.YELLOW")
    vname = f"opt_{letter.upper()}_{idx}"
    
    # 3b1b Sync: 50% highlight, 50% hold
    anim_t = round(duration * 0.5, 2)
    hold_t = round(duration * 0.5, 2)

    return f"""
        # Scene {idx}: option_arrow — highlight {letter}
        box_pos_{idx} = {_option_position(letter)}
        # Continuity Guard: Phantom redraw with helper
        {_render_option_box(letter, "", idx, f"box_pos_{idx}", is_ghost=True)}
        self.add(opt_{letter}_{idx}_grp)
        
        focus_ring_{idx} = RoundedRectangle(width=6.0, height=1.7, color={color}, stroke_width=4, corner_radius=0.15).move_to(box_pos_{idx})
        self.play(Indicate(focus_ring_{idx}, color={color}, scale_factor=1.1), run_time={anim_t})
        self.wait({hold_t})
"""


def _scene_cross_out(scene: dict, idx: int) -> str:
    d        = scene["visual_data"]
    duration = d.get("duration", 2.0)

    # Support both single "letter" and array "letters" from LLM, or string "B,C,D"
    raw = d.get("letters") or d.get("letter", "A")
    if isinstance(raw, str):
        letters = [l.strip().upper() for l in raw.replace(" ", "").split(",")]
    else:
        letters = raw
    letters = [l for l in letters if l in ("A", "B", "C", "D")]
    if not letters:
        letters = ["A"]

    lines = [f"\n        # Scene {idx}: cross_out — {letters}"]
    for li, letter in enumerate(letters):
        pos = _option_position(letter)
        lines.append(f"""
        # Continuity Guard: Phantom redraw with helper
        {_render_option_box(letter, "", idx, pos, is_ghost=True)}
        self.add(opt_{letter}_{idx}_grp)
        cross_{idx}_{li} = Cross(opt_{letter}_{idx}_grp, color=DesignTokens.RED, stroke_width=6)
        self.play(Create(cross_{idx}_{li}), run_time=0.4)""")

    lines.append(f"        self.wait({duration})")
    return "\n".join(lines)


def _scene_answer_reveal(scene: dict, idx: int) -> str:
    d           = scene["visual_data"]
    letter      = d.get("letter", "A")
    name        = d.get("name", "")
    explanation = d.get("explanation", "")[:80]
    duration    = d.get("duration", 4.0)
    pos         = _option_position(letter)

    exp_code = ""
    if explanation.strip():
        exp_code = f"""
        exp_{idx} = {tex(explanation)}
        exp_{idx}.scale(0.6).set_color(GREEN_C).to_edge(DOWN, buff=0.5)
        bg_{idx} = BackgroundRectangle(exp_{idx}, color=BLACK, fill_opacity=0.8, buff=0.1)
        self.play(FadeIn(bg_{idx}), Write(exp_{idx}))"""

    return f"""
        # Scene {idx}: answer_reveal — correct: {letter}
        # Continuity Guard: Phantom redraw with helper
        {_render_option_box(letter, name, idx, pos, is_ghost=True)}
        self.add(opt_{letter}_{idx}_grp)
        
        highlight_{idx} = SurroundingRectangle(opt_{letter}_{idx}_grp, color=DesignTokens.GREEN, buff=0.08, stroke_width=5)
        tick_{idx} = Tex(r"$\\checkmark$", tex_template=my_template).scale(1.4).set_color(DesignTokens.GREEN)
        tick_{idx}.move_to({pos} + np.array([2.2, 0, 0]))
        self.play(GrowFromCenter(highlight_{idx}), run_time=0.8)
        self.play(Write(tick_{idx})){exp_code}
        self.wait({duration})
"""


def _scene_formula_display(scene: dict, idx: int) -> str:
    d        = scene["visual_data"]
    formula  = d.get("formula", "")
    label    = d.get("label", "")
    duration = d.get("duration", 4.0)

    # 3b1b Proportional Sync: 40% anim, 60% wait
    entrance_t = round(duration * 0.4, 2)
    hold_t     = round(duration * 0.6, 2)

    return f"""
        # Scene {idx}: formula_display
        self._clear()
        formula_{idx} = {math(formula)}
        formula_{idx}.move_to(UP * 0.5)
        if formula_{idx}.width > DesignTokens.MAX_WIDTH: formula_{idx}.set_width(DesignTokens.MAX_WIDTH)

        label_{idx} = {tex(label)}
        label_{idx}.scale(DesignTokens.SUBTITLE_SIZE).set_color(DesignTokens.BLUE).next_to(formula_{idx}, DOWN, buff=0.5)
        if label_{idx}.width > 10: label_{idx}.set_width(10)

        self.play(Write(formula_{idx}), run_time={entrance_t})
        self.play(FadeIn(label_{idx}), run_time=0.5)
        self.wait({max(hold_t - 0.5, 0.1)})
        self.play(FadeOut(formula_{idx}), FadeOut(label_{idx}))
"""


def _scene_step_by_step(scene: dict, idx: int) -> str:
    d        = scene["visual_data"]
    heading  = d.get("heading", "Solution")
    steps    = d.get("steps", [])[:4]
    duration = d.get("duration", 5.0)

    lines = [f"\n        # Scene {idx}: step_by_step"]
    lines.append(f"        self._clear()")
    lines.append(f"        heading_{idx} = {tex(heading)}")
    lines.append(f"        heading_{idx}.scale(1.0).set_color(YELLOW).to_edge(UP, buff=0.4)")
    lines.append(f"        self.play(Write(heading_{idx}))")

    anim_time = 0.7 + len(steps) * 0.9  # heading + steps
    for si, step in enumerate(steps):
        vname = f"step_{idx}_{si}"
        is_math = any(c in step for c in ['=', '∫', '∑', 'd/dx', '\\']) or \
                  bool(re.search(r'\^|_|\d+\s*[\+\-\*\/]|\bfrac\b|\bsqrt\b|\bint\b', step))
        if is_math:
            lines.append(f"        {vname} = {math(step[:80])}")
        else:
            lines.append(f"        {vname} = {tex(step[:100])}")
        lines.append(f"        {vname}.scale(0.75).move_to(np.array([0, {1.2 - si * 1.0}, 0]))")
        lines.append(f"        if {vname}.width > 12: {vname}.set_width(12)")  # Adaptive Fitting
        lines.append(f"        {vname}_bg = BackgroundRectangle({vname}, color=BLACK, fill_opacity=0.7, buff=0.1)")
        lines.append(f"        self.play(FadeIn({vname}_bg), Write({vname}), run_time=0.9)")

    lines.append(f"        {_wait(duration, anim_time)}")
    lines.append(f"        self._clear()")
    return "\n".join(lines)


def _scene_concept_bullets(scene: dict, idx: int) -> str:
    d        = scene["visual_data"]
    heading  = d.get("heading", "")
    bullets  = d.get("bullets", [])[:3]
    duration = d.get("duration", 4.0)

    lines = [f"\n        # Scene {idx}: concept_bullets"]
    lines.append(f"        heading_{idx} = {tex(heading)}")
    lines.append(f"        heading_{idx}.scale(1.0).set_color(YELLOW).move_to(UP * 2.5)")
    lines.append(f"        self.play(Write(heading_{idx}))")

    anim_time = 0.7 + len(bullets) * 0.7  # heading + bullets
    for bi, bullet in enumerate(bullets):
        vname = f"bullet_{idx}_{bi}"
        lines.append(f"        {vname} = VGroup(")
        lines.append(f'            Tex(r"$\\bullet$", tex_template=my_template).scale(0.8).set_color(BLUE_C),')
        lines.append(f"            {tex(bullet[:65])}.scale(0.75),")
        lines.append(f"        ).arrange(RIGHT, buff=0.15)")
        lines.append(f"        {vname}.move_to(np.array([0, {1.2 - bi * 1.1}, 0]))")
        lines.append(f"        if {vname}.width > 12: {vname}.set_width(12)")  # Adaptive Fitting
        lines.append(f"        {vname}_bg = BackgroundRectangle({vname}, color=BLACK, fill_opacity=0.7, buff=0.1)")
        lines.append(f"        self.play(FadeIn({vname}_bg), FadeIn({vname}), run_time=0.7)")

    lines.append(f"        {_wait(duration, anim_time)}")
    lines.append(f"        self._clear()")
    return "\n".join(lines)


def _scene_summary(scene: dict, idx: int) -> str:
    d        = scene["visual_data"]
    heading  = d.get("heading", "Key Takeaways")
    points   = d.get("points", [])[:3]
    duration = d.get("duration", 4.0)

    # 3b1b Proportional Sync
    per_point_t = round(duration / (len(points) + 1), 2)

    lines = [f"\n        # Scene {idx}: summary"]
    lines.append(f"        self._clear()")
    lines.append(f"        heading_{idx} = {tex(heading)}")
    lines.append(f"        heading_{idx}.scale(1.1).set_color(DesignTokens.GREEN).move_to(UP * 2.8)")
    lines.append(f"        self.play(Write(heading_{idx}), run_time={per_point_t})")

    for pi, point in enumerate(points):
        vname = f"point_{idx}_{pi}"
        lines.append(f"        {vname} = VGroup(")
        lines.append(f'            Tex(r"\\checkmark", tex_template=my_template).scale(0.8).set_color(DesignTokens.GREEN),')
        lines.append(f"            {tex(point, width=40)}.scale(DesignTokens.BODY_SIZE),")
        lines.append(f"        ).arrange(RIGHT, buff=0.2)")
        lines.append(f"        {vname}.move_to(np.array([0, {1.4 - pi * 1.1}, 0]))")
        lines.append(f"        {vname}_bg = BackgroundRectangle({vname}, color=BLACK, fill_opacity=0.7, buff=0.1)")
        lines.append(f"        self.play(FadeIn({vname}_bg), FadeIn({vname}), run_time={per_point_t})")

    lines.append(f"        self.wait(1.0)")
    return "\n".join(lines)


_GRAPH_SYSTEM_PROMPT = """You are a Manim animation code writer for educational videos.

Write ONLY the indented body code (8-space indent) that goes inside a Manim construct() method.
The scene index is provided — suffix ALL variable names with _{idx} to avoid conflicts.

━━━ GOLDEN EXAMPLES (Follow these patterns EXACTLY) ━━━

EXAMPLE 1 (Function Plot):
        axes_{idx} = Axes(x_range=[-3, 3, 1], y_range=[0, 9, 1], axis_config={"include_tip": True})
        axes_{idx}.add_coordinates()
        curve_{idx} = axes_{idx}.get_graph(lambda x: x**2, color=BLUE)
        self.play(Create(axes_{idx}))
        self.play(Create(curve_{idx}))
        self.wait({duration})

EXAMPLE 2 (Bar Chart):
        # Use BarChart with explicit length for 16:9 frame safety
        bar_{idx} = BarChart(values=[10, 20, 30], bar_names=["A", "B", "C"], y_range=[0, 40, 10], x_length=7, y_length=5)
        self.play(Create(bar_{idx}))
        self.wait({duration})

━━━ INDUSTRIAL LAYOUT RULES ━━━
- ALWAYS use `axes.add_coordinates()` for clarity.
- ALWAYS set `x_length` and `y_length` to prevent the graph from touching screen edges.
- MANDATORY: Every Axes() call MUST include x_length=8, y_length=5.
- Never create Axes without explicit x_length and y_length.
- Never use default Axes sizing.
- Use `x_length=8, y_length=5` as a safe default for a 16:9 horizontal frame.
- For geometry, avoid `self.set_background()`.

━━━ CRITICAL SECURITY RULES ━━━
- NEVER use `self.set_background()` or `self.set_text()`. They do not exist.
- ALWAYS use `Tex(r"\\text{{...}}")` or `MathTex(r"...")` for text/math.
- ALWAYS suffix every variable with _{idx}.
- USE THE 3B1B DESIGN SYSTEM: Use `DesignTokens.BLUE`, `DesignTokens.YELLOW`, `DesignTokens.GREEN`, `DesignTokens.RED`, `DesignTokens.WHITE`.
- FRAME SAFETY: Title size `DesignTokens.TITLE_SIZE`, Body size `DesignTokens.BODY_SIZE`. 
- Output ONLY the Python code. No explanation, no markdown.
- Max 40 lines of code. No imports. No class definitions.
"""

# After getting code from LLM, force-suffix common variable names
def _sanitize_graph_code(code: str, idx: int) -> str:
    common_vars = [
        "axes", "curve", "graph", "label", "bar",
        "dot", "line", "arrow", "text", "point",
        "x_label", "y_label", "area", "region"
    ]
    for var in common_vars:
        # Replace var = with var_{idx} = 
        code = re.sub(
            rf'\b{var}\b(?!\w|_{idx})',
            f'{var}_{idx}',
            code
        )
    return code

def _validate_graph_code(code: str) -> bool:
    banned = [
        "self.set_background",
        "self.set_text", 
        "Text(",
        "self.camera.background_color = BLACK",
    ]
    for banned_pattern in banned:
        if banned_pattern in code:
            print(f"   ⚠️ graph_hint: banned pattern found: {banned_pattern}")
            return False
    return True

def _graph_axes_fallback(idx: int, description: str, duration: float) -> str:
    return f"""
        # Scene {idx}: graph_hint — fallback
        self._clear()
        axes_{idx} = Axes(
            x_range=[-0.5, 5, 1], y_range=[-0.5, 5, 1],
            x_length=8, y_length=5,
            axis_config={{"color": BLUE_C, "include_tip": True}},
        ).move_to(ORIGIN)
        label_{idx} = Tex(r"\\text{{{description[:30]}}}")
        label_{idx}.scale(0.65).next_to(axes_{idx}, DOWN, buff=0.3)
        self.play(Create(axes_{idx}), Write(label_{idx}), run_time=1.2)
        self.wait({duration})
        self._clear()
"""

def _scene_graph_hint(scene: dict, idx: int) -> str:
    d           = scene["visual_data"]
    graph_type  = d.get("graph_type", "generic")
    description = d.get("description", "")
    highlight   = d.get("highlight", "")
    duration    = d.get("duration", 4.0)

    prompt = (
        f"Scene index: {idx}\n"
        f"Graph type: {graph_type}\n"
        f"Description: {description}\n"
        f"Highlight/key insight: {highlight}\n"
        f"Wait duration: {duration} seconds\n\n"
        "INSTRUCTION: Create an accurate mathematical graph. "
        "If it is a parabola, ensure it is oriented correctly. "
        "If it is an integral, SHADE THE AREA between the limits mentioned in the description. "
        "Write the Manim construct() body code for this graph scene."
    )

    try:
        code = LLMFactory.get_completion(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=_GRAPH_SYSTEM_PROMPT.format(idx=idx, duration=duration),
            json_mode=False
        )
        # Strip any markdown fences if the extraction in LLMFactory was too loose
        code = re.sub(r"```(?:python)?", "", code, flags=re.IGNORECASE).replace("```", "").strip()
        
        code = _sanitize_graph_code(code, idx)
        
        if "Axes(" in code and "x_length" not in code:
            code = code.replace("Axes(", "Axes(x_length=8, y_length=5, ")

        if not _validate_graph_code(code):
            return _graph_axes_fallback(idx, description, duration)
        
        import textwrap
        indented_code = textwrap.indent(code, "        ")
        
        # Return exactly what Groq wrote so that list comprehensions down the chain are accurate.
        print(f"   🔢 graph_hint scene {idx}: LLM generated {len(code.splitlines())} lines")
        return f"        # Scene {idx}: graph_hint — {graph_type} (LLM-generated)\n{indented_code}\n"
    except Exception as e:
        print(f"   ⚠️  graph_hint LLM failed ({e}), falling back to plain axes")
        return _graph_axes_fallback(idx, description, duration)


def _scene_annotated_image(scene: dict, idx: int, global_image_path: str = None) -> str:
    d = scene["visual_data"]
    # Priority: 1. Scene-specific path | 2. Global path passed from builder
    image_path = d.get("image_path") or global_image_path or "None"
    label = d.get("label", "")
    bullets = d.get("bullets", [])[:3]
    duration = d.get("duration", 4.0)
    
    bullets_code = ""
    if bullets:
        bullets_code = f"""
        bullets_grp_{idx} = VGroup(
            {", ".join([f"{tex(b, width=22)}.scale(0.65)" for b in bullets])}
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        """
        left_grp_code = f"""left_grp_{idx} = VGroup(title_{idx}, bullets_grp_{idx}).arrange(DOWN, aligned_edge=LEFT, buff=0.5)"""
    else:
        left_grp_code = f"""left_grp_{idx} = VGroup(title_{idx})"""

    # ── Arrow target: vision-grounded coords or fallback to region grid ──
    landmark_coords = d.get("landmark_coords")  # injected by build_manim_script
    if landmark_coords:
        # Compute Manim scene coordinates from normalized [x, y]
        # Image is scaled to width=5.5, centered at RIGHT * 3.2 (x=3.2)
        # DALL-E images are 1024x1024 (square), so height = width = 5.5
        norm_x, norm_y = landmark_coords
        # Convert: image coords (0,0)=top-left → Manim coords
        target_x = 3.2 + (norm_x - 0.5) * 5.5   # center of image is at x=3.2
        target_y = -(norm_y - 0.5) * 5.5          # Manim y is inverted vs image y
        arrow_end_code = f"np.array([{target_x:.3f}, {target_y:.3f}, 0])"
    else:
        # Fallback: coarse 9-region grid
        region = d.get("region", "center_left")
        region_map = {
            "upper_left": "get_corner(UL)",
            "upper_center": "get_top()",
            "upper_right": "get_corner(UR)",
            "center_left": "get_left()",
            "center": "get_center()",
            "center_right": "get_right()",
            "lower_left": "get_corner(DL)",
            "lower_center": "get_bottom()",
            "lower_right": "get_corner(DR)"
        }
        anchor = region_map.get(region, "get_left()")
        arrow_end_code = f"img_{idx}.{anchor}"

    return f"""
        # Scene {idx}: annotated_image
        self._clear()
        img_{idx} = ImageMobject(r"{image_path}").scale_to_fit_width(5.5).move_to(RIGHT * 3.2)
        frame_{idx} = SurroundingRectangle(img_{idx}, color=BLUE_E, buff=0.08, stroke_width=3)
        
        # Left side: explanation
        title_{idx} = {tex(label)}.scale(0.9).set_color(DesignTokens.YELLOW)
        {bullets_code}
        {left_grp_code}
        left_grp_{idx}.move_to(LEFT * 3.5)
        
        # Arrow from text to image landmark
        arrow_{idx} = Arrow(
            start=left_grp_{idx}.get_right() + RIGHT * 0.2,
            end={arrow_end_code},
            color=DesignTokens.YELLOW, buff=0.1, stroke_width=6
        )
        
        self.play(FadeIn(img_{idx}), FadeIn(frame_{idx}))
        self.play(Write(left_grp_{idx}))
        self.play(GrowArrow(arrow_{idx}))
        self.wait({duration})
    """


def _scene_key_point(scene: dict, idx: int) -> str:
    """Presentation mode: single heading + body text."""
    d        = scene["visual_data"]
    heading  = d.get("heading", "")
    body     = d.get("body", "")[:120]
    duration = d.get("duration", 4.0)

    # Wrap body into lines of ~45 chars
    wrapped = textwrap.wrap(body, 45)

    lines = [f"\n        # Scene {idx}: key_point (presentation)"]
    lines.append(f"        self._clear()")
    lines.append(f"        heading_{idx} = {tex(heading)}")
    lines.append(f"        heading_{idx}.scale(1.0).set_color(YELLOW).move_to(UP * 2.8)")
    lines.append(f"        self.play(Write(heading_{idx}))")

    body_vnames = []
    for li, line in enumerate(wrapped[:5]):
        vn = f"body_{idx}_{li}"
        lines.append(f"        {vn} = {tex(line)}")
        lines.append(f"        {vn}.scale(0.75).move_to(np.array([0, {1.5 - li * 0.9}, 0]))")
        lines.append(f"        {vn}_bg = BackgroundRectangle({vn}, color=BLACK, fill_opacity=0.7, buff=0.1)")
        lines.append(f"        self.play(FadeIn({vn}_bg), FadeIn({vn}), run_time=0.5)")
        body_vnames.append(vn)

    lines.append(f"        self.wait({duration})")
    lines.append(f"        self._clear()")
    return "\n".join(lines)


# ── Dispatcher ────────────────────────────────────────────────────────────────

_GENERATORS = {
    "title_card":       _scene_title_card,
    "concept_image":    _scene_concept_image,
    "image_arrow":      _scene_image_arrow,
    "annotated_image":  _scene_annotated_image,
    "mcq_layout":       _scene_mcq_layout,
    "option_arrow":     _scene_option_arrow,
    "option_highlight": _scene_option_arrow,
    "cross_out":        _scene_cross_out,
    "answer_reveal":    _scene_answer_reveal,
    "formula_display":  _scene_formula_display,
    "step_by_step":     _scene_step_by_step,
    "concept_bullets":  _scene_concept_bullets,
    "summary":          _scene_summary,
    "graph_hint":       _scene_graph_hint,
    "key_point":        _scene_key_point,
}


# ── Public API ────────────────────────────────────────────────────────────────

def build_manim_script(
    scenes: list,
    image_path: str,
    topic: str,
    output_path: str,
    knowledge_base: dict = None,
    landmark_coords: dict = None,
) -> str:
    """
    Convert a list of scene dicts into a complete Manim Python script.

    Args:
        scenes          : list of scene dicts (from director_agent)
        image_path      : abs path to Gemini-generated concept image (or None)
        topic           : topic name (used in comments)
        output_path     : where to write the .py file
        landmark_coords : {scene_index_str: {label: [x, y]}} from vision_grounder

    Returns:
        Path to the written script
    """
    landmark_coords = landmark_coords or {}

    scene_blocks = []
    for i, scene in enumerate(scenes):
        vtype = scene.get("visual_type", "title_card")
        gen   = _GENERATORS.get(vtype)

        if gen is None:
            print(f"   ⚠️  Unknown visual_type '{vtype}' — skipping scene {i}")
            continue

        # ── Inject vision-grounded landmark coords into annotated_image scenes ──
        if vtype == "annotated_image" and str(i) in landmark_coords:
            scene_coords = landmark_coords[str(i)]
            target_landmark = scene.get("visual_data", {}).get("target_landmark", "")
            # Find the matching coordinate (case-insensitive)
            for label, coords in scene_coords.items():
                if label.lower() == target_landmark.lower() or target_landmark.lower() in label.lower():
                    scene["visual_data"]["landmark_coords"] = coords
                    print(f"   📍 Injected coords {coords} for scene {i} landmark '{target_landmark}'")
                    break

        try:
            if vtype == "title_card":
                block = gen(scene, i, topic)
            elif vtype in ["concept_image", "image_arrow", "annotated_image"]:
                block = gen(scene, i, image_path)
            else:
                block = gen(scene, i)
            scene_blocks.append(block)
        except Exception as e:
            print(f"   ⚠️  Scene {i} ({vtype}) generation failed: {e} — skipping")
            continue

    scenes_code = "\n".join(scene_blocks)

    script = f'''"""
Auto-generated Manim script for: {topic}
Generated by EaseToLearn template_renderer.py — DO NOT EDIT MANUALLY
"""

import numpy as np
from manim import *

# ── LaTeX Template ─────────────────────────────────────────────────────────────
my_template = TexTemplate()
my_template.add_to_preamble(r"\\usepackage{{amsmath}}")
my_template.add_to_preamble(r"\\usepackage{{amssymb}}")

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
''' + scenes_code + f'''
        self.wait(1)
'''

    with open(output_path, "w") as f:
        f.write(script)

    print(f"✅ Manim script written: {output_path} ({len(scenes)} scenes)")
    return output_path




# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys, json

    # Minimal test scenes covering all visual types
    test_scenes = [
        {"visual_type": "title_card",
         "narration_text": "Today we study the Internal Iliac Artery.",
         "visual_data": {"title": "Internal Iliac Artery", "subtitle": "Branches and Supply"}},

        {"visual_type": "concept_image",
         "narration_text": "Here is the anatomical diagram.",
         "visual_data": {"title": "Anatomical Overview"}},

        {"visual_type": "image_arrow",
         "narration_text": "This branch comes off here.",
         "visual_data": {"region": "upper_right", "label": "Anterior Division"}},

        {"visual_type": "concept_bullets",
         "narration_text": "Three key facts to remember.",
         "visual_data": {"heading": "Key Facts", "bullets": ["Supplies pelvic region", "Two divisions: anterior and posterior", "Branches include uterine and obturator"]}},

        {"visual_type": "mcq_layout",
         "narration_text": "Now let us look at the options.",
         "visual_data": {"options": {"A": "Ovarian artery", "B": "Superior vesical", "C": "Uterine artery", "D": "Internal pudendal"}}},

        {"visual_type": "option_arrow",
         "narration_text": "Option A is not a branch — it comes from the aorta.",
         "visual_data": {"letter": "A", "verdict": "wrong", "reason": "Arises from abdominal aorta, not iliac"}},

        {"visual_type": "cross_out",
         "narration_text": "So we eliminate option A.",
         "visual_data": {"letter": "A", "name": "Ovarian artery"}},

        {"visual_type": "answer_reveal",
         "narration_text": "The correct answer is A — the ovarian artery does NOT branch from here.",
         "visual_data": {"letter": "A", "name": "Ovarian artery", "explanation": "Arises from abdominal aorta directly"}},

        {"visual_type": "formula_display",
         "narration_text": "The key equation is cardiac output equals heart rate times stroke volume.",
         "visual_data": {"formula": r"CO = HR \times SV", "label": "Cardiac Output Formula"}},

        {"visual_type": "step_by_step",
         "narration_text": "Solve the integral step by step.",
         "visual_data": {"heading": "Integration by Parts", "steps": [r"\int \ln x \, dx", r"u = \ln x,\quad dv = dx", r"= x\ln x - \int x \cdot \frac{1}{x}dx", r"= x\ln x - x + C"]}},

        {"visual_type": "summary",
         "narration_text": "Let us summarise what we learned.",
         "visual_data": {"heading": "Key Takeaways", "points": ["Ovarian artery comes from aorta", "Internal iliac has anterior and posterior divisions", "Uterine and pudendal are branches"]}},
    ]

    path = build_manim_script(
        scenes=test_scenes,
        image_path=None,
        topic="Internal Iliac Artery",
        output_path="/tmp/test_render.py",
    )
    print(f"\nGenerated script at: {path}")
    print("\nFirst 40 lines:")
    with open(path) as f:
        for i, line in enumerate(f):
            if i >= 40: break
            print(line, end="")
