import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from explainer_slides_generator import render_explainer_mcq_slide

def test_mcq_renderer():
    print("🧪 Running MCQ Renderer unit test...")
    os.makedirs("output/test_mcq", exist_ok=True)
    
    # Scene 1: Option Reveal (None of the above)
    visual_data = {
        "question": "Which of the following is NOT a symptom of heart failure?",
        "options": {
            "A": "Systolic Failure: The heart can't pump with enough force.",
            "B": "Diastolic Failure: The heart can't fill with enough blood.",
            "C": "Shortness of breath.",
            "D": "All of the above are correct features."
        },
        "letter": "A",
        "correct_answer": "none",
        "explanation": "The correct answer is none of the above since the first two options describe types, not symptoms."
    }
    
    output_path = "output/test_mcq/answer_reveal_none.png"
    render_explainer_mcq_slide("answer_reveal", visual_data, output_path)
    print(f"🎉 Scene saved successfully to {output_path}!")

if __name__ == "__main__":
    test_mcq_renderer()
