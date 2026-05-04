"""
Healer Agent — Groq (Llama 3.3)
When Manim render fails, reads the error + broken script,
returns a fixed version of the script.

Called by autonomous_graph.py healer_node on render failure.
"""

import os
import re
from llm_factory import LLMFactory
from searxng_tool import search_searxng

SYSTEM_PROMPT = """You are a Manim expert fixing broken Python animation scripts.

You will receive:
1. The broken Manim script
2. The exact error message from the Manim renderer

━━━ CRITICAL RULES ━━━
- NEVER use `self.set_background()` or `self.set_text()`. They do not exist. Use `FadeIn(Rectangle(...))` and `Write(Tex(...))`.
- PRESERVE DESIGN SYSTEM: Always keep the `class DesignTokens:` block at the top. Use `DesignTokens.BLUE`, `DesignTokens.YELLOW`, `DesignTokens.GREEN`, etc. for coloring mobjects.
- Fix ONLY what is broken. Do not rewrite the logic.
- Keep all scene structure (`class ... (Scene): def construct(self)`) intact.
- Return ONLY the complete fixed Python script inside a single markdown code block. No explanation.

━━━ FEW-SHOT EXAMPLES ━━━

BROKEN:
    self.set_background("blue")
    self.set_text("Hello")
FIXED:
    bg = Rectangle(width=14, height=8, fill_color=BLUE, fill_opacity=1)
    self.add(bg)
    text = Tex(r"\\text{Hello}").scale(1.2)
    self.play(Write(text))

BROKEN:
    axes = Axes()
    val = axes.get_output(5)
FIXED:
    axes = Axes()
    val = axes.c2p(5, 0) # c2p is coords-to-point

Return ONLY the code. No chatter."""


def run_healer(broken_script: str, error_message: str, knowledge_base: dict = None, job_id: str = None) -> tuple[str, dict]:
    """
    Ask Groq (Llama 3.3) to fix a broken Manim script.
    Returns: (fixed_script, usage)
    """
    kb_context = ""
    if knowledge_base:
        import json
        kb_context = f"\n━━━ VERIFIED LESSON FACTS (KB) ━━━\n{json.dumps(knowledge_base, indent=2)}\n"
    # ... search logic remains same ...
    search_context = ""
    try:
        clean_error = error_message.strip().splitlines()[-1] if error_message else "Manim render error"
        if any(keyword in clean_error for keyword in ["Error", "Exception", "invalid", "not found"]):
            results = search_searxng(f"Manim {clean_error}", categories="it,general")
            if results:
                search_context = "\n━━━ WEB RESEARCH (POTENTIAL FIXES) ━━━\n"
                for res in results[:2]:
                    search_context += f"- {res['title']}: {res['content']}\n"
    except Exception as e:
        print(f"   ⚠️ Healer search failed: {e}")

    content, usage = LLMFactory.get_completion(
        messages=[
            {"role": "user", "content": (
                f"ERROR MESSAGE:\n{error_message}\n\n"
                f"{kb_context}\n"
                f"{search_context}\n"
                f"BROKEN SCRIPT:\n```python\n{broken_script}\n```\n\n"
                f"Return the complete fixed script."
            )}
        ],
        system_prompt=SYSTEM_PROMPT,
        json_mode=False,
        include_usage=True,
        cacheable=False,
        job_id=job_id
    )
    fixed = content
    match = re.search(r'```(?:python)?\s*(.*?)```', fixed, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip(), usage
    
    if "import " in fixed:
        lines = fixed.splitlines()
        for i, line in enumerate(lines):
            if line.strip().startswith(("import ", "from ")):
                code_body = "\n".join(lines[i:]).strip()
                return code_body.split("```")[0].strip(), usage
    
    return fixed.strip().split("```")[0].strip(), usage
