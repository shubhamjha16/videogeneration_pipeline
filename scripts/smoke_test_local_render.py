import os
import sys
import json
import uuid
from datetime import datetime

# Add root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from autonomous_graph import app
from html_parser import parse_tony_html

def run_local_smoke_test():
    print(f"🔥 [INDUSTRIAL SMOKE TEST] Running on LOCAL GEMMA...")
    print(f"📍 Endpoint: {config.LOCAL_LLM_URL}")
    print(f"📍 Model:    {config.LOCAL_LLM_MODEL}")
    
    # 1. Load the lesson content
    with open("academic_presets/linear_patterns.html", "r") as f:
        html_content = f.read()
    
    # 2. Setup job metadata
    job_id = f"smoke-test-{uuid.uuid4().hex[:6]}"
    
    print(f"\n🧠 Step 2: Triggering Local Gemma for Ingestion & Logic...")
    print("   (This will push your Mac Mini's GPU over the WireGuard tunnel)")
    
    # Prepare the standard state schema
    initial_state = {
        "raw_input":          html_content,
        "topic":              "Exploring Linear Patterns",
        "attempt_count":      0,
        "ppt_attempt_count":  0,
        "no_vision":          True,
        "job_id":             job_id,
        "parsed_facts":       None, "render_mode": None, "scenes": None,
        "image_path":         None, "audio_files": None, "manim_script_path": None,
        "output_path":        None, "video_url":   None, "rendering_errors":  None,
        "with_avatar":        False,
        "slides":             None, "slide_paths": None, "clip_paths": None,
        "critic_feedback":    None,
        "video_type":         "educational",
        "image_paths":        None,
        "heygen_video_path":  None,
        "subtitle_style":     None,
    }
    
    try:
        # Run the final completion
        print("   [Graph] Running full autonomous loop...")
        final = app.invoke(initial_state)
        
        if final.get("manim_script_path") or final.get("video_url"):
            print("\n✅ [Success] Local Gemma generated a valid output!")
            print(f"   Video URL: {final.get('video_url')}")
            print(f"   Local Cache: {final.get('output_path')}")
            print("\n🏆 SMOKE TEST PASSED! The factory is running on your Mac Mini.")
        else:
            print("\n⚠️  [Warning] Graph completed but no output found. Check logs.")
            
    except Exception as e:
        print(f"\n❌ SMOKE TEST CRASHED: {e}")

if __name__ == "__main__":
    run_local_smoke_test()
