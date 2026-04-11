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
  explainer    - Narrative-driven video with cinematic B-roll/generative clips.
                 Best for: deep-dive conceptual metaphors, complex system overviews.
  user_generated_video - Talking head (HeyGen) + Insta Reels kinetic subtitles (word-by-word highlight).
                 Best for: direct messages, short updates, tutors talking to students.

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
    concept_image    {"description": str}                    # for AI artist (Gemini Vision)
    image_arrow      {"region": str, "label": str}           # points to anatomical area
    summary          {"heading": str, "points": list[str]}   # closing takeaway

  EXPLAINER:
    title_card       {"title": str, "subtitle": str}
    b_roll_clip      {"prompt": str, "metaphor": str} # describe a cinematic visual (e.g. "falling dominoes", "high speed train")
    summary          {"heading": str, "points": list[str]}

  USER_GENERATED_VIDEO:
    subtitle_chunk   {"subtitle": str} # the text to be highlighted word-by-word

  EXPLAINER (Enhanced):
    counting_metaphor {"item_name": str, "count": int, "style": "3D stylized"} # 6 bananas logic
    generative_video  {"prompt": str, "metaphor": str} # 2s Higgsfield clips
"""

import os
import json
import anthropic
from groq import Groq
from pydantic import BaseModel
from typing import Literal, Any


# ── Schema ────────────────────────────────────────────────────────────────────

_REQUIRED_FIELDS = {
    "title_card":      {"title": "Lesson", "subtitle": ""},
    "concept_bullets": {"heading": "Key Concepts", "bullets": ["Key point"]},
    "formula_display": {"formula": "x = y", "label": ""},
    "step_by_step":    {"heading": "Solution", "steps": ["Step 1"]},
    "mcq_layout":      {"options": {"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"}},
    "option_highlight": {"letter": "A", "name": "", "body": "", "color": "#FFFFFF"},
    "cross_out":       {"letter": "A", "name": ""},
    "answer_reveal":   {"letter": "A", "name": "", "explanation": ""},
    "graph_hint":      {"graph_type": "generic", "description": "", "highlight": ""},
    "summary":         {"heading": "Key Takeaways", "points": ["Remember this"]},
    "key_point":       {"heading": "Key Point", "body": ""},
    "concept_image":   {"description": ""},
    "image_arrow":     {"region": "center", "label": ""},
    "b_roll_clip":     {"prompt": "Cinematic visual of...", "metaphor": ""},
    "counting_metaphor": {"item_name": "apple", "count": 6, "style": "3D stylized", "background_prompt": "A rustic wooden table in a sunlight kitchen"},
    "generative_video": {"prompt": "Cinematic motion of...", "metaphor": ""},
}


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
        "key_point",
        "subtitle_chunk",
        "concept_image",
        "image_arrow",
        "b_roll_clip",
        "counting_metaphor",
        "generative_video",
    ]
    visual_data: dict[str, Any]

    def model_post_init(self, __context: Any) -> None:
        """Fill in any missing visual_data fields with safe defaults."""
        defaults = _REQUIRED_FIELDS.get(self.visual_type, {})
        for key, default in defaults.items():
            if key not in self.visual_data or self.visual_data[key] is None:
                self.visual_data[key] = default
            # empty string fields — keep as-is, tex() handles them


class DirectorOutput(BaseModel):
    render_mode: Literal["manim", "presentation", "explainer", "user_generated_video"]
    decision_reasoning: str  # Explain why this mode was chosen based on the hierarchy
    scenes: list[Scene]


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the Director for EaseToLearn, an AI-powered video lesson platform for Indian competitive exams.

You receive extracted lesson content and produce two things:
  1. render_mode — which video engine to use
  2. scenes — the ordered teaching script

━━━ COMPUTE-AWARE DECISION ALGORITHM ━━━
Follow this hierarchy in order to maximize educational sense while minimizing compute overcost:

LEVEL 1 (Hard Science/Accuracy) → Use "manim":
  - Subject is Maths, Physics, Biology, or Chemistry.
  - Medical MCQ (FMGE) or any content with anatomical lesions/diagrams.
  - Logic that REQUIRES motion (e.g. "blood flow", "electron movement", "formula derivation").
  - Content with graphs, step-by-step calculations, or complex equations.

LEVEL 2 (High-Impact Deep Dive) → Use "explainer":
  - Abstract conceptual deep-dives (e.g. "The Butterfly Effect", "Vastness of Space").
  - Topics that benefit from Cinematic Metaphors (e.g. falling dominoes, ticking clocks).
  - Storytelling about systems where no specific math/diagram is provided in the text.

LEVEL 3 (Maximum Engagement) → Use "user_generated_video":
  - Personal tutor messages, motivational updates, or short "Reels" style snippets.
  - Conversational content where the face-to-face connection is the primary goal.

LEVEL 4 (Efficiency / Default) → Use "presentation":
  - Factual subjects: UPSC, History, Geography (no complex diagrams), Civic lessons.
  - Humanities: English grammar, Case Studies, Essays, Reasoning.
  - Any factual or purely text-based content where static slides are sufficient.

ECONOMY RULE: If unsure, prefer "presentation" to save compute. Only "upgrade" to Manim/Explainer if the content strictly warrants it.

━━━ SCENE RULES BY RENDER MODE ━━━

MANIM SCENES (8–12 scenes):
  - For MCQ:
      1. title_card
      2. concept_image (anatomical overview)
      3. image_arrow (if anatomical lesion mentioned)
      4. mcq_layout (draws all 4 boxes)
      5. option_highlight (wrong options, color "#FF6B6B")
      6. cross_out (all wrong options, NEVER the correct answer)
      7. answer_reveal (explanation + tick)
  - cross_out rule: if correct answer is A, cross_out B, C, D — never A. Always cross out all wrong options.
  - For numerical: formula_display → graph_hint (if applicable) → step_by_step (max 4 steps) → summary
  - For concept: concept_bullets → graph_hint (if applicable) → key supporting facts → summary
  - Placement Rule: Place `graph_hint` immediately after the first mention of the concept or formula it visualizes. Do not wait until the end of the lesson.
  - End with summary for concept/numerical; answer_reveal for MCQ

PRESENTATION SCENES (5–8 scenes):
  - title_card → concept_bullets → key_point scenes → summary
  - Keep it simple, no complex visuals

EXPLAINER SCENES (6–10 scenes):
  - title_card → series of multimodal scenes → summary
  - Use metaphors! If explaining a chain reaction, use "falling dominoes". 
  - ACADEMIC COUNTING: If the narration mentions a number (e.g. "three atoms" or "six steps"), use counting_metaphor. 
    1. First scene: counting_metaphor with count 1
    2. Final scene: counting_metaphor with target count (e.g. 6)
    3. THEMATIC RELEVANCE: Always provide a `background_prompt` for counting_metaphor. (e.g. if counting atoms, background is "A microscopic view of a vibrant molecular structure"). 
    4. NO PLAIN BACKGROUNDS: Ensure the background prompt provides a "World" for the objects to live in (e.g. "train on tracks", "market table", "blueprint drafting board").
  - MOOD: Each generative_video must have a cinematic prompt (e.g. "Sparks flying in a high-tech lab, 4k ultra realistic, Higgsfield style")

USER_GENERATED_VIDEO (1–4 long scenes):
  - subtitle_chunk scenes only
  - focus on the narration; the visuals will be a single talking head avatar.

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
  - graph_hint: {"graph_type": "string", "description": "MUST include the specific equation and any domain/ranges (e.g. 'Plot y=x^2 from x=4 to x=9 and shade the area'). Never omit the bounds for integrals."}
  - graph_type examples: "velocity_time", "bar_chart", "number_line", "venn_diagram", "function_plot"

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
        correct = facts.get('correct_answer', '')
        wrong_letters = [l for l in ["A", "B", "C", "D"] if l != correct and l in facts.get("options", {})]
        lines.append(
            f"\nCORRECT ANSWER: {correct}. {facts.get('correct_answer_name', '')}"
        )
        lines.append(
            f"WRONG OPTIONS (cross_out these, NEVER cross_out {correct}): {', '.join(wrong_letters)}"
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
