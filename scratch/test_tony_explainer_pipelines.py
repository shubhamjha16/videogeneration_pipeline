import os
import sys

# Ensure workspace root is in path
workspace_dir = "/Users/apple/Desktop/easetolearn.videogeneration"
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

import image_generator
# Bypasses DALL-E calls to prevent network wait and API cost
image_generator._DALLE_FAILED = True

from explainer_slides_generator import generate_explainer_slides_video
from explainer_gemini_hybrid_slides_generator import generate_explainer_gemini_hybrid_slides_video

def run_tony_explainer_test():
    print("🚀 Starting Tony Avatar Explainer Pipelines validation...")
    
    test_dir = os.path.join(workspace_dir, "output", "test_tony_explainer")
    os.makedirs(test_dir, exist_ok=True)
    
    # 1. Define a series of educational scenes with dynamic Tony poses
    scenes = [
        {
            "visual_type": "concept_bullets",
            "visual_data": {
                "title": "1. Understanding Mitochondria",
                "subtitle": "The Powerhouse of the Cell",
                "bullets": [
                    "Responsible for cellular respiration and energy creation.",
                    "Generates adenosine triphosphate (ATP) via aerobic processes.",
                    "Contains its own unique genetic material (mtDNA)."
                ],
                "objects": ["cell", "mitochondria diagram", "ATP molecule"]
            },
            "narration_text": "First, let's look at the powerhouse of the cell: the Mitochondria. It is responsible for producing most of the cell's energy in the form of ATP.",
            "tony_pose": "standing_point_up"
        },
        {
            "visual_type": "mcq_layout",
            "visual_data": {
                "question": "Which of the following is produced by the mitochondria during cellular respiration?",
                "options": {
                    "A": "Glucose",
                    "B": "Adenosine Triphosphate (ATP)",
                    "C": "Carbon Dioxide only",
                    "D": "Lactic Acid"
                },
                "letter": "B",
                "explanation": "Mitochondria convert nutrients into ATP, which serves as the primary energy currency of the cell."
            },
            "narration_text": "Here is a quick question: Which of the following is produced by the mitochondria during cellular respiration? Take a moment to think.",
            "tony_pose": "confused"
        }
    ]
    
    # ─── PART A: Whiteboard Doodle Slide Video Rendering ───
    print("\n--- Testing Whiteboard Doodle Slides Pipeline ---")
    try:
        whiteboard_video, whiteboard_ledger = generate_explainer_slides_video(
            scenes=scenes,
            output_dir=test_dir,
            topic="Cell Biology",
            job_id="test_tony_whiteboard",
            use_elevenlabs=False, # Use offline macOS say TTS
            subject="medical",
            avatar_type="tony_cartoon",
            with_avatar=True
        )
        print(f"✅ Whiteboard Slide Video compiled successfully!")
        print(f"   Video Location: {whiteboard_video}")
        print(f"   Usage Ledger: {whiteboard_ledger}")
        assert os.path.exists(whiteboard_video), "Whiteboard video file does not exist!"
        assert os.path.getsize(whiteboard_video) > 0, "Whiteboard video file is empty!"
    except Exception as e:
        print(f"❌ Whiteboard Slide Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    # ─── PART B: Explainer Gemini Hybrid Slide Video Rendering ───
    print("\n--- Testing Explainer Gemini Hybrid Slides Pipeline ---")
    try:
        # For hybrid slides, select optimal visual will fall back to dalle if omni fails,
        # which will trigger image_generator offline fallbacks. 
        hybrid_video, hybrid_ledger = generate_explainer_gemini_hybrid_slides_video(
            scenes=scenes,
            output_dir=test_dir,
            topic="Cell Biology",
            job_id="test_tony_hybrid",
            use_elevenlabs=False, # Use offline macOS say TTS
            subject="medical",
            avatar_type="tony_cartoon",
            with_avatar=True
        )
        print(f"✅ Explainer Gemini Hybrid Video compiled successfully!")
        print(f"   Video Location: {hybrid_video}")
        print(f"   Usage Ledger: {hybrid_ledger}")
        assert os.path.exists(hybrid_video), "Hybrid video file does not exist!"
        assert os.path.getsize(hybrid_video) > 0, "Hybrid video file is empty!"
    except Exception as e:
        print(f"❌ Explainer Gemini Hybrid Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n🎉 ALL Tony explainer slide video pipelines successfully validated!")

if __name__ == "__main__":
    run_tony_explainer_test()
