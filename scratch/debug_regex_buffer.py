
import json
import re
from html_parser import parse_tony_html
from bs4 import BeautifulSoup

# THE RAW PAYLOAD
raw_json = """[{"title": "Concept Explanation", "description": "This scenario tests recognition of traumatic brain injury patterns on CT. When a patient is unconscious after trauma but CT shows *no midline shift* (no large focal mass lesion), the concern shifts toward *diffuse* injuries rather than a localized hematoma or large contusion."}, {"title": "Option Analysis", "description": "### Option A) cortical contusion\\nCortical contusions are focal bruises. ### Option B) Cerebral laceration\\nA laceration implies a tear. ### Option C) Multiple infarcts\\nInfarcts are ischemic. ### Option D) Diffuse axonal injuries\\nDAI classically presents with immediate loss of consciousness."}, {"title": "Final Answer", "description": "*Option D — Diffuse axonal injuries."}, {"title": "Citations", "description": "- *Lecture Notes: Radiology"}]"""

# MANUALLY SIMULATE THE PARSER FLOW TO SEE THE BUFFER
data = json.loads(raw_json)
html_output = ""
for section in data:
    html_output += f"<h3>{section['title']}</h3>\n<p>{section['description']}</p>\n"

soup = BeautifulSoup(html_output, 'html.parser')
raw_text = soup.get_text(separator='\n')

print("--- RAW TEXT BUFFER START ---")
print(raw_text)
print("--- RAW TEXT BUFFER END ---")

# TEST THE NEW REGEX MANUALLY ON THIS BUFFER
matches = re.finditer(r'(?i)(?:^|[\n\.])\s*(?:[#*-]\s*)*(?:Option\s*)?([A-D])[.\)]\s+(.*?)(?=\s*(?:[\n\.])\s*(?:[#*-]\s*)*(?:Option\s*)?[A-D][.\)]|$)', raw_text, re.MULTILINE | re.DOTALL)
print("\n--- REGEX MATCHES ---")
for m in matches:
    print(f"Match Found: [{m.group(1)}] -> {m.group(2)[:20]}...")
