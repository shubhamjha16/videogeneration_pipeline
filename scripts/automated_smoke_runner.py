import os
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  Warning: 'python-dotenv' not found. Environment variables must be set manually.")

try:
    from autonomous_graph import app as graph
except ImportError as e:
    print(f"❌ Error: Could not import autonomous_graph. Ensure dependencies are installed. ({e})")
    import sys
    sys.exit(1)


def run_test_job():
    topic = "exploring linear patterns finding the steady path"
    html_path = "linear_patterns.html"
    
    with open(html_path, "r") as f:
        html_content = f.read()

    print(f"🚀 Starting Real-World Test Job: {topic}")
    
    # We force 'explainer' mode to test our new Higgsfield integration
    initial_state = {
        "raw_input":         html_content,
        "topic":             topic,
        "attempt_count":     0,
        "parsed_facts":      None,
        "render_mode":       "explainer",   # FORCED for testing
        "with_avatar":       False,
        "video_type":        "educational",
        "scenes":            None,
        "image_path":        None,
        "image_paths":       None,
        "audio_files":       None,
        "manim_script_path": None,
        "output_path":       None,
        "video_url":         None,
        "rendering_errors":  None,
        "slides":             None,
        "slide_paths":        None,
        "clip_paths":         None,
        "critic_feedback":    None,
        "ppt_attempt_count":  0,
        "no_vision":         False
    }

    try:
        final_state = graph.invoke(initial_state)
        
        print("\n--- TEST JOB FINAL STATE ---")
        print(f"Status: {'SUCCESS' if not final_state.get('rendering_errors') else 'FAILED'}")
        print(f"Output Path: {final_state.get('output_path')}")
        print(f"Video URL: {final_state.get('video_url')}")
        
        if final_state.get('rendering_errors'):
            print(f"Errors: {final_state.get('rendering_errors')}")
            
    except Exception as e:
        print(f"❌ Pipeline crashed: {e}")

if __name__ == "__main__":
    run_test_job()
