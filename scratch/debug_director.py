import json
from director_agent import run_director

with open("scratch/integrated_lesson.json") as f:
    raw = json.load(f)[0]

# Standardize as the graph does
parsed = {
    "topic": "Cardiac Output Analysis",
    "subject": "unknown",
    "content_type": "numerical",
    "concept": "### Concept: Cardiac Output\nCardiac output is the total volume of blood pumped by the heart per minute. It is the product of heart rate and stroke volume.\n\n### Clinical Calculation\nGiven a patient with a Heart Rate (HR) of 70 bpm and a Stroke Volume (SV) of 75 mL, calculate the Cardiac Output (CO).\n1. CO = HR x SV\n2. CO = 70 x 75\n3. CO = 5250 mL/min\n4. CO = 5.25 L/min",
    "key_points": [],
    "options": {},
    "sections": {}
}

print("🎬 Running Director Debug...")
output, usage = run_director(parsed)
print(f"Reasoning: {output.decision_reasoning}")
