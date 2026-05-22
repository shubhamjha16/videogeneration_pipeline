import os
import sys
from dotenv import load_dotenv

# Ensure parent directory is in path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from autonomous_graph import app, TonyState

load_dotenv()

# Topic and Content for the presentation
topic = "The Power of Generative AI in Video Production"
raw_input = """
# The Power of Generative AI in Video Production

## Introduction
Generative AI is transforming how we create video content, making it faster and more accessible than ever before.

## Key Benefits
- **Efficiency**: Reduce production time from weeks to minutes.
- **Cost-Effective**: Lower the barrier to entry for high-quality visuals.
- **Customization**: Easily tailor content for different audiences.

## ElevenLabs Integration
By using high-fidelity TTS from ElevenLabs, we can achieve natural-sounding narration that enhances the viewer's experience.

## Conclusion
The future of video is autonomous, creative, and powered by AI.
"""

# Initial state for the pipeline
initial_state = {
    "topic": topic,
    "raw_input": raw_input,
    "source_type": "markdown",
    "video_type": "educational",
    "render_mode": "presentation",
    "with_avatar": False,
    "use_elevenlabs": True,
    "avatar_type": "logo",
    "overrides": {
        "render_mode": "presentation",
        "use_elevenlabs": True,
        "enable_ambient": True
    },
    "job_id": "elevenlabs_demo_001",
    "attempt_count": 0,
    "ppt_attempt_count": 0,
    "no_vision": False,
    "research_count": 0,
}

print(f"🚀 Starting video generation pipeline for: {topic}")
print(f"🎬 Render Mode: Presentation | 🎙️ TTS: ElevenLabs")

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
