import os
import sys
from dotenv import load_dotenv

# Ensure parent directory is in path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from autonomous_graph import app, TonyState

load_dotenv()

# Topic and Content for the Notes video
topic = "Clinical Presentation of Heart Failure"
raw_input = """
# Clinical Presentation of Heart Failure

Heart failure (HF) is a clinical syndrome characterized by typical symptoms (e.g. breathlessness, ankle swelling, and fatigue) that may be accompanied by signs (e.g. elevated jugular venous pressure, pulmonary crackles, and peripheral oedema).

## Key Symptoms
- **Dyspnea**: Shortness of breath, especially during exertion or when lying down.
- **Orthopnea**: Difficulty breathing while lying flat.
- **Paroxysmal Nocturnal Dyspnea (PND)**: Sudden awakening with severe shortness of breath.
- **Fatigue and Weakness**: Reduced exercise tolerance.

## Physical Signs
- **Elevated JVP**: A sign of fluid overload.
- **Pulmonary Crackles**: Indicating pulmonary oedema.
- **Peripheral Oedema**: Swelling in the ankles and legs.
- **Third Heart Sound (S3)**: A classic sign of ventricular dysfunction.

## Diagnostic Approach
1. **ECG**: Looking for abnormalities.
2. **NT-proBNP**: A key biomarker for heart failure.
3. **Echocardiography**: The gold standard for assessing structural and functional changes.

## Conclusion
Early identification of symptoms and signs is crucial for the management of heart failure.
"""

# Initial state for the pipeline
initial_state = {
    "topic": topic,
    "raw_input": raw_input,
    "source_type": "markdown",
    "video_type": "educational",
    "render_mode": "notes",
    "with_avatar": False,
    "use_elevenlabs": True,
    "avatar_type": "logo",
    "overrides": {
        "render_mode": "notes",
        "use_elevenlabs": True,
        "enable_ambient": False
    },
    "job_id": "notes_demo_001",
    "attempt_count": 0,
    "ppt_attempt_count": 0,
    "no_vision": False,
    "research_count": 0,
}

print(f"🚀 Starting Notes video generation pipeline for: {topic}")
print(f"🎬 Render Mode: Notes | 🎙️ TTS: ElevenLabs")

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
