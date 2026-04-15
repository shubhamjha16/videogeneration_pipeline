import os
import sys
from autonomous_graph import run_autonomous_factory

def run_heygen_test():
    # Production Test: Internal Iliac Artery (Medical Update)
    # This lesson will be processed via Pipeline 4 (HeyGen / User-Generated)
    
    lesson_path = "lessons/tony.html"
    
    if not os.path.exists(lesson_path):
        print(f"❌ Error: Lesson file {lesson_path} not found.")
        return

    with open(lesson_path, "r") as f:
        html_content = f.read()

    # Industrial Instruction: Force Pipeline 4 (User-Generated Avatar)
    state = {
        "job_id": "heygen_test_v1",
        "topic": "Internal Iliac Artery branches vs Ovarian Artery",
        "render_mode": "user_generated", # Forces HeyGen Path
        "raw_input": html_content,
        "media_assets": [],
        "voice_id": os.environ.get("ELEVENLABS_VOICE_ID", "josh")
    }

    print("🚀 [HEYGEN TEST] Launching Industrial Pipeline 4...")
    final_state = run_autonomous_factory(state)
    
    print("\n" + "="*50)
    print(f"HEYGEN TEST STATUS: {final_state.get('status', 'UNKNOWN')}")
    print(f"OUTPUT PATH: {final_state.get('output_path', 'N/A')}")
    print("="*50)

if __name__ == "__main__":
    run_heygen_test()
