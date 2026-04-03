import os
import requests
import json
from typing import TypedDict, List, Optional, Annotated
from langgraph.graph import StateGraph, END
import subprocess
from langchain_anthropic import ChatAnthropic # Import Claude

# The Unified Ignition: Gemini 2.0 Flash
GEMINI_KEY = "AIzaSyBLPm8Wgg5xOsNd95fOdRT6q_5vjavnzvg"

def model_invoke(prompt: str) -> str:
    """Unified Orchestration: Gemini 2.0 Flash REST."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        raise Exception(f"Gemini API Error: {response.text}")
    return response.json()['candidates'][0]['content']['parts'][0]['text']

# Define the state that Tony's team will manage

# Define the state that Tony's team will manage
class TonyState(TypedDict):
    raw_input: str
    topic: str
    lesson_html: Optional[str]
    script_plan: Optional[str]
    image_prompt: Optional[str] # New: The prompt for Imagen
    image_path: Optional[str]   # New: Path to generated diagram
    manim_code: Optional[str]
    image_prompts: List[str]
    rendering_errors: Optional[str]
    output_path: Optional[str]
    attempt_count: int

import config

def director_node(state: TonyState) -> TonyState:
    """🎬 Tony [Director]: Content Synthesis & Pedagogical Planning."""
    print(f"🎬 Tony [Director]: Synthesizing high-fidelity content for {state['topic']}...")
    
    # Phase 1: Generate the HTML Lesson
    html_prompt = f"Topic: {state['raw_input']}\nGenerate a professional medical HTML lesson. Output ONLY the <html>. No conversational text."
    state["lesson_html"] = model_invoke(html_prompt)
    
    # Phase 2: Generate the Manim Script Plan
    script_prompt = f"Lesson: {state['lesson_html']}\nPlan a 3-part Manim script. Output ONLY a JSON string with 'intro', 'investigation', 'reveal', and 'image_description' keys."
    plan_text = model_invoke(script_prompt)
    state["script_plan"] = plan_text
    
    # Phase 3: Extract Image Description for Vision Node
    try:
        plan_json = json.loads(plan_text.replace("```json", "").replace("```", "").strip())
        state["image_prompt"] = plan_json.get("image_description", f"Cinematic anatomical diagram of {state['topic']}, modern dark medical aesthetic.")
    except:
        state["image_prompt"] = f"Cinematic anatomical diagram of {state['topic']}, modern dark medical aesthetic."
        
    return state

def vision_node(state: TonyState) -> TonyState:
    """📸 Tony [Vision]: AI Diagram Synthesis."""
    print(f"📸 Tony [Vision]: Synthesizing clinical diagram for {state['topic']}...")
    # Placeholder for now, but configured to use a unique filename
    # In a full production env, this would call Imagen 3 REST API.
    state["image_path"] = f"{state['topic']}_diagram.png"
    # Fallback to existing or placeholder
    if not os.path.exists(state["image_path"]):
         os.system(f"cp bpf_diagram.png {state['image_path']}")
    return state

def architect_node(state: TonyState) -> TonyState:
    """📐 Tony [Architect]: Code Generation & Visual Design."""
    print(f"📐 Tony [Architect]: Drafting Manim code with Gemini 2.0...")
    prompt = f"""
    Based on this pedagogical plan: {state['script_plan']}
    Write a single, professional Manim Python script.
    
    CRITICAL TEMPLATE (STABLE):
    ```python
    from manim import *
    
    class Masterclass(Scene):
        def construct(self):
            # 1. Setup Background (STAYS THROUGHOUT)
            try:
                bg = ImageMobject("{state['image_path']}").scale(2)
                self.add(bg)
            except: pass
            
    CRITICAL STABILITY RULES:
    1. ONLY use 'MathTex(r"\\text{...}")' for all clinical text to ensure LaTeX elegance.
    2. For formulas, use standard LaTeX (e.g., MathTex(r"Ca^{{2+}}") or MathTex(r"CO_{{2}}")).
    3. ONLY use 'FadeIn' and 'FadeOut' animations.
    4. KEEP it under 40 lines of code.
    5. Use VGroup().arrange(DOWN) for lists.
    6. The class MUST be named 'Masterclass'.
    """
    state["manim_code"] = model_invoke(prompt).replace("```python", "").replace("```", "").strip()
    return state

def supervisor_node(state: TonyState) -> TonyState:
    """🔍 Tony [Supervisor]: Verification Trial & Final Assembly."""
    print(f"🔍 Tony [Supervisor]: Verification Trial {state['attempt_count'] + 1}...")
    
    # 1. Render Manim
    temp_file = f"temp_{state['topic']}.py"
    with open(temp_file, "w") as f:
        f.write(state["manim_code"])
    
    cmd = ["./venv/bin/manim", "-ql", temp_file]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("❌ Tony [Supervisor]: Manim Render Failed.")
        state["rendering_errors"] = result.stderr
        state["attempt_count"] += 1
        return state

    # 2. Generate Narration Audio (Robust Subprocess)
    print("🎙️ Tony [Supervisor]: Generating Narration Audio...")
    audio_path = f"{state['topic']}_audio.m4a"
    # Extract plain text from script plan (simplified for demo)
    script_text = state["script_plan"].replace("{", "").replace("}", "").replace('"', "")
    subprocess.run(["say", "-v", "Samantha", "-o", audio_path, script_text])
    
    # 3. Final Media Merge (Topic-Specific Discovery)
    print(f"🎬 Tony [Supervisor]: Merging Masterclass for {state['topic']}...")
    import glob
    # Search strictly within the topic's folder to avoid stale asset collision
    renders = glob.glob(f"media/videos/temp_{state['topic']}/**/Masterclass.mp4", recursive=True)
    
    if not renders:
        print(f"❌ Tony [Supervisor]: No rendered video found for {state['topic']}.")
        state["rendering_errors"] = "Manim output not found"
        return state
        
    video_path = renders[0]
    print(f"✅ Tony [Supervisor]: Found valid topic-asset at {video_path}")
    
    # 3. Final Media Merge (Direct FFmpeg for stability)
    print(f"🎬 Tony [Supervisor]: Merging Masterclass for {state['topic']} via FFmpeg...")
    final_output = f"{state['topic']}_masterclass.mp4"
    
    # Direct FFmpeg merge command (Hardened with explicit encoding)
    FFMPEG_PATH = "/Users/apple/Desktop/easetolearn.videogeneration/venv/lib/python3.9/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-x86_64-v7.1"
    
    merge_cmd = [
        FFMPEG_PATH, "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "libx264",        # Explicitly encode to H.264
        "-preset", "veryfast",    # Speed optimization
        "-crf", "23",             # High quality
        "-c:a", "aac",            # Standard audio
        "-b:a", "128k",           # Audio bitrate
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-movflags", "+faststart", # Web-optimized playback
        "-shortest",
        final_output
    ]
    
    merge_result = subprocess.run(merge_cmd, capture_output=True, text=True)
    
    if merge_result.returncode == 0:
        state["output_path"] = os.path.abspath(final_output)
        state["rendering_errors"] = None
        print(f"✅ Tony [Supervisor]: Production Complete! -> {final_output}")
    else:
        print(f"❌ Tony [Supervisor]: FFmpeg Merge Failed: {merge_result.stderr}")
        state["rendering_errors"] = merge_result.stderr
    
    return state

def should_continue(state: TonyState):
    """Router for self-healing loop."""
    if state.get("rendering_errors") and state["attempt_count"] < 3:
        print("⚠️ Tony [Supervisor]: Error detected. Retrying...")
        return "architect"
    return END

# Build the Graph
workflow = StateGraph(TonyState)

workflow.add_node("director", director_node)
workflow.add_node("vision", vision_node) # New Node!
workflow.add_node("architect", architect_node)
workflow.add_node("supervisor", supervisor_node)

workflow.set_entry_point("director")
workflow.add_edge("director", "vision")     # Director -> Vision
workflow.add_edge("vision", "architect")    # Vision -> Architect
workflow.add_edge("architect", "supervisor")
workflow.add_conditional_edges("supervisor", should_continue)

app = workflow.compile()

if __name__ == "__main__":
    # Test Trigger
    initial_state = {
        "raw_input": "Cardiac output is the volume of blood the heart pumps per minute. Formula: CO = HR x SV.",
        "topic": "CardiacOutput",
        "attempt_count": 0,
        "image_prompts": []
    }
    print("🚀 Team Tony: Autonomous Mission Started!")
    final_state = app.invoke(initial_state)
    print(f"🏆 Mission Complete! Output: {final_state.get('output_path')}")
