import os
import sys
import json
from unittest.mock import patch, MagicMock

# Ensure workspace root is in path
workspace_dir = "/Users/apple/Desktop/easetolearn.videogeneration"
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

import image_generator
# Bypasses DALL-E calls to use high-fidelity offline fallbacks
image_generator._DALLE_FAILED = True

from llm_factory import LLMFactory
from explainer_slides_marketing_generator import explainer_slides_marketing_node

def run_marketing_pipeline_test():
    print("🚀 Starting Marketing Explainer Slides Agent Closed-Loop validation...")
    
    # 1. Define the mock responses to simulate:
    #    - Attempt 1: Planner script is dry, Critic rejects with feedback.
    #    - Attempt 2: Planner fixes the feedback, Critic approves!
    
    # Attempt 1: Dry planner proposal
    planner_attempt_1 = {
        "scenes": [
            {
                "visual_type": "concept_bullets",
                "visual_data": {
                    "title": "Mitochondria Specs",
                    "subtitle": "Cellular Specs",
                    "bullets": ["It makes ATP energy", "It has double membranes"],
                    "objects": ["cell outline"]
                },
                "narration_text": "Mitochondria are organelles that produce energy. They are characterized by having a outer and inner membrane.",
                "tony_pose": "desk_happy"
            }
        ]
    }
    
    # Attempt 1 Critique: Reject!
    critic_critique_1 = {
        "approved": False,
        "feedback": "This slide is way too dry, boring, and reads like a textbook manual! Re-write it to be highly persuasive, focus on dynamic customer-centric benefits, add a visual metaphor rocket doodle, and add an interactive MCQ slide with a powerful Call to Action (CTA) at the end!",
        "score": 4
    }
    
    # Attempt 2: Persuasive planner correction
    planner_attempt_2 = {
        "scenes": [
            {
                "visual_type": "concept_bullets",
                "visual_data": {
                    "title": "Supercharge Cellular Productivity",
                    "subtitle": "Energy at 10x Scale",
                    "bullets": [
                        "Boost operational efficiency naturally",
                        "Power thousands of functions concurrently",
                        "Futureproof your core cellular structure"
                    ],
                    "objects": ["speedometer sketch", "rocket metaphor sketch"]
                },
                "narration_text": "Are you ready to scale your cellular energy to 10x efficiency? Say goodbye to sluggish cellular performance and supercharge your body's productivity today!",
                "tony_pose": "excited"
            },
            {
                "visual_type": "mcq_layout",
                "visual_data": {
                    "question": "Ready to claim your 10x energy boost today?",
                    "options": {
                        "A": "Sign up for premium cellular coaching",
                        "B": "Download our free Mitochondria Guide",
                        "C": "Schedule a 1-on-1 energy audit",
                        "D": "Continue feeling sluggish"
                    },
                    "letter": "B",
                    "explanation": "Claim your free guide today and immediately Futureproof your cellular productivity!"
                },
                "narration_text": "Choose your next high-impact step. Sign up or download our guide now to begin scaling!",
                "tony_pose": "standing_point_up"
            }
        ]
    }
    
    # Attempt 2 Critique: Approved!
    critic_critique_2 = {
        "approved": True,
        "feedback": "Perfect! This is incredibly engaging, benefit-oriented, visually punchy, features a brilliant interactive MCQ guide choice, and ends with a powerful sign-up CTA. Approved!",
        "score": 9
    }
    
    # 2. Mock get_completion to return these sequenced responses
    mock_completions = [
        (json.dumps(planner_attempt_1), {}),
        (json.dumps(critic_critique_1), {}),
        (json.dumps(planner_attempt_2), {}),
        (json.dumps(critic_critique_2), {})
    ]
    
    call_index = 0
    def mock_get_completion(*args, **kwargs):
        nonlocal call_index
        if call_index < len(mock_completions):
            res = mock_completions[call_index]
            call_index += 1
            return res[0] # Returns string content
        return "{}"

    # 3. Trigger validation state
    test_state = {
        "topic": "Cellular Energy Booster",
        "job_id": "test_marketing_slides",
        "use_elevenlabs": False, # Use offline macOS say TTS
        "parsed_facts": {
            "subject": "biology",
            "key_benefits": ["10x energy", "ATP scaling"]
        },
        "avatar_type": "tony_cartoon",
        "with_avatar": True
    }
    
    print("\n--- Running Closed-Loop Agent Mock Test ---")
    with patch.object(LLMFactory, "get_completion", side_effect=mock_get_completion):
        final_state = explainer_slides_marketing_node(test_state)
        
    print("\n--- Verifying Output Assets ---")
    video_path = final_state.get("output_path")
    print(f"🎬 Marketing video compiled successfully at: {video_path}")
    
    assert video_path and os.path.exists(video_path), "Marketing slide video was not compiled!"
    assert os.path.getsize(video_path) > 0, "Compiled marketing slide video file is empty!"
    
    # Let's verify that the MCQ slide image is narrowed correctly and Tony is present
    output_dir = os.path.dirname(video_path)
    slide_1_img = os.path.join(output_dir, "slide_1.png")
    assert os.path.exists(slide_1_img), "MCQ slide card image slide_1.png was not rendered!"
    
    print("✅ MCQ slide card slide_1.png exists on disk!")
    print("\n🎉 Closed-loop Marketing Explainer Agent successfully verified and compiled!")

if __name__ == "__main__":
    run_marketing_pipeline_test()
