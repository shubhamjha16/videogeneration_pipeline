import os
import sys

# Ensure project root is in python path
sys.path.append(os.path.abspath("."))

from explainer_slides_generator import generate_explainer_slides_video

# Define scenes based on the user's chemistry flame test curriculum JSON
scenes = [
    {
        "visual_type": "title_card",
        "visual_data": {
            "title": "Metal Cation Identification",
            "subtitle": "Advanced Flame Test Signature Colors"
        },
        "narration_text": "Welcome to today's chemistry lab session. Today, we will study flame tests, a classic analytical method used to identify metal cations based on the unique, vibrant wavelengths of light they emit when excited by heat."
    },
    {
        "visual_type": "concept_explanation",
        "visual_data": {
            "title": "1. Flame Test Principles",
            "subtitle": "Electron excitation and emission",
            "bullets": [
                "Heat excites electrons in the metal cations",
                "Electrons emit light when returning to ground state",
                "Wavelengths produce distinct flame colors"
            ],
            "objects": ["vibrant flame visual illustration", "energy level transitions chart"]
        },
        "narration_text": "First, let's learn the science. Heating excites valence electrons in the metal ions, pushing them to higher orbitals. As these electrons fall back to their lower ground states, they emit electromagnetic radiation. The specific wavelengths of this light produce a characteristic flame signature."
    },
    {
        "visual_type": "solution_steps",
        "visual_data": {
            "title": "2. Analyzing Cation Signatures",
            "subtitle": "Matching observations to elements",
            "bullets": [
                "Observation: Green flame with a blue center",
                "Barium produces an apple-green flame without a blue center",
                "Copper salts yield a blue-green flame with hotter blue cores"
            ],
            "objects": ["bunsen burner diagram", "sketched copper sulfate structure"]
        },
        "narration_text": "Next, let's analyze the clinical observation: a green flame featuring a distinct blue center. While barium salts emit a simple apple-green color, copper cations produce a composite blue-green flame, where the hotter, inner mantle of the flame appears distinctly blue."
    },
    {
        "visual_type": "mcq_layout",
        "visual_data": {
            "question": "Which metal cation classically produces a green flame with a blue center in a flame test?:",
            "options": {
                "A": "Cu2+",
                "B": "Sr2+",
                "C": "Ba2+",
                "D": "Ca2+"
              }
        },
        "narration_text": "Let's review the options. We need to match this signature blue-centered green flame to the correct metal ion."
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "Which metal cation classically produces a green flame with a blue center in a flame test?:",
            "letter": "B",
            "options": {
                "A": "Cu2+",
                "B": "Sr2+",
                "C": "Ba2+",
                "D": "Ca2+"
              }
        },
        "narration_text": "Analyzing Option B: strontium ions produce a bright crimson red flame, which is completely inconsistent with a green flame. Thus, Option B is incorrect."
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "Which metal cation classically produces a green flame with a blue center in a flame test?:",
            "letter": "C",
            "options": {
                "A": "Cu2+",
                "B": "Sr2+",
                "C": "Ba2+",
                "D": "Ca2+"
              }
        },
        "narration_text": "Analyzing Option C: barium typically gives a pale apple-green flame, but it lacks the characteristic hot blue center described in the observation. Option C is therefore incorrect."
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "Which metal cation classically produces a green flame with a blue center in a flame test?:",
            "letter": "D",
            "options": {
                "A": "Cu2+",
                "B": "Sr2+",
                "C": "Ba2+",
                "D": "Ca2+"
              }
        },
        "narration_text": "Analyzing Option D: calcium cations produce a brick-red or orange-red flame. This does not match a green flame at all, making Option D incorrect."
    },
    {
        "visual_type": "cross_out",
        "visual_data": {
            "question": "Which metal cation classically produces a green flame with a blue center in a flame test?:",
            "letters": ["B", "C", "D"],
            "options": {
                "A": "Cu2+",
                "B": "Sr2+",
                "C": "Ba2+",
                "D": "Ca2+"
              }
        },
        "narration_text": "Consequently, we eliminate Option B, Option C, and Option D from our options."
    },
    {
        "visual_type": "answer_reveal",
        "visual_data": {
            "question": "Which metal cation classically produces a green flame with a blue center in a flame test?:",
            "letter": "A",
            "correct_answer": "A",
            "explanation": "Copper salts produce a blue-green flame with hotter inner regions appearing distinctly blue.",
            "options": {
                "A": "Cu2+",
                "B": "Sr2+",
                "C": "Ba2+",
                "D": "Ca2+"
              }
        },
        "narration_text": "This leaves Option A: copper two plus. Copper salts typically impart a signature green outer flame with a beautiful, hot, blue-colored center mantle. Option A is our correct answer."
    }
]

output_dir = "output/user_flame_explainer_slides"
os.makedirs(output_dir, exist_ok=True)

print("🚀 Starting compilation using standard Explainer Slides Pipeline for flame tests...")
try:
    output_path, ledger = generate_explainer_slides_video(
        scenes=scenes,
        output_dir=output_dir,
        topic="Flame Tests Cations",
        job_id="user-flame-job",
        use_elevenlabs=True
    )
    print("\n🎉 VIDEO RENDER SUCCESS!")
    print(f"🎬 Output video saved to: {output_path}")
    print(f"📊 Resource Ledger: {ledger}")
except Exception as e:
    print(f"\n❌ Pipeline execution encountered an error: {e}")
    sys.exit(1)
