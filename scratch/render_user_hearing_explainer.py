import os
import sys

# Ensure project root is in python path
sys.path.append(os.path.abspath("."))

from gemini_omni_slides_generator import generate_gemini_omni_slides_video

# Define scenes based on the Rinne/Weber hearing test reasoning JSON
scenes = [
    {
        "visual_type": "title_card",
        "visual_data": {
            "title": "Hearing Tests: Rinne & Weber",
            "subtitle": "Interpreting Tuning Fork Diagnostics"
        },
        "narration_text": "Hello student! Today we are exploring the Rinne and Weber tuning fork tests, two essential clinical tools used to diagnose and differentiate between conductive and sensorineural hearing loss."
    },
    {
        "visual_type": "concept_explanation",
        "visual_data": {
            "title": "1. The Rinne Test",
            "subtitle": "Air vs. Bone Conduction",
            "bullets": [
                "Compares Air Conduction (AC) with Bone Conduction (BC).",
                "**Positive Rinne**: AC > BC (Normal or Sensorineural loss).",
                "**Negative Rinne**: BC > AC (Suggests Conductive loss).",
                "Right ear Rinne is **positive** in our patient."
            ]
        },
        "narration_text": "Let's first look at the Rinne test, which compares air conduction with bone conduction. A positive Rinne test means air conduction is louder than bone conduction. This is the normal state, but it is also seen in cases of sensorineural hearing loss. A negative Rinne test means bone conduction is stronger, suggesting a conductive hearing loss in that ear. In our patient, the right ear Rinne is positive, meaning the right ear does not show a conductive defect."
    },
    {
        "visual_type": "concept_explanation",
        "visual_data": {
            "title": "2. The Weber Test",
            "subtitle": "Lateralization of Sound",
            "bullets": [
                "Sound lateralizes to the **affected ear** in conductive deafness.",
                "Sound lateralizes to the **better ear** in sensorineural deafness.",
                "Patient's Weber lateralizes to the **left**.",
                "So either: **Left ear conductive loss** OR **Right ear sensorineural loss**."
            ]
        },
        "narration_text": "Next, we have the Weber test, which helps identify which side is affected. In conductive deafness, sound is heard louder in the affected ear. In sensorineural deafness, sound lateralizes to the better-hearing ear. Since our patient's Weber test lateralizes to the left, it means either the left ear has conductive loss, or the right ear has sensorineural loss."
    },
    {
        "visual_type": "mcq_layout",
        "visual_data": {
            "question": "A patient presents with positive Rinne test on the right ear, and the Weber test lateralizes to the left side. What is the most likely diagnosis?",
            "options": {
                "A": "Left side conductive deafness",
                "B": "Right side conductive deafness",
                "C": "Left side sensorineural deafness",
                "D": "Right side sensorineural deafness"
            }
        },
        "narration_text": "Now, let's analyze our options to identify the correct clinical interpretation of these combined tuning fork findings."
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "A patient presents with positive Rinne test on the right ear, and the Weber test lateralizes to the left side. What is the most likely diagnosis?",
            "letter": "A",
            "options": {
                "A": "Left side conductive deafness",
                "B": "Right side conductive deafness",
                "C": "Left side sensorineural deafness",
                "D": "Right side sensorineural deafness"
            }
        },
        "narration_text": "Option A is Left side conductive deafness. While left conductive loss can make Weber lateralize to the left, this paired pattern of a positive Rinne on the right with a Weber shifting to the left is classically used to indicate sensorineural loss in the opposite ear. Let's analyze the other options to be absolutely sure."
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "A patient presents with positive Rinne test on the right ear, and the Weber test lateralizes to the left side. What is the most likely diagnosis?",
            "letter": "B",
            "options": {
                "A": "Left side conductive deafness",
                "B": "Right side conductive deafness",
                "C": "Left side sensorineural deafness",
                "D": "Right side sensorineural deafness"
            }
        },
        "narration_text": "Option B is right-sided conductive deafness. This is incorrect because a right conductive loss would classically present with a negative Rinne test on the right, and the Weber test would lateralize to the right, which is the affected ear."
    },
    {
        "visual_type": "cross_out",
        "visual_data": {
            "question": "A patient presents with positive Rinne test on the right ear, and the Weber test lateralizes to the left side. What is the most likely diagnosis?",
            "letters": ["A", "B", "C"],
            "options": {
                "A": "Left side conductive deafness",
                "B": "Right side conductive deafness",
                "C": "Left side sensorineural deafness",
                "D": "Right side sensorineural deafness"
            }
        },
        "narration_text": "This allows us to safely eliminate Option A, Option B, and Option C."
    },
    {
        "visual_type": "answer_reveal",
        "visual_data": {
            "question": "A patient presents with positive Rinne test on the right ear, and the Weber test lateralizes to the left side. What is the most likely diagnosis?",
            "letter": "D",
            "correct_answer": "D",
            "explanation": "In right sensorineural deafness, the Rinne test remains positive in the affected ear (AC > BC), and the Weber test lateralizes to the opposite, better-hearing ear, which is the left side.",
            "options": {
                "A": "Left side conductive deafness",
                "B": "Right side conductive deafness",
                "C": "Left side sensorineural deafness",
                "D": "Right side sensorineural deafness"
            }
        },
        "narration_text": "This leaves Option D: Right-sided sensorineural deafness. In right sensorineural deafness, the Rinne test remains positive in the affected ear, and the Weber test lateralizes to the opposite, better-hearing ear, which is the left side here. Option D is the correct answer."
    }
]

output_dir = "output/job_hearing_loss"
os.makedirs(output_dir, exist_ok=True)

print("🚀 Starting compilation for Rinne and Weber Tests lesson...")
try:
    output_path, ledger = generate_gemini_omni_slides_video(
        scenes=scenes,
        output_dir=output_dir,
        topic="Rinne and Weber Tuning Fork Tests",
        job_id="hearing-loss-mcq-gemini-omni",
        use_elevenlabs=True
    )
    print("\n🎉 VIDEO RENDER SUCCESS!")
    print(f"🎬 Output video saved to: {output_path}")
    print(f"📊 Resource Ledger: {ledger}")
except Exception as e:
    print(f"\n❌ Pipeline execution encountered an error: {e}")
    sys.exit(1)
