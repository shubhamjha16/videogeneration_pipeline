import os
import time
import json
import re
from llm_factory import LLMFactory, clean_llm_json
from explainer_slides_generator import generate_explainer_slides_video

# ── SYSTEM PROMPTS FOR MARKETING AGENTS ────────────────────────────────────────

_MARKETING_PLANNER_PROMPT = """You are a World-Class Direct-Response Marketing Copywriter and Video Script Director.
Your task is to write a highly persuasive, benefits-driven, and high-impact whiteboard marketing slide sequence explaining the topic.
The slide sequence MUST grab the viewer's attention immediately, highlight key value propositions or metrics, show a punchy visual metaphor for each slide, and end with a powerful Call to Action (CTA).

Slide Design Guidance:
- Focus on customer benefits (e.g., "Save 10x time", "Scale instantly") rather than dry technical specs.
- Use visual metaphors and concrete objects that DALL-E can draw sequentially (e.g., "rocket ship taking off", "magnifying glass over dollar bills").
- Provide a clear, bold slide title, a short punchy subtitle, and exactly 2-4 benefit-oriented bullets.
- Narrations should be active, energetic, persuasive, and directly address the user (approx 20-30 seconds per slide).
- For slides presenting questions or choices, utilize the high-contrast PIL MCQ layout ("mcq_layout", "option_highlight", "cross_out", "answer_reveal").
- End with a final slide having a strong, compelling Call to Action (CTA) asking the user to sign up, buy, or download.

{feedback_section}

You must write a list of scenes in JSON format. Each scene has:
- "visual_type": "title_card" | "concept_bullets" | "mcq_layout" | "formula_display" | "formula_derivation" | "formula_step_list" | "step_by_step" | "option_highlight" | "cross_out" | "answer_reveal" | "summary" | "key_point"
- "visual_data": A dictionary with visual details.
  - For standard slides, include "title", "subtitle", "bullets" (list of strings), and "objects" (list of visual doodle icons to draw).
  - For MCQ slides, include "question", "options" (A, B, C, D), "letter" (correct letter key), and "explanation".
- "narration_text": Punchy copywriting script to be spoken.
- "tony_pose": standing_point_up | thinking | desk_happy | explaining | victory | excited | confused (choose the perfect mood to overlay on PIL/MCQ slides).

Output format MUST be strictly JSON like this:
{{
  "scenes": [
    {{
      "visual_type": "title_card",
      "visual_data": {{
        "title": "Unleash The Future",
        "subtitle": "No Coding Required",
        "bullets": ["Instant setup", "Zero server overhead"],
        "objects": ["gear sketch", "sparkles"]
      }},
      "narration_text": "Imagine a world where you can deploy software without writing a single line of code. Let's make it a reality.",
      "tony_pose": "excited"
    }}
  ]
}}
"""

_MARKETING_CRITIC_PROMPT = """You are a highly analytical, strict Direct-Response Marketing Critic.
Your job is to strictly review the proposed whiteboard marketing slide plan.
To pass your review, the plan MUST meet the following Direct-Response Copywriting standards:
1. Is it highly persuasive and benefit-driven? (Reject if it reads like a dry academic list of facts/features).
2. Is the tone active, energetic, and engaging?
3. Is there a powerful, clear Call to Action (CTA) at the end? (Reject if it just fades out without asking the user to act).
4. Are the visual objects (doodles) punchy and metaphorical? (Reject if objects are generic or missing).

Analyze the slides carefully. Give a critique and a score from 1 to 10.
If the plan scores less than 8, or lacks a strong CTA, or is too dry/academic, set "approved" to false.

Output format MUST be strictly JSON like this:
{{
  "approved": true or false,
  "feedback": "detailed critique explaining exactly what is dry, what to rewrite, or how to strengthen the CTA",
  "score": 1-10
}}
"""


# ── LANGGRAPH PIPELINE NODE ───────────────────────────────────────────────────

def explainer_slides_marketing_node(state: dict) -> dict:
    """
    Explainer Slides Marketing Node
    Runs a closed-loop Planner + Critic agent cycle powered by ChatGPT (GPT-4o)
    to plan punchy, benefits-driven marketing slides and render them using whiteboards.
    """
    import copy
    start_t = time.time()
    state = copy.deepcopy(state)
    
    topic = state.get("topic", "Product Overview")
    print(f"🎬 [Marketing Explainer] Starting ChatGPT-powered Planner + Critic loop for: {topic}")
    
    # Configure job directory
    from autonomous_graph import get_topic_safe
    job_prefix = f"job_{state.get('job_id', get_topic_safe(state))}"
    job_dir = os.path.join("output", job_prefix)
    os.makedirs(job_dir, exist_ok=True)
    
    # Loop parameters
    max_attempts = 3
    feedback = ""
    rejections = []
    scenes = []
    approved = False
    
    for attempt in range(max_attempts):
        print(f"   [attempt {attempt + 1}] Invoking ChatGPT Marketing Planner...")
        
        # Build feedback history section
        feedback_section = ""
        if feedback:
            feedback_section = f"\n⚠️ PREVIOUS ATTEMPT WAS REJECTED. Fix these specific copy issues:\n{feedback}\n"
            
        planner_prompt = _MARKETING_PLANNER_PROMPT.format(feedback_section=feedback_section)
        
        user_msg = f"Topic: {topic}\n"
        facts = state.get("parsed_facts")
        if facts:
            user_msg += f"Facts/Details:\n{json.dumps(facts, indent=2)}\n"
            
        try:
            # Force ChatGPT / OpenAI gpt-4o for premium copy outputs
            planner_response = LLMFactory.get_completion(
                messages=[{"role": "user", "content": user_msg}],
                system_prompt=planner_prompt,
                provider_override="openai",
                model_override="gpt-4o",
                json_mode=True,
                temperature=0.7,
                job_id=state.get("job_id")
            )
            data = clean_llm_json(planner_response)
            scenes = data.get("scenes", [])
            print(f"   Planned {len(scenes)} scenes.")
        except Exception as e:
            print(f"   ⚠️ Marketing Planner failed: {e}. Falling back to default state scenes.")
            scenes = state.get("scenes") or []
            
        if not scenes:
            print("   ⚠️ No scenes planned. Falling back directly.")
            scenes = state.get("scenes") or []
            break
            
        # Invoke Marketing Critic Agent
        print(f"   [attempt {attempt + 1}] Invoking ChatGPT Marketing Critic...")
        try:
            critic_response = LLMFactory.get_completion(
                messages=[{"role": "user", "content": f"Proposed Slides:\n{json.dumps(scenes, indent=2)}"}],
                system_prompt=_MARKETING_CRITIC_PROMPT,
                provider_override="openai",
                model_override="gpt-4o",
                json_mode=True,
                temperature=0.0,
                job_id=state.get("job_id")
            )
            eval_data = clean_llm_json(critic_response)
            approved = eval_data.get("approved", True)
            feedback = eval_data.get("feedback", "")
            score = eval_data.get("score", 7)
            print(f"   Critic Evaluation Score: {score}/10 | {'✅ Approved' if approved else '❌ Rejected'}")
            
            if approved:
                break
            else:
                print(f"   Critic Feedback: {feedback}")
                rejections.append({
                    "plan": json.dumps(scenes[:2], indent=2),
                    "feedback": feedback,
                    "score": score
                })
        except Exception as e:
            print(f"   ⚠️ Marketing Critic failed ({e}). Auto-approving to prevent block.")
            approved = True
            break
            
    # Save the selected scenes back to state for subtitles / fusion compatibility
    state["scenes"] = scenes
    
    # ─── Render Final Whiteboard Video ────────────────────────
    print("   🎞️ Synthesizing and rendering Whiteboard Marketing Slides...")
    try:
        video_path, metrics = generate_explainer_slides_video(
            scenes=scenes,
            output_dir=job_dir,
            topic=topic,
            job_id=state.get("job_id"),
            use_elevenlabs=state.get("use_elevenlabs", True),
            subject=state.get("parsed_facts", {}).get("subject", "default"),
            avatar_type=state.get("avatar_type", "tony_cartoon"),
            with_avatar=state.get("with_avatar", True)
        )
        
        state["output_path"] = os.path.abspath(video_path)
        
        # Log Ledger Telemetry
        state["ledger"] = state.get("ledger", {})
        state["ledger"]["elevenlabs_chars"] = state["ledger"].get("elevenlabs_chars", 0) + metrics.get("elevenlabs_chars", 0)
        state["ledger"]["dalle_calls"] = state["ledger"].get("dalle_calls", 0) + metrics.get("dalle_calls", 0)
        
        print(f"✅ Premium Marketing Slides Video compiled successfully: {video_path}")
        
    except Exception as e:
        print(f"❌ Marketing Slides Video compilation failed: {e}")
        raise e
        
    try:
        from autonomous_graph import _log_progress
        _log_progress(state, "EXPLAINER_SLIDES_MARKETING", "Structured marketing slide production lifecycle complete.", duration=time.time() - start_t)
    except Exception:
        pass
        
    return state
