import os
import sys
from dotenv import load_dotenv

# Load env variables from .env
load_dotenv()

# Add parent directory to path so we can import the local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from explainer_gemini_hybrid_slides_generator import generate_explainer_gemini_hybrid_slides_video

# Define a premium 4-scene masterclass representing all hybrid visual types
scenes = [
    {
        "visual_type": "concept_image",
        "visual_data": {
            "title": "Deriving Einstein's Energy Equation",
            "subtitle": "Relativistic Mass-Energy Equivalence",
            "bullets": ["E = m * c^2", "Relativistic momentum integration", "Mass-energy conversion constant"],
            "objects": ["Einstein formula", "energy conversion"]
        },
        "narration_text": "To understand the relation between mass and energy, we integrate relativistic momentum to derive Einstein's famous formula, E equals m c squared."
    },
    {
        "visual_type": "concept_image",
        "visual_data": {
            "title": "3D Ventricular Contraction Flow",
            "subtitle": "Clinical Cardiac Ejection Cycle",
            "bullets": ["Left ventricle squeezing blood", "Mitral valve closing under pressure", "Aortic valve opening for ejection"],
            "objects": ["clinical heart model", "blood flow arrows"]
        },
        "narration_text": "During ventricular systole, the left ventricle contracts, forcing the mitral valve to close and ejecting blood rapidly through the aortic valve."
    },
    {
        "visual_type": "concept_image",
        "visual_data": {
            "title": "Comparison of Subatomic Particles",
            "subtitle": "Protons, Neutrons, and Electrons",
            "bullets": [
                "Protons: Positive charge, mass 1 AMU, inside nucleus",
                "Neutrons: Neutral charge, mass 1 AMU, inside nucleus",
                "Electrons: Negative charge, negligible mass, outer orbit"
            ],
            "objects": ["particle comparison table", "atomic structure infographic"]
        },
        "narration_text": "This static matrix highlights the fundamental differences in charge, mass, and location between protons, neutrons, and electrons."
    },
    {
        "visual_type": "mcq_layout",
        "visual_data": {
            "question": "Which particle is responsible for forming chemical bonds between atoms?",
            "options": {
                "A": "Proton",
                "B": "Neutron",
                "C": "Electron",
                "D": "Alpha Particle"
            },
            "letter": "C",
            "explanation": "Electrons residing in the outermost valence shell are shared or transferred to form chemical bonds."
        },
        "narration_text": "Therefore, the correct answer is C, as valence electrons drive all atomic bonding."
    }
]

output_dir = "output/test_hybrid_slides"
topic = "Relativity Cardiac Chemistry Review"

print("🚀 Starting 4-Scene Master Showcase for Explainer Gemini Hybrid Slides...")
try:
    video_path, ledger = generate_explainer_gemini_hybrid_slides_video(
        scenes=scenes,
        output_dir=output_dir,
        topic=topic,
        job_id="test-master-run",
        use_elevenlabs=False, # Use local TTS/gTTS fallback to preserve ElevenLabs quota
        subject="physics"
    )
    print("\n✅ Verification Test Successful!")
    print(f"🎥 Generated Video Path: {video_path}")
    print(f"📊 Resource Ledger: {ledger}")
except Exception as e:
    print(f"\n❌ Verification Test Failed: {e}")
    sys.exit(1)
