import os
import sys
from dotenv import load_dotenv

# Load env variables from .env
load_dotenv()

# Add parent directory to path so we can import the local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gemini_omni_slides_generator import generate_gemini_omni_slides_video

# Define a premium 2-scene 3D explainer slides input
scenes = [
    {
        "visual_type": "title_card",
        "visual_data": {
            "title": "Structure of the Atom",
            "subtitle": "The 3D Rutherford Scattering Model",
            "bullets": ["Gold foil experiment", "Alpha particle deflection", "Discovery of the atomic nucleus"]
        },
        "narration_text": "Rutherford scattered alpha particles against a thin sheet of gold foil, discovering that the atom is mostly empty space with a dense positive nucleus."
    },
    {
        "visual_type": "mcq_layout",
        "visual_data": {
            "question": "Which of the following is correct regarding Rutherford's atomic model?",
            "options": {
                "A": "Electrons reside in a positive pudding-like sphere.",
                "B": "The nucleus is extremely dense and positively charged.",
                "C": "Neutrons orbit the nucleus in circular paths.",
                "D": "Alpha particles never deflect."
            },
            "letter": "B",
            "explanation": "Rutherford's gold foil experiment proved the existence of a highly dense, positively charged center called the nucleus."
        },
        "narration_text": "Therefore, option B is correct because the nucleus contains almost the entire mass of the atom in an incredibly tiny, positively charged space."
    }
]

output_dir = "output/test_gemini_omni"
topic = "Rutherford Atomic Model"

print("🚀 Starting Local Gemini Omni 7th Pipeline verification test...")
try:
    # We will trigger it using gTTS fallback first to save ElevenLabs quota, or standard if configured
    video_path, ledger = generate_gemini_omni_slides_video(
        scenes=scenes,
        output_dir=output_dir,
        topic=topic,
        job_id="test-omni-run",
        use_elevenlabs=False # Use gTTS/local TTS to preserve ElevenLabs characters during development
    )
    print("\n✅ Verification Test Successful!")
    print(f"🎥 Generated Video Path: {video_path}")
    print(f"📊 Resource Ledger: {ledger}")
except Exception as e:
    print(f"\n❌ Verification Test Failed: {e}")
    sys.exit(1)
