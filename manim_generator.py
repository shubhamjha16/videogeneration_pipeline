import os
import subprocess
import json
import re
from openai import OpenAI

# Initialize the OpenAI client
# Ensure the OPENAI_API_KEY environment variable is set
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

def get_dynamic_manim_code(text: str) -> str:
    """
    Calls OpenAI to generate a ManimCE script based on the educational text.
    """
    if not client.api_key:
        print("Warning: OPENAI_API_KEY is not set. Falling back to simple template.")
        return get_fallback_manim_code(text)
        
    prompt = f"""
You are an expert at Manim (Community Edition).
Generate a complete, completely valid Python script using ManimCE that visualizes the following physics/math explanation.
The animation should be visually appealing, educational, and clean.

Explanation Text:
"{text}"

RULES:
1. ONLY output valid Python code. NO markdown formatting, NO explanations.
2. The main scene class MUST be named `GeneratedScene`.
3. Use `self.play(Write(Text("something")))` or `Tex("...Formula...")` appropriately.
4. Keep the animation simple enough to render cleanly (less than 15 seconds total run_time).
5. Output the code strictly without ```python or ``` block enclosures. Just the raw code.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        code = response.choices[0].message.content.strip()
        
        # Clean up in case there are still markdown formatting artifacts
        code = re.sub(r"^```python\s*", "", code)
        code = re.sub(r"^```\s*", "", code)
        code = re.sub(r"```$", "", code)
        
        if "class GeneratedScene(Scene):" not in code:
            raise ValueError("LLM did not generate a class named GeneratedScene")
            
        return code
        
    except Exception as e:
        print(f"Failed to generate dynamic Manim code via OpenAI: {e}")
        return get_fallback_manim_code(text)

def get_fallback_manim_code(text: str) -> str:
    """
    Fallback basic template if API fails or key is missing.
    """
    return f"""
from manim import *
import textwrap

class GeneratedScene(Scene):
    def construct(self):
        text_str = {json.dumps(text)}
        wrapped_text = textwrap.fill(text_str, width=45)
        text_obj = Text(wrapped_text, font_size=36)
        self.play(Write(text_obj), run_time=int(len(text_str)*0.05))
        self.wait(2)
"""

def generate_manim_video(text: str, scene_idx: int, output_dir: str = ".") -> str:
    """
    Dynamically generates a Manim scene script using AI, then renders it to an mp4 file.
    """
    output_filename = os.path.join(output_dir, f"scene_{scene_idx}_manim.mp4")
    script_filename = os.path.join(output_dir, f"scene_{scene_idx}_script.py")

    # Fetch the dynamic code from LLM
    print(f"Generating dynamic Manim python code for Scene {scene_idx} via OpenAI...")
    manim_code = get_dynamic_manim_code(text)

    with open(script_filename, "w") as f:
        f.write(manim_code)

    print(f"Running Manim to render Scene {scene_idx}...")
    
    # Run manim command: -qm means Medium Quality
    # We specify media_dir so Manim doesn't clutter the root media folder
    media_dir = os.path.join(output_dir, "media")
    cmd = ["manim", "-qm", "--media_dir", media_dir, "-o", f"scene_{scene_idx}_manim.mp4", script_filename, "GeneratedScene"]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600, env=os.environ)
    except subprocess.CalledProcessError as e:

        print(f"Manim rendering failed for scene {scene_idx}. Error: {e}")
        return ""
        
    expected_dir = os.path.join(media_dir, "videos", f"scene_{scene_idx}_script", "720p30")
    rendered_path = os.path.join(expected_dir, f"scene_{scene_idx}_manim.mp4")
    
    if os.path.exists(rendered_path):
        os.rename(rendered_path, output_filename)

    print(f"Generated Manim video for scene {scene_idx} -> {output_filename}")
    return output_filename
