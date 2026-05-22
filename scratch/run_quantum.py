import os
import sys

# Ensure parent directory is in path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from autonomous_graph import app, TonyState

# Create input file
with open("quantum.txt", "w") as f:
    f.write("Explain the basics of quantum computing, qubits, and superposition for a presentation.")

# Initial state for the pipeline
initial_state = {
    "topic": "Quantum Computers",
    "raw_input": "Explain the basics of quantum computing, qubits, and superposition for a presentation.",
    "source_type": "markdown",
    "video_type": "educational",
    "render_mode": "presentation",
    "with_avatar": False,
    "use_elevenlabs": False,
    "avatar_type": "logo",
    "overrides": {
        "render_mode": "presentation",
        "enable_ambient": True
    },
    "job_id": "quantum_presentation_001",
    "attempt_count": 0,
    "ppt_attempt_count": 0,
    "no_vision": False,
    "research_count": 0,
}

print("Starting video generation pipeline for Quantum Computers in presentation mode...")

try:
    final_state = app.invoke(initial_state)
    print("\n✅ Pipeline completed successfully.")
    print(f"Output Video Path: {final_state.get('output_path')}")
except Exception as e:
    print(f"\n❌ Pipeline failed: {e}")
