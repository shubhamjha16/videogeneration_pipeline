from knowledge_vector_store import retrieve_related_research
import os

print("Testing KB retrieval and logging...")
hits = retrieve_related_research(
    "Ejection Fraction", 
    node="test_script", 
    job_id="test_job_123", 
    render_mode="manim"
)

if hits:
    print(f"Success! Hits found: {len(hits)}")
else:
    print("No hits found (expected if DB is empty or similarity low).")

log_path = "output/kb_retrievals.jsonl"
if os.path.exists(log_path):
    print(f"Log file created: {log_path}")
    with open(log_path, "r") as f:
        print("Log content:")
        print(f.read())
else:
    print("Log file NOT found.")
