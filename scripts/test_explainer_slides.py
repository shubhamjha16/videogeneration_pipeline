import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from autonomous_graph import app

def test_explainer_slides():
    topic = "Heart Failure: A Comprehensive Overview"
    # Simple markdown content about heart failure
    raw_input = """
    Heart failure, sometimes known as congestive heart failure, occurs when the heart muscle doesn't pump blood as well as it should.
    
    ### What should the AI hosts focus on?
    - The difference between Systolic and Diastolic heart failure.
    - Common causes like coronary artery disease and high blood pressure.
    - Visualizing the 'backup' of fluid into lungs or legs.
    
    ### Key Concepts
    1. Systolic Failure: The heart can't pump with enough force.
    2. Diastolic Failure: The heart can't fill with enough blood.
    3. Symptoms: Shortness of breath, fatigue, swollen legs.
    """
    
    print(f"🚀 Triggering Explainer Slides pipeline for: {topic}")
    
    # We force explainer_slides mode via overrides
    initial_state = {
        "raw_input": raw_input,
        "topic": topic,
        "job_id": "test_explainer_slides_" + str(os.getpid()),
        "overrides": {"render_mode": "explainer_slides"},
        "use_elevenlabs": True,
        
        # Initialize other required state fields
        "attempt_count": 0,
        "ppt_attempt_count": 0,
        "no_vision": False,
        "with_avatar": False,
        "ledger": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "elevenlabs_chars": 0,
            "heygen_seconds": 0
        },
        "rejected_attempts": [],
        "media_manifest": [],
        "research_count": 0
    }
    
    final_state = app.invoke(initial_state)
    
    print("\n🏁 Pipeline Finished!")
    print(f"Output Path: {final_state.get('output_path')}")
    print(f"Video URL: {final_state.get('video_url')}")
    print(f"Ledger: {final_state.get('ledger')}")

if __name__ == "__main__":
    test_explainer_slides()
