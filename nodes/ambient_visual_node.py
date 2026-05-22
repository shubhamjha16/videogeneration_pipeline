import os
import json
import base64
import re
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from autonomous_graph import TonyState
from llm_factory import LLMFactory
from openai import OpenAI
import config
from cost_tracker import LedgerManager

def ambient_visual_node(state: "TonyState") -> "TonyState":
    from autonomous_graph import get_job_dir
    render_mode = state.get("render_mode", "")
    if render_mode != "presentation":
        print(f"Ambient Visual Node: Skipping for {render_mode} path.")
        return state

    overrides = state.get("overrides", {}) or {}
    if overrides.get("enable_ambient") is False:
        print(f"Ambient Visual Node: Skipping — operator set enable_ambient=False")
        state["ambient_assets"] = {"atmospheric": [], "accents": []}
        return state

    topic = state.get("topic", "general")
    parsed_facts = state.get("parsed_facts", {})
    if not isinstance(parsed_facts, dict):
        parsed_facts = {}
        
    subject_hint = parsed_facts.get("subject", "general")
    content_type = parsed_facts.get("content_type", "concept")
    job_id = state.get("job_id", "unknown")

    META_PROMPT = f'''You are an art director for an educational video on the topic: "{topic}".

Subject area (context only, do not rely on it): {subject_hint}
Content type: {content_type}

Your job: write 5 DALL-E 3 image prompts that will be used as ambient visuals in this video.

TIER 1 — ATMOSPHERIC (2 prompts):
PURPOSE: Environment/Context. These will be used as faded background layers (10-12% opacity).
INSTRUCTION: Prompts MUST focus on a scattered collection of peripheral objects or a broad scene related to the topic. Do NOT focus on the primary subject of the video yet. For example, if the topic is "The Human Heart", Tier 1 should be about scattered medical tools, EKG lines, or blood vessels—NOT the heart itself. Composition must leave breathing space in the center for text overlay. Wide composition (16:9).

TIER 2 — ACCENT (3 prompts):
PURPOSE: Focal Point. These will be used as sharp corner illustrations (full opacity).
INSTRUCTION: Each prompt MUST focus on the primary subject element of the topic, isolated and centered. For "The Human Heart", these prompts should finally describe the heart itself or its specific components (valves, ventricles). Square composition (1:1).

CRITICAL STYLE RULES — every prompt MUST end with this exact phrase:
"High-fidelity textbook illustration, professional clinical and academic diagram style, sharp detail, rich vibrant colors, high resolution, clean educational graphic, wowed aesthetic. No watermarks."

Each prompt should be 2-3 sentences. Focus on WHAT to draw (specific objects, scenes, elements relevant to the topic) — the style rule above handles HOW.

Return ONLY valid JSON in this exact format, no markdown fences:
{{
  "atmospheric": [
    "prompt 1 here",
    "prompt 2 here"
  ],
  "accents": [
    "prompt 1 here",
    "prompt 2 here", 
    "prompt 3 here"
  ]
}}'''

    messages = [{"role": "user", "content": META_PROMPT}]
    prompts_data = {"atmospheric": [], "accents": []}
    
    try:
        llm_response = LLMFactory.get_completion(
            messages=messages,
            json_mode=True,
            include_usage=False,
            job_id=job_id
        )
        
        if isinstance(llm_response, str):
            cleaned = re.sub(r'```(?:json)?\s*(.*?)\s*```', r'\1', llm_response, flags=re.DOTALL)
            prompts_data = json.loads(cleaned)
        else:
            prompts_data = llm_response
            
    except Exception as e:
        print(f"⚠️ Ambient Visual Node: Failed to generate/parse LLM prompts: {e}")
        state["ambient_assets"] = {"atmospheric": [], "accents": []}
        return state

    atmospheric_prompts = prompts_data.get("atmospheric", [])
    accent_prompts = prompts_data.get("accents", [])

    api_key = config.OPENAI_API_KEY
    if not api_key:
        print("⚠️ OPENAI_API_KEY not set in config / environment. Skipping ambient visual generation.")
        state["ambient_assets"] = {"atmospheric": [], "accents": [], "generated_prompts": prompts_data}
        return state
    from openai import Timeout
    client = OpenAI(
        api_key=api_key,
        timeout=Timeout(connect=5.0, read=300.0, write=5.0, pool=5.0)
    )
    
    ambient_dir = os.path.join(get_job_dir(state), "ambient")
    os.makedirs(ambient_dir, exist_ok=True)
    
    successful_atmospheric = []
    successful_accents = []
    
    print(f"🎨 Ambient Visual Node: Generating images for '{topic}'...")

    for i, prompt in enumerate(atmospheric_prompts[:2]):
        try:
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1792x1024",
                quality="standard",
                n=1,
                response_format="b64_json"
            )
            if response.data:
                output_path = os.path.join(ambient_dir, f"atmospheric_{i}.png")
                image_bytes = base64.b64decode(response.data[0].b64_json)
                with open(output_path, "wb") as f:
                    f.write(image_bytes)
                successful_atmospheric.append(os.path.abspath(output_path))
                try:
                    LedgerManager.record_dalle_call(job_id, cost=0.08)
                except Exception as e:
                    print(f"⚠️ [ambient_visual_node] Failed to record atmospheric DALL-E cost: {e}")
        except Exception as e:
            print(f"⚠️ Failed to generate atmospheric_{i}.png: {e}")

    for i, prompt in enumerate(accent_prompts[:3]):
        try:
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
                response_format="b64_json"
            )
            if response.data:
                output_path = os.path.join(ambient_dir, f"accent_{i}.png")
                image_bytes = base64.b64decode(response.data[0].b64_json)
                with open(output_path, "wb") as f:
                    f.write(image_bytes)
                successful_accents.append(os.path.abspath(output_path))
                try:
                    LedgerManager.record_dalle_call(job_id, cost=0.04)
                except Exception as e:
                    print(f"⚠️ [ambient_visual_node] Failed to record accent DALL-E cost: {e}")
        except Exception as e:
            print(f"⚠️ Failed to generate accent_{i}.png: {e}")

    state["ambient_assets"] = {
        "atmospheric": successful_atmospheric,
        "accents": successful_accents,
        "generated_prompts": prompts_data
    }
    
    print(f"Ambient Visual Node: Generated {len(successful_atmospheric)}/2 atmospheric and {len(successful_accents)}/3 accent images for topic '{topic}'")
    
    return state
