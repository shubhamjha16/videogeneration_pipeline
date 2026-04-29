"""
Step 2: Director Agent (LLM — Gemma 4)

Responsibilities:
  1. Decides the render mode  : manim | presentation | user_generated_video

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
    cross_out        {"letters": list[str]}
    answer_reveal    {"letter": str, "name": str, "explanation": str}
    graph_hint       {"graph_type": str, "description": str} # e.g. velocity-time, bar chart
    annotated_image  {"region": str, "label": str, "bullets": list[str]} # Image on right, text on left, arrow pointing to region
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
import copy
import anthropic
from pydantic import BaseModel
from typing import Literal, Any
from llm_factory import LLMFactory, clean_llm_json


# ── Schema ────────────────────────────────────────────────────────────────────

_REQUIRED_FIELDS = {
    "title_card":      {"title": "Lesson", "subtitle": ""},
    "concept_bullets": {"heading": "Key Concepts", "bullets": ["Key point"]},
    "formula_display": {"formula": "x = y", "label": ""},
    "step_by_step":    {"heading": "Solution", "steps": ["Step 1"]},
    "mcq_layout":      {"options": {"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"}},
    "option_highlight": {"letter": "A", "name": "", "body": "", "color": "#FFFFFF"},
    "cross_out":       {"letters": ["A", "B", "C"]},
    "answer_reveal":   {"letter": "A", "name": "", "explanation": ""},
    "graph_hint":      {"graph_type": "generic", "description": "", "highlight": ""},
    "summary":         {"heading": "Key Takeaways", "points": ["Remember this"]},
    "key_point":       {"heading": "Key Point", "body": ""},
    "annotated_image": {"region": "center_right", "label": "Title", "bullets": ["Fact 1"]},
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
        "annotated_image",
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
                # Copy mutable defaults so scenes never share state.
                self.visual_data[key] = copy.deepcopy(default)
            # empty string fields — keep as-is, tex() handles them


class DirectorOutput(BaseModel):
    render_mode: Literal["manim", "presentation", "explainer", "user_generated_video"]
    decision_reasoning: str  # Explain why this mode was chosen based on the hierarchy
    search_queries: list[str] = [] # If content is sparse, list 1-3 queries to run via SearXNG
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

━━━ MCQ MANDATORY SCENE RULE ━━━
If the content type is "mcq", you MUST include exactly these scenes at the end of your script in this exact order:
  1. "mcq_layout": To show the question and all 4 options.
  2. "option_highlight" (optional): To analyze specific wrong options before elimination.
  3. "cross_out": To eliminate the wrong options one by one.
  4. "answer_reveal": To highlight the correct answer and provide the explanation.
━━━ CONSECUTIVE RULE ━━━
These scenes (1 through 4) MUST be consecutive. Once you call "mcq_layout", you MUST NOT insert other visual types (like formula_display or step_by_step) until after the "answer_reveal" is complete. Explain the logic BEFORE the MCQ block starts or AFTER it ends.
Do NOT skip these scenes if options are provided in the input.

━━━ SEARCH / RESEARCH RULE ━━━
- If the input lesson is thin or lacks specific facts (names, dates, stats), you MUST populate `search_queries` with 1-3 specific search terms. 
- Example: Topic "History of AI" but no dates. Query: ["first artificial intelligence conference date", "early AI pioneers timeline"].
- If you request search, your `scenes` can be a preliminary "stub" — the system will re-run you with the search results.

━━━ SCENE RULES BY RENDER MODE ━━━

MANIM SCENES (8–12 scenes):
  - HYBRID RULE: If the lesson includes a "Concept Explanation" section, you MUST start with 2–4 scenes explaining the background material (using concept_bullets, formula_display, or key_point) before starting the MCQ phase.
  - For MCQ Phase (CONTINUOUS VISUAL FLOW):
      1. title_card (Topic)
      2. annotated_image (anatomical/clinical overview with bullets on left)
      3. CONCEPT TEACHING (Use concept_bullets to reinforce each new fact)
      4. annotated_image (Update image region pointer for the new concept)
      5. mcq_layout (Switch to MCQ focus)
      7. option_highlight (wrong options, color "#FF6B6B")
      8. cross_out (Scrub wrong options)
      9. answer_reveal (explanation + final diagram summarizing the answer)
  - PEDAGOGICAL INTEGRITY: NEVER use generic placeholders like "Option A" or "Option B" if real names (e.g., "Cortical contusion") are available in the parsed_facts. You MUST use the exact names from the facts in your `visual_data`.
  - ANSWER LOCK: The "correct_answer" letter and "explanation" in the answer_reveal scene MUST match the ground truth provided in the parsed_facts. Do not hallucinate a different answer.
  - cross_out rule (SINGLE SCENE): You MUST provide exactly ONE "cross_out" scene that includes all incorrect letters in a single list (e.g., {"letters": ["A", "B", "C"]}). NEVER split cross-outs across multiple scenes.
  - For numerical: formula_display → graph_hint (if applicable) → step_by_step (max 4 steps) → summary
  - For concept: concept_bullets → graph_hint (if applicable) → key supporting facts → summary
  - PEDAGOGICAL IMPORTANCE (CRITICAL):
      1. If a 'parsed_facts' section contains '###', use that text as the PRIMARY HEADLINE in that scene's `title` or `key_point`.
      2. If text contains '**word**', preserve those asterisks in the `visual_data`. The Architect will translate them into highlighted text.
      3. Use these markers to decide which part of the narration should be emphasized.
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

━━━ NARRATION RULES (THE 3B1B STANDARD) ━━━
  - SYNC-FIRST RULE: In scenes where an element is highlighted (option_highlight, option_arrow, image_arrow), your narration MUST begin by identifying that specific element. (e.g., "Looking at Option B...", "Observe this region..."). This ensures the Pointer and the Speech land at the exact same moment.
  - CONCISE ELEGANCE: Favor short, powerful sentences. The 3b1b style thrives on clarity, not wordiness.
  - GROUND TRUTH OATH: Use the PERSISTENT KNOWLEDGE BASE (GROUND TRUTH) as your primary source of facts. If a KB fact contradicts the input, the KB WINS.
  - Build tension before an answer reveal. Use "we", "let's", "notice that" — conversational and engaging.
  - MCQ ALIGNMENT: During "option_highlight" or "cross_out" scenes, ONLY discuss the specific options being visually focused on. Do NOT mention the final correct answer until the "answer_reveal" scene.

━━━ VISUAL DATA RULES (HIGH FIDELITY) ━━━
  - SMART WRAPPING: You can now provide up to 100 characters for bullet points or solution steps. The engine will automatically wrap these into a beautiful 3b1b-style layout.
  - formula: Use plain text or LaTeX (e.g. "e = mc^2").
  - graph_hint: MUST include specific equations and domain/ranges (e.g. 'Plot y=sin(x) from -pi to pi').
  - option_highlight: {"letter": "A", "verdict": "wrong", "reason": "why this option is incorrect"}.

OUTPUT: Return valid JSON only. No extra text."""


# ── Director ──────────────────────────────────────────────────────────────────

def run_director(parsed_facts: dict, search_results: list[dict] = None, knowledge_base: dict = None) -> tuple[DirectorOutput, dict]:
    """
    Call Groq (Llama 3.3) to decide render mode and generate teaching scenes.

    Args:
        parsed_facts   : output from html_parser.parse_tony_html()
        search_results : (optional) list of relevant snippets from SearXNG
        knowledge_base : (optional) distilled verified facts from persistent storage

    Returns:
        DirectorOutput with render_mode and scenes list
    """
    from llm_factory import clean_llm_json
    
    user_message = _build_prompt(parsed_facts, search_results, knowledge_base)
    
    # INDUSTRIAL OPTIMIZATION: Gemma 4/Local models perform 30% better with specific structural prototypes
    # than with raw JSON Schema definitions. 
    schema_hint = """
CRITICAL: You MUST output valid JSON only.
Structure:
{
  "render_mode": "manim",
  "decision_reasoning": "Reason why you chose this mode...",
  "search_queries": [],
  "scenes": [
    {
      "visual_type": "title_card",
      "visual_data": {"title": "Topic", "subtitle": "Description"},
      "narration_text": "Hello, today we talk about..."
    },
    {
      "visual_type": "annotated_image",
      "visual_data": {"label": "Internal Iliac Artery", "region": "center_left", "bullets": ["Anterior division: Obturator, Uterine", "Posterior division: Iliolumbar, Lateral sacral"]},
      "narration_text": "Let us look at the branches of the internal iliac artery..."
    },
    {
      "visual_type": "annotated_image",
      "visual_data": {"label": "Convex Lens Ray Diagram", "region": "center_right", "bullets": ["Parallel rays converge at focal point", "Image is real and inverted beyond 2F"]},
      "narration_text": "Observe how parallel rays pass through the lens and meet at the focal point..."
    }
  ]
}

IMPORTANT: Use "annotated_image" whenever you need to show an image with explanatory text. It creates a split layout (image right, bullets left, arrow pointing to region). Do NOT use "concept_image" or "image_arrow" — they are deprecated.
"""
    system_prompt_with_hint = SYSTEM_PROMPT + "\n\n" + schema_hint
    
    content, usage = LLMFactory.get_completion(
        messages=[{"role": "user", "content": user_message}],
        system_prompt=system_prompt_with_hint,
        json_mode=True,
        include_usage=True
    )
    
    try:
        data = clean_llm_json(content)
        
        # Industrial Guard: If the model returned a 'DirectorOutput' or similar wrapper, unwrap it
        if isinstance(data, dict):
            # Gemma/Llama often nest inside a key named after the requested object
            if "DirectorOutput" in data: data = data["DirectorOutput"]
            elif "output" in data: data = data["output"]
            elif "json" in data: data = data["json"]
            
            # INDUSTRIAL SCRUBBER: Ensure visual_data is always a dict
            if "scenes" in data and isinstance(data["scenes"], list):
                for scene in data["scenes"]:
                    if isinstance(scene, dict) and "visual_data" in scene:
                        if isinstance(scene["visual_data"], list):
                            # LLM hallucinated a list for visual_data, wrap it in a dict or take first item
                            if len(scene["visual_data"]) > 0 and isinstance(scene["visual_data"][0], dict):
                                scene["visual_data"] = scene["visual_data"][0]
                            else:
                                scene["visual_data"] = {"data": scene["visual_data"]}
        
        # Fallback for required fields (Industrial Resilience)
        if not data.get("render_mode"): data["render_mode"] = "manim"
        def _ensure_mcq_continuity(scenes):
            """Defense in Depth: Group MCQ scenes into a contiguous atomic block."""
            mcq_types = {"mcq_layout", "option_highlight", "cross_out", "answer_reveal"}
            mcq_scenes = [s for s in scenes if s.visual_type in mcq_types]
            other_scenes = [s for s in scenes if s.visual_type not in mcq_types]
            
            if not mcq_scenes:
                return scenes
            
            # The atomic block always moves to the end to ensure the question is the final takeaway
            return other_scenes + mcq_scenes

        data["scenes"] = _ensure_mcq_continuity(data.get("scenes", []))
        response = DirectorOutput(**data)
        
        # INDUSTRIAL OVERRIDE: Programmatic Label Injection
        try:
            import re
            def sanitize(txt):
                if not txt: return ""
                # Strip Markdown headers (###), bolding (**), and bullets (-)
                t = re.sub(r'^(#+\s*|\*+|-\s*)', '', str(txt)).strip()
                t = re.sub(r'\*+', '', t)
                # Avoid literal dashes
                return t if t != "-" else ""

            real_options = parsed_facts.get("options", {})
            if isinstance(real_options, dict):
                for scene in response.scenes:
                    if scene.visual_type == "mcq_layout":
                        for letter, real_data in real_options.items():
                            if "options" not in scene.visual_data:
                                scene.visual_data["options"] = {}
                            
                            # Handle both dict and string forms of real_data
                            raw_text = real_data.get("name") if isinstance(real_data, dict) else str(real_data)
                            option_text = sanitize(raw_text)
                            scene.visual_data["options"][letter] = option_text or f"Option {letter}"
                    
                    elif scene.visual_type in ["option_highlight", "answer_reveal", "cross_out", "option_arrow"]:
                        letter = str(scene.visual_data.get("letter", "A")).upper()
                        if letter in real_options:
                            real_data = real_options[letter]
                            raw_text = real_data.get("name", "") if isinstance(real_data, dict) else str(real_data)
                            scene.visual_data["name"] = sanitize(raw_text)
                            if scene.visual_type == "answer_reveal":
                                 # If LLM didn't provide a good explanation, use the one from parsed_facts
                                 if not scene.visual_data.get("explanation") and isinstance(real_data, dict):
                                     scene.visual_data["explanation"] = real_data.get("explanation", "")
        except Exception as e:
            print(f"   ⚠️ Label Injection failed: {e}")

        return response, usage
        
    except Exception as e:
        print(f"❌ Director Parse Error: {e}")
        # INDUSTRIAL FALLBACK: Return a basic manim plan rather than crashing the pipeline
        fallback_plan = {
            "render_mode": "manim",
            "decision_reasoning": "Parse failure fallback. System auto-generated generic title.",
            "scenes": [
                {
                    "visual_type": "title_card",
                    "visual_data": {"title": parsed_facts.get("topic", "Chemistry Masterclass"), "subtitle": "Introduction"},
                    "narration_text": f"Today we are exploring {parsed_facts.get('topic', 'this important topic')}. Let's dive in."
                }
            ]
        }
        return DirectorOutput(**fallback_plan), {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def _build_prompt(facts: dict, search_results: list[dict] = None, knowledge_base: dict = None) -> str:
    """Build the user message from parsed facts, research context, and knowledge base."""
    topic = facts.get("topic", "Untitled Lesson")
    subject = facts.get("subject", "unknown")
    content_type = facts.get("content_type", "concept")
    concept = facts.get("concept") or ""

    lines = [
        f"TOPIC: {topic}",
        f"SUBJECT: {subject}",
        f"CONTENT TYPE: {content_type}",
        "",
    ]

    if knowledge_base:
        lines.append("━━━ PERSISTENT KNOWLEDGE BASE (GROUND TRUTH) ━━━")
        lines.append("Use these verified facts as your primary source of truth to prevent hallucination.")
        lines.append(json.dumps(knowledge_base, indent=2))
        lines.append("")

    lines.append("━━━ CORE CURRICULUM (INPUT) ━━━")
    lines.append(concept)
    lines.append("")
    
    if search_results:
        lines.append("━━━ ENRICHED SEARCH CONTEXT (WEB RESEARCH) ━━━")
        lines.append("Use these facts to improve the depth and accuracy of the lesson.")
        for res in search_results[:5]:
            lines.append(f"- {res['title']} ({res['url']}):")
            lines.append(f"  {res['content']}")
        lines.append("")

    if content_type == "mcq" and facts.get("options"):
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

    elif content_type == "numerical":
        if facts.get("formula"):
            lines.append(f"\nKEY FORMULA: {facts['formula']}")
        if facts.get("steps"):
            lines.append("\nSOLUTION STEPS:")
            for i, step in enumerate(facts["steps"], 1):
                lines.append(f"  {i}. {step}")
        if facts.get("final_answer"):
            lines.append(f"\nFINAL ANSWER: {facts['final_answer']}")

    elif content_type in ("concept", "case_study"):
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
