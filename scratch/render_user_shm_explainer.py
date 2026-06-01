import os
import sys

# Ensure project root is in python path
sys.path.append(os.path.abspath("."))

from explainer_slides_generator import generate_explainer_slides_video

# Define scenes based on the user's SHM curriculum JSON
scenes = [
    {
        "visual_type": "title_card",
        "visual_data": {
            "title": "Amplitude of Simple Harmonic Motion",
            "subtitle": "Combining Orthogonal SHM Components"
        },
        "narration_text": "Welcome to today's physics session. We are exploring simple harmonic motion, specifically investigating how to find the resultant amplitude when a sine and cosine component combine at the same angular frequency."
    },
    {
        "visual_type": "concept_explanation",
        "visual_data": {
            "title": "1. Resultant Amplitude Concept",
            "subtitle": "Geometrical phasor representation",
            "bullets": [
                "Displacement formula: x = A1 sin(wt) + A2 cos(wt)",
                "Sine and cosine terms are orthogonal (90 deg apart)",
                "Resultant amplitude formula: R = sqrt(A1^2 + A2^2)"
            ],
            "objects": ["sine wave oscillation curve", "vector phasor addition diagram"]
        },
        "narration_text": "First, let's look at the theory. Any displacement that is a linear combination of a sine and cosine function of the same frequency acts as orthogonal components. Geometrically, because they are ninety degrees out of phase, they combine like perpendicular vectors, making the resultant amplitude the square root of the sum of their squares."
    },
    {
        "visual_type": "solution_steps",
        "visual_data": {
            "title": "2. Step-by-Step Calculation",
            "subtitle": "Substituting the given coefficients",
            "bullets": [
                "Given SHM equation: x = 8 sin(wt) + 6 cos(wt)",
                "Coefficients: A1 = 8 cm and A2 = 6 cm",
                "R^2 = 8^2 + 6^2 = 64 + 36 = 100",
                "Resultant amplitude R = sqrt(100) = 10 cm"
            ],
            "objects": ["Pythagorean right triangle", "mathematical square root formula"]
        },
        "narration_text": "Next, let's substitute the values. Our sine component has an amplitude of eight centimeters, and our cosine has six centimeters. Squaring both terms gives sixty-four and thirty-six. Adding them equals one hundred, and taking the square root gives a resultant amplitude of exactly ten centimeters."
    },
    {
        "visual_type": "mcq_layout",
        "visual_data": {
            "question": "What is the resultant amplitude of the motion x = 8 sin(wt) + 6 cos(wt)?:",
            "options": {
                "A": "10 cm",
                "B": "2 cm",
                "C": "14 cm",
                "D": "3.5 cm"
            }
        },
        "narration_text": "Let's review the options. We need to select the correct magnitude for the combined oscillation."
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "What is the resultant amplitude of the motion x = 8 sin(wt) + 6 cos(wt)?:",
            "letter": "B",
            "options": {
                "A": "10 cm",
                "B": "2 cm",
                "C": "14 cm",
                "D": "3.5 cm"
            }
        },
        "narration_text": "Looking at Option B, two centimeters is obtained by incorrectly subtracting the coefficients of eight and six. Simple subtraction only applies if the components are in opposite phases, which is not true here."
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "What is the resultant amplitude of the motion x = 8 sin(wt) + 6 cos(wt)?:",
            "letter": "C",
            "options": {
                "A": "10 cm",
                "B": "2 cm",
                "C": "14 cm",
                "D": "3.5 cm"
            }
        },
        "narration_text": "Looking at Option C, fourteen centimeters is obtained by simply adding eight and six. However, because the sine and cosine components are ninety degrees out of phase, a direct arithmetic sum is incorrect."
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "What is the resultant amplitude of the motion x = 8 sin(wt) + 6 cos(wt)?:",
            "letter": "D",
            "options": {
                "A": "10 cm",
                "B": "2 cm",
                "C": "14 cm",
                "D": "3.5 cm"
            }
        },
        "narration_text": "Looking at Option D, three point five centimeters might come from an incorrect averaging approach, which has no physical basis in wave combinations. Option D is also incorrect."
    },
    {
        "visual_type": "cross_out",
        "visual_data": {
            "question": "What is the resultant amplitude of the motion x = 8 sin(wt) + 6 cos(wt)?:",
            "letters": ["B", "C", "D"],
            "options": {
                "A": "10 cm",
                "B": "2 cm",
                "C": "14 cm",
                "D": "3.5 cm"
            }
        },
        "narration_text": "Consequently, we eliminate Options B, C, and D from our possibilities."
    },
    {
        "visual_type": "answer_reveal",
        "visual_data": {
            "question": "What is the resultant amplitude of the motion x = 8 sin(wt) + 6 cos(wt)?:",
            "letter": "A",
            "correct_answer": "A",
            "explanation": "Orthogonal phasor addition yields R = sqrt(8^2 + 6^2) = 10 cm.",
            "options": {
                "A": "10 cm",
                "B": "2 cm",
                "C": "14 cm",
                "D": "3.5 cm"
            }
        },
        "narration_text": "This leaves Option A: ten centimeters. Since the sine and cosine oscillations are orthogonal, they combine as perpendicular vectors, yielding a root-sum-square amplitude of exactly ten centimeters. Option A is the correct answer."
    }
]

output_dir = "output/user_shm_explainer_slides"
os.makedirs(output_dir, exist_ok=True)

print("🚀 Starting compilation using standard Explainer Slides Pipeline for SHM...")
try:
    output_path, ledger = generate_explainer_slides_video(
        scenes=scenes,
        output_dir=output_dir,
        topic="Amplitude of SHM",
        job_id="user-shm-job",
        use_elevenlabs=True
    )
    print("\n🎉 VIDEO RENDER SUCCESS!")
    print(f"🎬 Output video saved to: {output_path}")
    print(f"📊 Resource Ledger: {ledger}")
except Exception as e:
    print(f"\n❌ Pipeline execution encountered an error: {e}")
    sys.exit(1)
