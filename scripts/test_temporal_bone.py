import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from autonomous_graph import app

def test_temporal_bone():
    topic = "Temporal Bone Air Cell Groups MCQ"
    raw_input = """
    <h1>Explanation of Temporal Bone Air Cell Groups</h1>
    <p>
      The temporal bone is a complex structure comprising several parts that are pneumatized (contain air cells). These air cell groups are incorporated in various regions of the temporal bone and play an important role in the resonance and ventilation of the middle ear, as well as in reducing the weight of the skull. The main pneumatized regions include the mastoid air cell system, petrous, retrofacial, and hypotympanic groups. These air cells are categorized based on their anatomical locations within the temporal bone. It is critical to differentiate between these genuine air cell groups and anatomical structures that might be confused as such.
    </p>
    <h2>Analysis of the Options</h2>
    <h3>Option A: Petrosal</h3>
    <p>
      The “petrosal” air cells refer to the air cells found within the petrous portion of the temporal bone. These cells, often called the petrous apex air cells, are a recognized group in the context of temporal bone pneumatization. Therefore, this option correctly represents one of the temporal bone air cell groups.
    </p>
    <h3>Option B: Retrofacial</h3>
    <p>
      Retrofacial air cells are part of the mastoid air cell system. They are located posterior to the labyrinthine facial nerve area. This group forms a distinct set of pneumatized cells in the region. Hence, this option is an accurate air cell group within the temporal bone.
    </p>
    <h3>Option C: Promontory</h3>
    <p>
      The promontory is defined as the rounded bony eminence on the medial wall of the middle ear. It is formed by the basal turn of the cochlea. Unlike the other options, the promontory is not a group of air cells; it is simply a bony landmark. Therefore, this option does not belong to the temporal bone air cell groups.
    </p>
    <h3>Option D: Hypotympanic</h3>
    <p>
      Hypotympanic air cells are located inferior to the tympanic cavity. This group of air cells forms part of the overall pneumatization of the temporal bone. As such, this is correctly considered one of the temporal bone air cell groups.
    </p>
    <h2>Final Answer</h2>
    <p>
      Based on the analysis of each option, the correct answer is Option C: Promontory.
    </p>
    <h2>Citations</h2>
    <h3>Books</h3>
    <ul>
      <li>Gray’s Anatomy for Students – which details the temporal bone subdivisions and pneumatization.</li>
      <li>Rudolf Fahlbusch's Complete Otolaryngology – provides an in-depth look into the anatomy of the temporal bone and middle ear structures.</li>
    </ul>
    """
    
    print(f"🚀 Triggering Explainer Slides pipeline for: {topic}")
    
    # We force explainer_slides mode via overrides
    initial_state = {
        "raw_input": raw_input,
        "topic": topic,
        "job_id": "test_temporal_bone_" + str(os.getpid()),
        "overrides": {"render_mode": "explainer_slides"},
        "use_elevenlabs": True,
        
        # Initialize other required state fields
        "attempt_count": 0,
        "ppt_attempt_count": 0,
        "no_vision": False,
        "with_avatar": False,
        "ledger": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "elevenlabs_chars": 0,
            "heygen_seconds": 0
        },
        "rejected_attempts": [],
        "media_manifest": [],
        "research_count": 0
    }
    
    final_state = app.invoke(initial_state)
    
    print("\n🏁 Pipeline Finished!")
    print(f"Output Path: {final_state.get('output_path')}")
    print(f"Video URL: {final_state.get('video_url')}")
    print(f"Ledger: {final_state.get('ledger')}")

if __name__ == "__main__":
    test_temporal_bone()
