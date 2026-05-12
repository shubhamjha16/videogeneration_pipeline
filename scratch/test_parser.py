from html_parser import parse_tony_html
import json

payload_v2 = [
    {
      "title": "Concept Explanation",
      "description": "Tetralogy of Fallot (ToF) is the most common cyanotic congenital heart defect. It consists of four distinct anatomical abnormalities: 1. Ventricular Septal Defect (VSD), 2. Pulmonary Stenosis, 3. Overriding Aorta, and 4. Right Ventricular Hypertrophy (RVH)."
    },
    {
      "title": "Option Analysis",
      "description": "A. ASD - not part of ToF. B. Left Ventricular Hypertrophy - wrong, it is RVH. C. Tetralogy of Fallot - includes VSD and Pulmonary Stenosis, CORRECT. D. Transposition of Great Arteries - separate defect."
    },
    {
      "title": "Final Answer",
      "description": "Option C: Tetralogy of Fallot"
    }
]

print("Testing parse_tony_html with ToF payload...")
result = parse_tony_html(payload_v2, topic_hint="Tetralogy of Fallot")

print(f"Content Type: {result['content_type']}")
print(f"Correct Answer: {result.get('correct_answer')}")
print(f"Correct Name: {result.get('correct_answer_name')}")
print(f"Options keys: {result.get('options', {}).keys()}")
print("\n--- Detailed Options ---")
print(json.dumps(result.get('options', {}), indent=2))
