import os
import sys

# Ensure workspace root is in path
sys.path.append(os.path.abspath("."))

from explainer_slides_marketing_generator import explainer_slides_marketing_node

# Define state to execute the premium Planner + Critic marketing loop for EaseToLearn
state = {
    "topic": "EaseToLearn: The Premier AI-Powered Animated Video Platform for Indian Competitive Exams",
    "job_id": "easetolearn_marketing_slides",
    "use_elevenlabs": True,
    "parsed_facts": {
        "subject": "marketing",
        "topic": "EaseToLearn EdTech Video Platform",
        "concept": (
            "EaseToLearn is a state-of-the-art AI video education platform that transforms dry textbook content "
            "into beautiful, highly interactive animated lessons. Tailored for Indian competitive exams like UPSC, "
            "FMGE, JEE, and NEET, the platform uses modern visual templates (whiteboard doodles, Manim animations, "
            "and Gemini Omni) to explain hard concepts. Students engage actively through real-time MCQ practice "
            "and benefit from 10x faster revision and retention."
        ),
        "key_benefits": [
            "Whiteboard and 3D dynamic animated lessons for hard scientific topics.",
            "Interactive MCQ layouts with step-by-step cross-outs and instant answer reveals.",
            "Human-like synthetic voiceovers powered by ElevenLabs for clear retention.",
            "Visual cheat sheets and custom summaries to maximize competitive exam scores."
        ]
    },
    "avatar_type": "tony_cartoon",
    "with_avatar": True
}

print("🚀 Starting EaseToLearn Closed-Loop Whiteboard Marketing Slide Production...")
try:
    final_state = explainer_slides_marketing_node(state)
    video_path = final_state.get("output_path")
    print("\n🎉 MARKETING VIDEO COMPILATION SUCCESS!")
    print(f"🎬 Output video saved to: {video_path}")
except Exception as e:
    print(f"\n❌ Pipeline execution encountered an error: {e}")
    sys.exit(1)
