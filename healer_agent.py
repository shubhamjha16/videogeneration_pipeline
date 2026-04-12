"""
Healer Agent — Groq (Llama 3.3)
When Manim render fails, reads the error + broken script,
returns a fixed version of the script.

Called by autonomous_graph.py healer_node on render failure.
"""

import os
import re
from groq import Groq

SYSTEM_PROMPT = """You are a Manim expert fixing broken Python animation scripts.

You will receive:
1. The broken Manim script
2. The exact error message from the Manim renderer

Your job:
- Read the error carefully
- Fix ONLY what is broken — do not rewrite the whole script
- Keep all visual_type logic and scene structure intact
- Common fixes:
  * LaTeX errors: check Tex() vs MathTex() usage, escape special chars
  * play with no animations: guard with: fos=[FadeOut(m) for m in self.mobjects]; self.play(*fos) if fos else None
  * Undefined variable: check variable names match between scenes
  * Unicode in Tex(): replace with LaTeX commands (bullet->$\\bullet$, checkmark->$\\checkmark$)

Return ONLY the complete fixed Python script. No explanation, no markdown."""


def run_healer(broken_script: str, error_message: str) -> str:
    """
    Ask Groq (Llama 3.3) to fix a broken Manim script.

    Args:
        broken_script : full content of the broken .py file
        error_message : stderr from the failed Manim render

    Returns:
        Fixed Python script as a string
    """

    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"ERROR MESSAGE:\n{error_message}\n\n"
                f"BROKEN SCRIPT:\n```python\n{broken_script}\n```\n\n"
                f"Return the complete fixed script."
            )}
        ]
    )
    fixed = response.choices[0].message.content
    # Robust extraction: Only take what is inside ```python ... ```
    # If LLM includes chatter outside the blocks, this prevents a SyntaxError in Manim.
    match = re.search(r'```python\s*(.*?)```', fixed, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Fallback: if no backticks but starts with 'import', it might be naked code
    if "import " in fixed:
        # Still try to strip any common LLM lead-in chatter
        lines = fixed.splitlines()
        for i, line in enumerate(lines):
            if line.strip().startswith(("import ", "from ")):
                return "\n".join(lines[i:]).strip()
    
    return fixed.strip()
