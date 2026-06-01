import os
import sys

# Ensure project root is in python path
sys.path.append(os.path.abspath("."))

from explainer_slides_generator import generate_explainer_slides_video

# Define scenes for the direct/indirect speech English MCQ lesson
scenes = [
    {
        "visual_type": "title_card",
        "visual_data": {
            "title": "Direct and Indirect Speech",
            "subtitle": "Transforming: 'He bade his friends goodbye'"
        },
        "narration_text": "Hello student! Today we are exploring a key concept in grammar: transforming sentences from indirect speech to direct speech while preserving the original meaning and tone."
    },
    {
        "visual_type": "concept_explanation",
        "visual_data": {
            "title": "Direct vs. Indirect Speech",
            "subtitle": "Understanding reported utterances",
            "bullets": [
                "Direct: Repeats the speaker's exact words in quotation marks.",
                "Indirect: Reports the essence of speech without exact quotes.",
                "Original sentence uses 'bade... goodbye' (a farewell).",
                "Must convert this indirect farewell back to direct speech."
            ]
        },
        "narration_text": "Direct speech reports actual words spoken using quotation marks, while indirect speech conveys the essence of the statement without quotation marks. Converting between them requires shifting the reporting verbs and pronouns to maintain original meaning."
    },
    {
        "visual_type": "mcq_layout",
        "visual_data": {
            "question": "What is the correct direct speech form of: 'He bade his friends goodbye'?",
            "options": {
                "A": "“I will see you later” he told his friends.",
                "B": "“I am bidding you Goodbye.”",
                "C": "He said, “Goodbye, my friends.”",
                "D": "“Goodbye, my friends” he was saying to them."
            }
        },
        "narration_text": "Let's analyze the options to find the correct direct speech conversion that matches the meaning of bidding goodbye."
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "What is the correct direct speech form of: 'He bade his friends goodbye'?",
            "letter": "A",
            "options": {
                "A": "“I will see you later” he told his friends.",
                "B": "“I am bidding you Goodbye.”",
                "C": "He said, “Goodbye, my friends.”",
                "D": "“Goodbye, my friends” he was saying to them."
            }
        },
        "narration_text": "Option A says 'I will see you later' he told his friends. This refers to a future meeting and doesn't capture the finality of a farewell. So Option A is incorrect."
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "What is the correct direct speech form of: 'He bade his friends goodbye'?",
            "letter": "B",
            "options": {
                "A": "“I will see you later” he told his friends.",
                "B": "“I am bidding you Goodbye.”",
                "C": "He said, “Goodbye, my friends.”",
                "D": "“Goodbye, my friends” he was saying to them."
            }
        },
        "narration_text": "Option B is 'I am bidding you Goodbye.' While literal, it uses the present continuous tense, which is unnatural and unidiomatic for saying goodbye. Thus, Option B is incorrect."
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "What is the correct direct speech form of: 'He bade his friends goodbye'?",
            "letter": "C",
            "options": {
                "A": "“I will see you later” he told his friends.",
                "B": "“I am bidding you Goodbye.”",
                "C": "He said, “Goodbye, my friends.”",
                "D": "“Goodbye, my friends” he was saying to them."
            }
        },
        "narration_text": "Option C says He said, 'Goodbye, my friends.' This correctly transforms the reporting verb 'bade' into the direct exclamation 'Goodbye, my friends' introduced by 'He said'. This perfectly captures the true essence of the original indirect statement."
    },
    {
        "visual_type": "cross_out",
        "visual_data": {
            "question": "What is the correct direct speech form of: 'He bade his friends goodbye'?",
            "letters": ["A", "B", "D"],
            "options": {
                "A": "“I will see you later” he told his friends.",
                "B": "“I am bidding you Goodbye.”",
                "C": "He said, “Goodbye, my friends.”",
                "D": "“Goodbye, my friends” he was saying to them."
            }
        },
        "narration_text": "Therefore, we can safely eliminate Option A, Option B, and Option D."
    },
    {
        "visual_type": "answer_reveal",
        "visual_data": {
            "question": "What is the correct direct speech form of: 'He bade his friends goodbye'?",
            "letter": "C",
            "correct_answer": "C",
            "explanation": "He said, 'Goodbye, my friends' properly converts 'He bade his friends goodbye' from indirect to direct speech, capturing the true meaning of bidding farewell.",
            "options": {
                "A": "“I will see you later” he told his friends.",
                "B": "“I am bidding you Goodbye.”",
                "C": "He said, “Goodbye, my friends.”",
                "D": "“Goodbye, my friends” he was saying to them."
            }
        },
        "narration_text": "This leaves Option C: He said, 'Goodbye, my friends.' It represents the natural, grammatically correct direct speech transformation of the original indirect statement. Option C is the correct answer."
    }
]

output_dir = "output/job_direct_indirect_speech"
os.makedirs(output_dir, exist_ok=True)

print("🚀 Starting compilation for English Direct/Indirect Speech lesson...")
try:
    output_path, ledger = generate_explainer_slides_video(
        scenes=scenes,
        output_dir=output_dir,
        topic="Direct and Indirect Speech",
        job_id="direct-indirect-speech-english-mcq",
        use_elevenlabs=True
    )
    print("\n🎉 ENGLISH VIDEO RENDER SUCCESS!")
    print(f"🎬 Output video saved to: {output_path}")
    print(f"📊 Resource Ledger: {ledger}")
except Exception as e:
    print(f"\n❌ Pipeline execution encountered an error: {e}")
    sys.exit(1)
