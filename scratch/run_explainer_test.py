import os
import asyncio
from autonomous_graph import app
from dotenv import load_dotenv

load_dotenv()

async def main():
    topic = "The Butterfly Effect"
    lesson_file = "lessons/butterfly_effect_explainer.html"
    
    if not os.path.exists(lesson_file):
        print(f"❌ Error: Lesson file {lesson_file} not found.")
        return

    with open(lesson_file) as f:
        content = f.read()

    print(f"🚀 Starting Pipeline 3 (Explainer) Test: {topic}")
    
    # Run the compiled graph
    final = await app.ainvoke({
        "raw_input":          content,
        "topic":              topic,
        "attempt_count":      0,
        "ppt_attempt_count":  0,
        "no_vision":          False,
        "job_id":             "explainer_test_v1",
        "parsed_facts":       None, "render_mode": "auto", "scenes": None,
        "image_path":         None, "audio_files": None, "manim_script_path": None,
        "output_path":        None, "video_url":   None, "rendering_errors":  None,
        "with_avatar":        False,
        "slides":             None, "slide_paths": None, "clip_paths": None,
        "critic_feedback":    None,
        "video_type":         "educational",
        "image_paths":        None,
        "heygen_video_path":  None,
        "subtitle_style":     None,
    })

    print("\n" + "="*50)
    print(f"Status: SUCCESS" if final.get('output_path') else "Status: FAILED")
    print(f"Output: {final.get('output_path')}")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
