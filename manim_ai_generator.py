import os
import re
import google.generativeai as genai
import config

def generate_manim_script(scenes, topic):
    """
    Translates a list of (text, duration) scenes into a synced Manim script.
    """
    api_key = config.GEMINI_API_KEY
    if not api_key:
        return "Error: GEMINI_API_KEY not found in config."

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    # Convert scenes to a formatted string for the prompt
    formatted_scenes = "\n".join([f"- TEXT: \"{s['text']}\" | DURATION: {s['duration']}s" for s in scenes])

    prompt = f"""
    You are an expert Manim animator and global pedagogical expert. 
    Translate the following synced audio scenes into a single, clean, professional Manim Python script.
    
    THEME:
    - Use a 'Modern Dark' aesthetic: BackgroundColor = "#121212".
    - Primary Color for Math/Biology: "#00BFFF" (Deep Sky Blue).
    - Secondary/Step Color: "#FFD700" (Gold).
    
    SYNC REQUIREMENTS:
    - For EVERY scene below, you must perform the corresponding animation and use `self.wait(DURATION)`.
    - Total duration of the animation MUST match the sum of durations provided.
    
    VISUAL POLISH:
    - DO NOT USE MathTex or LaTeX. Use pure 'Text' objects.
    - Use `VGroup` to keep multi-line equations centered and clean.
    - Use `Write()`, `FadeIn()`, and `Transform()` for fluid transitions.
    - Use `SurroundingRectangle()` or `Indicate()` for final key points or answers.
    
    SCENE METADATA:
    - Class Name: {re.sub(r'[^a-zA-Z0-9]', '', topic)}
    
    SCENES TO ANIMATE:
    {formatted_scenes}
    
    ONLY return the Python code. No markdown, no explanations.
    """

    response = model.generate_content(prompt)
    
    # Clean the response if it contains markdown code blocks
    code = response.text.replace("```python", "").replace("```", "").strip()
    return code

if __name__ == "__main__":
    # Test call
    test_scenes = [
        {"text": "First, we initialize the variable x.", "duration": 2.5},
        {"text": "Then we add five to it.", "duration": 1.8}
    ]
    print(generate_manim_script(test_scenes, "TestSync"))
