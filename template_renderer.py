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
from groq import Groq


# ── LaTeX helpers ─────────────────────────────────────────────────────────────

def tex(text: str) -> str:
    """Wrap plain text in LaTeX text mode for Tex()."""
    if not text or not text.strip():
        text = "-"  # empty/space Tex() crashes Manim
    escaped = (text
        .replace("\\", r"\textbackslash{}")
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
    return f'Tex(r"\text{{{escaped}}}", tex_template=my_template)'


def math(formula: str) -> str:
    """Wrap a formula in MathTex."""
    return f'MathTex(r"{formula}", tex_template=my_template)'


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
        "A": "np.array([-3.2,  1.2, 0])",
        "B": "np.array([ 3.2,  1.2, 0])",
        "C": "np.array([-3.2, -1.2, 0])",
        "D": "np.array([ 3.2, -1.2, 0])",
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


def _scene_title_card(scene: dict, idx: int) -> str:
    d        = scene["visual_data"]
    title    = d.get("title", "EaseToLearn")
    subtitle = d.get("subtitle", "").strip()
    duration = d.get("duration", 3.0)

    anim_time = 1.2 + (0.8 if subtitle else 0)

    if subtitle:
        subtitle_code = f"""
        subtitle_{idx} = {tex(subtitle)}
        subtitle_{idx}.scale(0.8).set_color(BLUE_C).next_to(title_{idx}, DOWN, buff=0.4)
        self.play(FadeIn(subtitle_{idx}), run_time=0.8)"""
        fadeout_sub = f", FadeOut(subtitle_{idx})"
    else:
        subtitle_code = ""
        fadeout_sub   = ""

    return f"""
        # Scene {idx}: title_card
        title_{idx} = {tex(title)}
        title_{idx}.scale(1.4).move_to(UP * 0.5)
        self.play(Write(title_{idx}), run_time=1.2){subtitle_code}
        {_wait(duration, anim_time)}
        self.play(FadeOut(title_{idx}){fadeout_sub})
"""


def _scene_concept_image(scene: dict, idx: int, image_path: str) -> str:
    d = scene["visual_data"]
    title    = d.get("title", "")
    duration = d.get("duration", 3.0)

    if image_path and os.path.exists(image_path):
        img_line = f'img_{idx} = ImageMobject(r"{image_path}").scale_to_fit_width(13)'
    else:
        # Fallback: dark rectangle placeholder
        img_line = f'img_{idx} = Rectangle(width=13, height=7.3, color=DARK_GRAY, fill_opacity=0.3)'

    return f"""
        # Scene {idx}: concept_image
        {img_line}
        img_{idx}.move_to(ORIGIN)
        label_{idx} = {tex(title)}
        label_{idx}.scale(0.9).set_color(YELLOW).to_edge(UP, buff=0.2)
        box_{idx} = BackgroundRectangle(label_{idx}, color=BLACK, fill_opacity=0.7, buff=0.1)
        self.play(FadeIn(img_{idx}), run_time=1.0)
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
        arrow_{idx} = Arrow(
            start=target_{idx} + np.array([1.2, -1.2, 0]),
            end=target_{idx},
            color=YELLOW, buff=0.1, stroke_width=4,
        )
        label_{idx} = {tex(label)}
        label_{idx}.scale(0.75).set_color(YELLOW)
        label_{idx}.next_to(arrow_{idx}.get_start(), RIGHT, buff=0.15)
        box_{idx} = BackgroundRectangle(label_{idx}, color=BLACK, fill_opacity=0.75, buff=0.08)
        self.play(GrowArrow(arrow_{idx}), run_time=0.8)
        self.play(FadeIn(box_{idx}), Write(label_{idx}))
        self.wait({duration})
        self.play(FadeOut(arrow_{idx}), FadeOut(label_{idx}), FadeOut(box_{idx}))
"""


def _scene_mcq_layout(scene: dict, idx: int) -> str:
    d       = scene["visual_data"]
    options = d.get("options", {})
    duration = d.get("duration", 2.0)

    lines = [f"\n        # Scene {idx}: mcq_layout — draw 4 option boxes"]
    lines.append(f"        self._clear_keep_image()")

    for letter, name in options.items():
        pos   = _option_position(letter)
        vname = f"opt_{letter}_{idx}"
        lines.append(f"""
        {vname}_box = RoundedRectangle(width=5.8, height=1.5, corner_radius=0.15,
            color=WHITE, stroke_width=2).move_to({pos})
        {vname}_letter = {tex(letter + ".")}
        {vname}_letter.scale(0.85).set_color(BLUE_C).move_to({pos} + np.array([-2.4, 0, 0]))
        {vname}_text = {tex(name[:45])}
        {vname}_text.scale(0.65).move_to({pos} + np.array([0.3, 0, 0]))
        self.play(
            FadeIn({vname}_box),
            Write({vname}_letter),
            Write({vname}_text),
            run_time=0.5,
        )""")

    lines.append(f"        self.wait({duration})")
    return "\n".join(lines)


def _scene_option_arrow(scene: dict, idx: int) -> str:
    d       = scene["visual_data"]
    letter  = d.get("letter", "A")
    # support both field naming conventions from different LLMs
    verdict  = d.get("verdict") or d.get("color", "neutral")
    reason   = d.get("reason") or d.get("body") or d.get("name", "")
    duration = d.get("duration", 3.5)

    color_map = {"correct": "GREEN", "likely": "GREEN",
                 "wrong": "RED", "incorrect": "RED", "unlikely": "RED",
                 "neutral": "YELLOW"}
    color = color_map.get(verdict, "YELLOW")
    pos   = _option_position(letter)

    return f"""
        # Scene {idx}: option_arrow — {letter} ({verdict})
        arrow_{idx} = Arrow(
            start={pos} + np.array([-5, 0, 0]),
            end={pos} + np.array([-2.9, 0, 0]),
            color={color}, stroke_width=5, buff=0.05,
        )
        reason_{idx} = {tex(reason[:60])}
        reason_{idx}.scale(0.6).set_color({color}).to_edge(DOWN, buff=0.5)
        bg_{idx} = BackgroundRectangle(reason_{idx}, color=BLACK, fill_opacity=0.8, buff=0.1)
        self.play(GrowArrow(arrow_{idx}), run_time=0.7)
        self.play(FadeIn(bg_{idx}), Write(reason_{idx}))
        self.wait({duration})
        self.play(FadeOut(arrow_{idx}), FadeOut(reason_{idx}), FadeOut(bg_{idx}))
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
        cross_{idx}_{li} = Cross(
            RoundedRectangle(width=5.8, height=1.5).move_to({pos}),
            color=RED, stroke_width=6,
        )
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
        ans_box_{idx} = RoundedRectangle(width=5.8, height=1.5, corner_radius=0.15).move_to({pos})
        highlight_{idx} = SurroundingRectangle(ans_box_{idx}, color=GREEN, buff=0.08, stroke_width=5)
        tick_{idx} = Tex(r"$\checkmark$", tex_template=my_template).scale(1.4).set_color(GREEN)
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

    return f"""
        # Scene {idx}: formula_display
        self._clear()
        formula_{idx} = {math(formula)}
        formula_{idx}.scale(1.6).move_to(UP * 0.5)
        label_{idx} = {tex(label)}
        label_{idx}.scale(0.75).set_color(BLUE_C).next_to(formula_{idx}, DOWN, buff=0.5)
        self.play(Write(formula_{idx}), run_time=1.5)
        self.play(FadeIn(label_{idx}))
        self.wait({duration})
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
            lines.append(f"        {vname} = {math(step[:60])}")
        else:
            lines.append(f"        {vname} = {tex(step[:70])}")
        lines.append(f"        {vname}.scale(0.75).move_to(np.array([0, {1.2 - si * 1.0}, 0]))")
        lines.append(f"        self.play(Write({vname}), run_time=0.9)")

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
        lines.append(f"        self.play(FadeIn({vname}), run_time=0.7)")

    lines.append(f"        {_wait(duration, anim_time)}")
    lines.append(f"        self._clear()")
    return "\n".join(lines)


def _scene_summary(scene: dict, idx: int) -> str:
    d        = scene["visual_data"]
    heading  = d.get("heading", "Key Takeaways")
    points   = d.get("points", [])[:3]
    duration = d.get("duration", 4.0)

    lines = [f"\n        # Scene {idx}: summary"]
    lines.append(f"        self._clear()")
    lines.append(f"        heading_{idx} = {tex(heading)}")
    lines.append(f"        heading_{idx}.scale(1.1).set_color(GREEN).move_to(UP * 2.8)")
    lines.append(f"        self.play(Write(heading_{idx}))")

    anim_time = 0.7 + len(points) * 0.7
    for pi, point in enumerate(points):
        vname = f"point_{idx}_{pi}"
        lines.append(f"        {vname} = VGroup(")
        lines.append(f'            Tex(r"$\\checkmark$", tex_template=my_template).scale(0.8).set_color(GREEN),')
        lines.append(f"            {tex(point[:65])}.scale(0.75),")
        lines.append(f"        ).arrange(RIGHT, buff=0.2)")
        lines.append(f"        {vname}.move_to(np.array([0, {1.4 - pi * 1.1}, 0]))")
        lines.append(f"        self.play(FadeIn({vname}), run_time=0.7)")

    lines.append(f"        {_wait(duration, anim_time)}")
    return "\n".join(lines)


_GRAPH_SYSTEM_PROMPT = """You are a Manim animation code writer for educational videos.

Write ONLY the indented body code (8-space indent) that goes inside a Manim construct() method.
The scene index is provided — suffix ALL variable names with _{idx} to avoid conflicts.

RULES:
- Use `from manim import *` is already imported — do not re-import
- config.background_color is already "#0d0d1a" (dark)
- Start with: self._clear()  (already defined in the class)
- End with: self._clear()
- Use Axes for line/curve graphs, VGroup of Rectangle for bar charts, NumberLine for number lines
- CRITICAL: Use `self.play(Create(axes_idx))` and `self.play(Create(curve_idx))` to animate the drawing process.
- FORBIDDEN: Do not use `self.add()` for main elements. They MUST be animated with `Create`, `Write`, or `FadeIn`.
- For definite integrals, use `axes.get_area(curve, x_range=[a, b])` and animate it with `self.play(FadeIn(area_idx))`.
- Ensure Axes `x_range` and `y_range` cover the specific intervals mentioned in the description.
- Use MathTex for all labels and math expressions
- Suffix every variable with _{idx} (e.g. axes_3, curve_3, bar_3)
- Max 40 lines of code
- No imports, no class definition, no def construct — just the body lines
- Use 8-space indentation throughout
- self.wait({duration}) before the final self._clear()

Output ONLY the Python code lines. No explanation, no markdown fences."""

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
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": _GRAPH_SYSTEM_PROMPT.format(idx=idx, duration=duration)},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=600,
        )
        code = resp.choices[0].message.content.strip()
        # Strip any markdown fences Groq might add
        code = re.sub(r"```(?:python)?", "", code).replace("```", "").strip()
        
        # Return exactly what Groq wrote so that list comprehensions down the chain are accurate.
        print(f"   🔢 graph_hint scene {idx}: LLM generated {len(code.splitlines())} lines")
        return f"\n# Scene {idx}: graph_hint — {graph_type} (LLM-generated)\n" + code + "\n"
    except Exception as e:
        print(f"   ⚠️  graph_hint LLM failed ({e}), falling back to plain axes")
        return f"""
        # Scene {idx}: graph_hint — {graph_type} (fallback)
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
        lines.append(f"        self.play(FadeIn({vn}), run_time=0.5)")
        body_vnames.append(vn)

    lines.append(f"        self.wait({duration})")
    lines.append(f"        self._clear()")
    return "\n".join(lines)


# ── Dispatcher ────────────────────────────────────────────────────────────────

_GENERATORS = {
    "title_card":       _scene_title_card,
    "concept_image":    _scene_concept_image,
    "image_arrow":      _scene_image_arrow,
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
) -> str:
    """
    Convert a list of scene dicts into a complete Manim Python script.

    Args:
        scenes      : list of scene dicts (from director_agent)
        image_path  : abs path to Gemini-generated concept image (or None)
        topic       : topic name (used in comments)
        output_path : where to write the .py file

    Returns:
        Path to the written script
    """
    scene_blocks = []
    for i, scene in enumerate(scenes):
        vtype = scene.get("visual_type", "title_card")
        gen   = _GENERATORS.get(vtype)

        if gen is None:
            print(f"   ⚠️  Unknown visual_type '{vtype}' — skipping scene {i}")
            continue

        try:
            block = gen(scene, i, image_path) if vtype in ["concept_image", "image_arrow"] else gen(scene, i)
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
# Includes amssymb and amsmath for symbols like \checkmark and \bullet
my_template = TexTemplate()
my_template.add_to_preamble(r"\\usepackage{{amsmath}}")
my_template.add_to_preamble(r"\\usepackage{{amssymb}}")

config.background_color = "#0d0d1a"  # deep dark background
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
        # Set default template for all Tex/MathTex objects in this scene
        self.camera.background_color = "#0d0d1a"
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
