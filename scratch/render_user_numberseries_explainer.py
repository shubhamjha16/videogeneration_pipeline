import os
import sys

# Ensure project root is in python path
sys.path.append(os.path.abspath("."))

from explainer_slides_generator import generate_explainer_slides_video

# Define scenes based on the user's Number Series logical reasoning JSON
scenes = [
    {
        "visual_type": "title_card",
        "visual_data": {
            "title": "Logical Reasoning: Number Series",
            "subtitle": "Finding the next terms of: 4, 8, 22, 12, 16, 22, 20, 24..."
        },
        "narration_text": "Hello student! Today we are exploring a logical reasoning question analyzing number patterns, specifically focusing on how sequences can be built from repeating positions rather than a single rule."
    },
    {
        "visual_type": "concept_explanation",
        "visual_data": {
            "title": "1. Repeating Positions Pattern",
            "subtitle": "Grouping the sequence into 3-term blocks",
            "bullets": [
                "Instead of a single rule, look at repeating positions.",
                "The sequence splits into repeating blocks of three terms.",
                "First position values of each block form their own progression.",
                "Second position values form their own progression.",
                "Third position values remain constant at 22."
            ]
        },
        "narration_text": "A common way to spot number patterns is to check whether the sequence is built from repeating positions rather than one single rule applied to all terms. Here, the numbers suggest a repeating block of three terms: the 3rd, 6th, and 9th terms follow a separate constant rule, while the others increase."
    },
    {
        "visual_type": "solution_steps",
        "visual_data": {
            "title": "2. Step-by-Step Block Analysis",
            "subtitle": "Applying progression rules",
            "bullets": [
                "Block 1: (4, 8, 22)",
                "Block 2: (12, 16, 22)  -> terms increase by 8 compared to Block 1",
                "Block 3: (20, 24, 22)  -> terms increase by 8 compared to Block 2",
                "Block 4 starts with first term: 20 + 8 = 28",
                "After 24, we need the 3rd term of Block 3 (22), and the 1st term of Block 4 (28)."
            ]
        },
        "narration_text": "Let's analyze the arithmetic progressions. Block one is 4, 8, 22. Block two increases the first two terms by 8, giving 12, 16, 22. Block three increases them by 8 again, giving 20, 24, 22. The term after 24 must be the constant 3rd-position value, which is 22. Then, the next block begins with the first-position progression, which is 20 plus 8, yielding 28. So the next two terms are 22 and 28."
    },
    {
        "visual_type": "mcq_layout",
        "visual_data": {
            "question": "What are the next two numbers in the series: 4, 8, 22, 12, 16, 22, 20, 24...?",
            "options": {
                "A": "28, 32",
                "B": "28, 22",
                "C": "22, 28",
                "D": "32, 36"
            }
        },
        "narration_text": "Our analysis reveals the next two terms are 22 followed by 28. Let's look at the multiple choice options to see which matches our findings."
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "What are the next two numbers in the series: 4, 8, 22, 12, 16, 22, 20, 24...?",
            "letter": "A",
            "options": {
                "A": "28, 32",
                "B": "28, 22",
                "C": "22, 28",
                "D": "32, 36"
            }
        },
        "narration_text": "Option A is 28, 32. This continues the increasing progressions of positions one and two, but completely skips the expected constant term of 22 that belongs in the 3rd position. Thus, Option A is incorrect."
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "What are the next two numbers in the series: 4, 8, 22, 12, 16, 22, 20, 24...?",
            "letter": "B",
            "options": {
                "A": "28, 32",
                "B": "28, 22",
                "C": "22, 28",
                "D": "32, 36"
            }
        },
        "narration_text": "Option B is 28, 22. This gets the two values in the wrong order. The repeating 3rd term must come first immediately after 24, rather than 28. Thus, Option B is incorrect."
    },
    {
        "visual_type": "cross_out",
        "visual_data": {
            "question": "What are the next two numbers in the series: 4, 8, 22, 12, 16, 22, 20, 24...?",
            "letters": ["A", "B", "D"],
            "options": {
                "A": "28, 32",
                "B": "28, 22",
                "C": "22, 28",
                "D": "32, 36"
            }
        },
        "narration_text": "We can safely eliminate Option A, Option B, and Option D."
    },
    {
        "visual_type": "answer_reveal",
        "visual_data": {
            "question": "What are the next two numbers in the series: 4, 8, 22, 12, 16, 22, 20, 24...?",
            "letter": "C",
            "correct_answer": "C",
            "explanation": "Grouping into 3-term blocks: (4, 8, 22), (12, 16, 22), (20, 24, 22), so the next term is 22. Then the next block starts with 20+8 = 28.",
            "options": {
                "A": "28, 32",
                "B": "28, 22",
                "C": "22, 28",
                "D": "32, 36"
            }
        },
        "narration_text": "This leaves Option C: 22, 28. This perfectly matches our 3-term block pattern, placing the repeating 3rd term first, followed by the +8 progression start of the next block. Option C is the correct answer."
    }
]

output_dir = "output/job_number_series"
os.makedirs(output_dir, exist_ok=True)

print("🚀 Starting compilation for Number Series logical reasoning lesson...")
try:
    output_path, ledger = generate_explainer_slides_video(
        scenes=scenes,
        output_dir=output_dir,
        topic="Number Series Logical Reasoning",
        job_id="number-series-mcq",
        use_elevenlabs=True
    )
    print("\n🎉 NUMBER SERIES REASONING VIDEO RENDER SUCCESS!")
    print(f"🎬 Output video saved to: {output_path}")
    print(f"📊 Resource Ledger: {ledger}")
except Exception as e:
    print(f"\n❌ Pipeline execution encountered an error: {e}")
    sys.exit(1)
