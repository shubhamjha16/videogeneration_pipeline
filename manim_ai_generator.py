import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def generate_manim_script(explanation_text, topic):
    """
    Translates a text explanation into a Manim Python script.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Error: GEMINI_API_KEY not found in .env file."

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""
    You are an expert Manim animator and math tutor.
    Translate the following explanation into a clean, professional Manim Python script.
    
    GUIDELINES:
    1. DO NOT USE MathTex or LaTeX. Use pure 'Text' objects instead for macOS compatibility.
    2. The scene class name MUST be '{topic.replace(' ', '')}'.
    3. Center everything. Use wait() commands that match natural speaking pauses.
    4. Keep visuals simple: show the problem, show the steps, show the final answer.
    5. ONLY return the Python code. No markdown, no explanations.

    EXPLANATION TO ANIMATE:
    {explanation_text}
    """

    response = model.generate_content(prompt)
    
    # Clean the response if it contains markdown code blocks
    code = response.text.replace("```python", "").replace("```", "").strip()
    return code

if __name__ == "__main__":
    # Test call
    test_text = "To find the area of a circle, we use the formula Pi r squared."
    print(generate_manim_script(test_text, "AreaOfCircle"))
