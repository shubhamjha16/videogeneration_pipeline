import os
import sys
from dotenv import load_dotenv

# Ensure parent directory is in path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from autonomous_graph import app, TonyState

load_dotenv()

# Topic and Content for the Manim video
topic = "The Pythagorean Theorem"
raw_input = """
# The Pythagorean Theorem

The Pythagorean theorem is a fundamental relation in Euclidean geometry among the three sides of a right triangle.

## The Formula
In a right-angled triangle, the square of the hypotenuse (the side opposite the right angle) is equal to the sum of the squares of the other two sides.
The formula is: **a² + b² = c²**

## Example
If side **a** is 3 units and side **b** is 4 units, then:
3² + 4² = 9 + 16 = 25
So, side **c** is √25 = 5 units.

## Visualization
Imagine squares built on each of the three sides. The area of the square on the hypotenuse is exactly the sum of the areas of the other two squares.
"""

# Initial state for the pipeline
initial_state = {
    "topic": topic,
    "raw_input": raw_input,
    "source_type": "markdown",
    "video_type": "educational",
    "render_mode": "manim",
    "with_avatar": False,
    "use_elevenlabs": True,
    "avatar_type": "logo",
    "overrides": {
        "render_mode": "manim",
        "use_elevenlabs": True,
        "enable_ambient": True,
        "has_formula": True
    },
    "job_id": "manim_demo_001",
    "attempt_count": 0,
    "ppt_attempt_count": 0,
    "no_vision": False,
    "research_count": 0,
}

print(f"🚀 Starting Manim video generation pipeline for: {topic}")
print(f"🎬 Render Mode: Manim | 🎙️ TTS: ElevenLabs")

try:
    final_state = app.invoke(initial_state)
    print("\n✅ Pipeline completed successfully.")
    print(f"Output Video Path: {final_state.get('output_path')}")
    if final_state.get('video_url'):
        print(f"Video URL: {final_state.get('video_url')}")
except Exception as e:
    print(f"\n❌ Pipeline failed: {e}")
    import traceback
    traceback.print_exc()
