"""
Step 2: Director Agent (LLM — Claude Opus)

Responsibilities:
  1. Decides the render mode  : manim | presentation | human_face
  2. Writes the teaching script: ordered list of scenes

Render modes:
  manim        - Animated Manim video. Default for most content.
                 Best for: maths, physics, medical MCQ, visual concepts.
  presentation - Slide-based video (tony_pipeline).
                 Best for: case studies, English, UPSC essays, simple concepts.
  human_face   - (Future) Talking head + subtitle strips.
                 Best for: conversational walkthroughs.

Visual types per mode:

  MANIM:
    title_card       {"title": str, "subtitle": str}
    concept_bullets  {"heading": str, "bullets": list[str]}  # max 3 bullets, ≤8 words each
    formula_display  {"formula": str, "label": str}           # key equation / law
    step_by_step     {"heading": str, "steps": list[str]}    # max 4 steps, ≤12 words each
    option_highlight {"letter": str, "name": str, "body": str, "color": str}
    cross_out        {"letter": str, "name": str}
    answer_reveal    {"letter": str, "name": str, "explanation": str}
    graph_hint       {"graph_type": str, "description": str} # e.g. velocity-time, bar chart
    summary          {"heading": str, "points": list[str]}   # closing takeaway

  PRESENTATION:
    title_card       {"title": str, "subtitle": str}
    concept_bullets  {"heading": str, "bullets": list[str]}
    key_point        {"heading": str, "body": str}
    summary          {"heading": str, "points": list[str]}

  HUMAN_FACE (future — include narration_text only, visual_data unused):
    subtitle_chunk   {"subtitle": str}
"""

import os
import json
import anthropic
from groq import Groq
from pydantic import BaseModel
from typing import Literal, Any


# ── Schema ────────────────────────────────────────────────────────────────────

class Scene(BaseModel):
    narration_text: str
    visual_type: Literal[
        "title_card",
        "concept_bullets",
        "mcq_layout",
        "formula_display",
        "step_by_step",
        "option_highlight",
        "cross_out",
        "answer_reveal",
        "graph_hint",
        "summary",
        # presentation
        "key_point",
        # human_face (future)
        "subtitle_chunk",
    ]
    visual_data: dict[str, Any]


class DirectorOutput(BaseModel):
    render_mode: Literal["manim", "presentation", "human_face"]
    scenes: list[Scene]


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the Director for EaseToLearn, an AI-powered video lesson platform for Indian competitive exams.

You receive extracted lesson content and produce two things:
  1. render_mode — which video engine to use
  2. scenes — the ordered teaching script

━━━ RENDER MODE RULES ━━━

Choose "manim" when:
  - Subject is maths or physics (ALWAYS manim — formulas and graphs need animation)
  - Medical MCQ (FMGE) — visual option elimination is very effective
  - Chemistry with atomic/molecular diagrams
  - Any content with formulas, graphs, or step-by-step calculations

Choose "presentation" when:
  - English grammar rules (text-heavy, examples-driven)
  - UPSC/GS conceptual explanations (no formulas)
  - MBA/case study reasoning
  - Simple concept explanations with no math

Choose "human_face" when:
  - Caller explicitly requests conversational mode (rarely used now)

DEFAULT: if unsure, always choose "manim". It is the platform's primary mode.

━━━ SCENE RULES BY RENDER MODE ━━━

MANIM SCENES (8–12 scenes):
  - Always start with: title_card → concept_bullets (or formula_display for math)
  - For MCQ: mcq_layout (draws all 4 boxes) → option_highlight on options → cross_out wrong ones → answer_reveal
  - For numerical: formula_display → step_by_step (max 4 steps) → summary
  - For concept: concept_bullets → key supporting facts → summary
  - Use graph_hint whenever a graph/chart would genuinely help (velocity-time, pie chart, etc.)
  - End with summary for concept/numerical; answer_reveal for MCQ

PRESENTATION SCENES (5–8 scenes):
  - title_card → concept_bullets → key_point scenes → summary
  - Keep it simple, no complex visuals

━━━ NARRATION RULES ━━━
  - Speak like a confident teacher, not a textbook
  - 1–3 sentences per scene
  - Build tension before the answer/reveal
  - Use "we", "let's", "notice that" — conversational and engaging
  - For MCQ: make students think before revealing the answer

━━━ VISUAL DATA RULES ━━━
  - mcq_layout: {"options": {"A": "string", "B": "string", "C": "string", "D": "string"}}
  - option_highlight: {"letter": "A", "verdict": "neutral", "reason": "why this option matters"}
  - concept_bullets / summary: max 3 bullets/points, each under 8 words
  - step_by_step: max 4 steps, each under 12 words
  - option colors: "#FF6B6B" wrong/unlikely, "#4ECDC4" correct, "#FFFFFF" neutral/unknown
  - formula: write in plain text (e.g. "v = u + at", "integral of ln(x) dx")
  - graph_type examples: "velocity_time", "bar_chart", "number_line", "venn_diagram"

OUTPUT: Return valid JSON only. No extra text."""


# ── Director ──────────────────────────────────────────────────────────────────

def run_director(parsed_facts: dict) -> DirectorOutput:
    """
    Call Claude Opus to decide render mode and generate teaching scenes.

    Args:
        parsed_facts: output from html_parser.parse_tony_html()

    Returns:
        DirectorOutput with render_mode and scenes list
    """
    # client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    user_message = _build_prompt(parsed_facts)
    # response = client.messages.parse(
    #     model="claude-opus-4-6",
    #     max_tokens=4000,
    #     thinking={"type": "adaptive"},
    #     system=SYSTEM_PROMPT,
    #     messages=[{"role": "user", "content": user_message}],
    #     output_format=DirectorOutput,
    # )
    # return response.parsed_output

    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    
    system_prompt_with_schema = SYSTEM_PROMPT + "\n\nCRITICAL: Output valid JSON exactly matching this schema:\n" + json.dumps(DirectorOutput.model_json_schema(), indent=2)
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt_with_schema},
            {"role": "user", "content": user_message}
        ],
        response_format={"type": "json_object"}
    )
    
    return DirectorOutput.model_validate_json(response.choices[0].message.content)


def _build_prompt(facts: dict) -> str:
    """Build the user message from parsed facts."""
    lines = [
        f"TOPIC: {facts['topic']}",
        f"SUBJECT: {facts['subject']}",
        f"CONTENT TYPE: {facts['content_type']}",
        "",
        f"CONCEPT:\n{facts['concept']}",
    ]

    if facts["content_type"] == "mcq" and facts.get("options"):
        lines.append("\nOPTIONS:")
        for letter, data in sorted(facts["options"].items()):
            lines.append(f"  {letter}. {data['name']}: {data['explanation']}")
        lines.append(
            f"\nCORRECT ANSWER: {facts.get('correct_answer', '')}. "
            f"{facts.get('correct_answer_name', '')}"
        )

    elif facts["content_type"] == "numerical":
        if facts.get("formula"):
            lines.append(f"\nKEY FORMULA: {facts['formula']}")
        if facts.get("steps"):
            lines.append("\nSOLUTION STEPS:")
            for i, step in enumerate(facts["steps"], 1):
                lines.append(f"  {i}. {step}")
        if facts.get("final_answer"):
            lines.append(f"\nFINAL ANSWER: {facts['final_answer']}")

    elif facts["content_type"] in ("concept", "case_study"):
        if facts.get("key_points"):
            lines.append("\nKEY POINTS:")
            for kp in facts["key_points"][:5]:
                lines.append(f"  • {kp}")
        if facts.get("final_answer"):
            lines.append(f"\nCONCLUSION: {facts['final_answer']}")

    if facts.get("sections"):
        extra = {
            k: v for k, v in facts["sections"].items()
            if k.lower() not in ["concept explanation", "option analysis",
                                  "citations", "final answer", "conclusion"]
        }
        if extra:
            lines.append("\nADDITIONAL SECTIONS:")
            for heading, body in list(extra.items())[:3]:
                lines.append(f"  [{heading}]: {body[:200]}")

    lines.append("\nWrite the render_mode and teaching scenes now.")
    return "\n".join(lines)


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from html_parser import parse_tony_html

    path = sys.argv[1] if len(sys.argv) > 1 else "bpf_source.html"
    topic = sys.argv[2] if len(sys.argv) > 2 else path.replace(".html", "").replace("_", " ").title()

    with open(path) as f:
        raw = f.read()

    if path.endswith(".txt"):
        html = f"<html><body><p>{raw}</p></body></html>"
    else:
        html = raw

    facts = parse_tony_html(html, topic_hint=topic)
    print(f"\n📋 Subject: {facts['subject']} | Type: {facts['content_type']}")

    print("🎬 Running Director Agent (Claude Opus)...\n")
    output = run_director(facts)

    print(f"🎥 Render Mode: {output.render_mode.upper()}")
    print(f"📽  Scenes: {len(output.scenes)}\n")

    for i, scene in enumerate(output.scenes, 1):
        print(f"Scene {i:02d} [{scene.visual_type}]")
        print(f"  Narration : {scene.narration_text}")
        print(f"  Data      : {json.dumps(scene.visual_data)}")
        print()
