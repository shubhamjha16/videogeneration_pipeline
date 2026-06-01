import os
import sys

# Ensure project root is in python path
sys.path.append(os.path.abspath("."))

from explainer_slides_generator import generate_explainer_slides_video

# Define scenes for the Active/Passive voice English MCQ lesson
scenes = [
    {
        "visual_type": "title_card",
        "visual_data": {
            "title": "Active and Passive Voice",
            "subtitle": "Transforming: 'We prohibit smoking'"
        },
        "narration_text": "Hello student! I'm Tony, your AI English teacher. Today we are exploring a key concept in grammar: transforming active voice sentences into the passive voice, focusing on general rules and stative verbs."
    },
    {
        "visual_type": "concept_explanation",
        "visual_data": {
            "title": "Active vs. Passive Voice",
            "subtitle": "Understanding the Subject Action flow",
            "bullets": [
                "Active: Subject performs the action. (We prohibit smoking)",
                "Passive: Subject receives the action. (Smoking is prohibited)",
                "Focus shifts: Object of active becomes subject of passive",
                "Rule: Use form of 'to be' plus past participle"
            ]
        },
        "narration_text": "In the active voice, the subject performs the action. In 'We prohibit smoking', 'We' is the subject and 'smoking' is the object. In the passive voice, the subject receives the action, shifting the focus to 'smoking' as the new subject."
    },
    {
        "visual_type": "mcq_layout",
        "visual_data": {
            "question": "What is the passive voice form of: 'We prohibit smoking'?",
            "options": {
                "A": "Smoking is being prohibited.",
                "B": "Smoking has been prohibited.",
                "C": "Smoking will be prohibited.",
                "D": "Smoking is prohibited."
            }
        },
        "narration_text": "Now, let's analyze the multiple choice options to see which transformation correctly represents the passive voice form of 'We prohibit smoking' in the simple present tense."
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "What is the passive voice form of: 'We prohibit smoking'?",
            "letter": "A",
            "options": {
                "A": "Smoking is being prohibited.",
                "B": "Smoking has been prohibited.",
                "C": "Smoking will be prohibited.",
                "D": "Smoking is prohibited."
            }
        },
        "narration_text": "Option A says 'Smoking is being prohibited'. This continuous passive form implies the action is happening right now, whereas the original sentence is a general rule. So, Option A is incorrect."
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "What is the passive voice form of: 'We prohibit smoking'?",
            "letter": "B",
            "options": {
                "A": "Smoking is being prohibited.",
                "B": "Smoking has been prohibited.",
                "C": "Smoking will be prohibited.",
                "D": "Smoking is prohibited."
            }
        },
        "narration_text": "Option B says 'Smoking has been prohibited'. This uses the present perfect passive, which suggests a past completed action rather than a permanent general rule. Thus, Option B is incorrect."
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "What is the passive voice form of: 'We prohibit smoking'?",
            "letter": "C",
            "options": {
                "A": "Smoking is being prohibited.",
                "B": "Smoking has been prohibited.",
                "C": "Smoking will be prohibited.",
                "D": "Smoking is prohibited."
            }
        },
        "narration_text": "Option C uses 'will be prohibited', which shifts the tense from the present into the future. Since the original active voice statement is in the simple present, Option C is also incorrect."
    },
    {
        "visual_type": "cross_out",
        "visual_data": {
            "question": "What is the passive voice form of: 'We prohibit smoking'?",
            "letters": ["A", "B", "C"],
            "options": {
                "A": "Smoking is being prohibited.",
                "B": "Smoking has been prohibited.",
                "C": "Smoking will be prohibited.",
                "D": "Smoking is prohibited."
            }
        },
        "narration_text": "Therefore, we can confidently eliminate Option A, Option B, and Option C."
    },
    {
        "visual_type": "answer_reveal",
        "visual_data": {
            "question": "What is the passive voice form of: 'We prohibit smoking'?",
            "letter": "D",
            "correct_answer": "D",
            "explanation": "Smoking is prohibited uses the simple present passive voice, matching the general rule meaning of the original sentence.",
            "options": {
                "A": "Smoking is being prohibited.",
                "B": "Smoking has been prohibited.",
                "C": "Smoking will be prohibited.",
                "D": "Smoking is prohibited."
            }
        },
        "narration_text": "This leaves Option D: 'Smoking is prohibited'. This is the simple present passive form, which perfectly matches the meaning of the original general rule. Option D is the correct answer."
    }
]

output_dir = "output/job_active_passive_voice"
os.makedirs(output_dir, exist_ok=True)

print("🚀 Starting compilation for English Active/Passive Voice lesson...")
try:
    output_path, ledger = generate_explainer_slides_video(
        scenes=scenes,
        output_dir=output_dir,
        topic="Active and Passive Voice",
        job_id="active-passive-voice-english-mcq",
        use_elevenlabs=True
    )
    print("\n🎉 ENGLISH VIDEO RENDER SUCCESS!")
    print(f"🎬 Output video saved to: {output_path}")
    print(f"📊 Resource Ledger: {ledger}")
except Exception as e:
    print(f"\n❌ Pipeline execution encountered an error: {e}")
    sys.exit(1)
