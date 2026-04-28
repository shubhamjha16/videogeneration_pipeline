
import json
from html_parser import parse_tony_html

# THIS IS THE JSON YOU PROVIDED
raw_json = """[{"title": "Concept Explanation", "description": "This scenario tests recognition of traumatic brain injury patterns on CT. When a patient is unconscious after trauma but CT shows *no midline shift* (no large focal mass lesion), the concern shifts toward *diffuse* injuries rather than a localized hematoma or large contusion."}, {"title": "Option Analysis", "description": "### Option A) cortical contusion\\nCortical contusions are focal bruises. ### Option B) Cerebral laceration\\nA laceration implies a tear. ### Option C) Multiple infarcts\\nInfarcts are ischemic. ### Option D) Diffuse axonal injuries\\nDAI classically presents with immediate loss of consciousness."}, {"title": "Final Answer", "description": "*Option D — Diffuse axonal injuries."}, {"title": "Citations", "description": "- *Lecture Notes: Radiology"}]"""

result = parse_tony_html(raw_json)
# FOCUS ON THE OPTIONS AND THE CORRECT ANSWER
print(f"📊 Content Type: {result['content_type']}")
print(f"✅ Final Answer: {result['correct_answer']}")
print("📝 Options Extracted:")
for k, v in result['options'].items():
    print(f"   [{k}] -> {v['name']}")
