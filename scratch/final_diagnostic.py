
import re
import json

raw_json = """[{"title": "Concept Explanation", "description": "This scenario tests recognition of traumatic brain injury patterns on CT. When a patient is unconscious after trauma but CT shows *no midline shift* (no large focal mass lesion), the concern shifts toward *diffuse* injuries rather than a localized hematoma or large contusion."}, {"title": "Option Analysis", "description": "### Option A) cortical contusion\\nCortical contusions are focal bruises. ### Option B) Cerebral laceration\\nA laceration implies a tear. ### Option C) Multiple infarcts\\nInfarcts are ischemic. ### Option D) Diffuse axonal injuries\\nDAI classically presents with immediate loss of consciousness."}, {"title": "Final Answer", "description": "*Option D — Diffuse axonal injuries."}, {"title": "Citations", "description": "- *Lecture Notes: Radiology"}]"""

data = json.loads(raw_json)
raw_text = "\n".join([f"{s['title']}\n{s['description']}" for s in data])

print("--- DIAGNOSTIC START ---")
print(f"Buffer length: {len(raw_text)}")

# Test 1: Literal Search
print("\nTest 1: Literal search for markers")
for letter in ['A', 'B', 'C', 'D']:
    found = f"Option {letter})" in raw_text or f"{letter})" in raw_text
    print(f"   Searching for {letter})... Found? {found}")

# Test 2: Word Boundary Regex
print("\nTest 2: Word Boundary findall")
matches = re.findall(r'(?i)\b(?:Option\s+)?([A-D])[.\)]\s+', raw_text)
print(f"   Matches found: {matches}")

# Test 3: The Splitter
print("\nTest 3: The Splitter behavior")
chunks = re.split(r'(?i)\b(?:Option\s+)?([A-D])[.\)]\s+', raw_text)
print(f"   Split into {len(chunks)} chunks")
if len(chunks) > 1:
    for i in range(1, len(chunks), 2):
         print(f"   Chunk {i} (Letter): {chunks[i]}")

# Test 4: NO Word Boundary
print("\nTest 4: No Word Boundary findall")
matches = re.findall(r'(?i)(?:Option\s+)?([A-D])[.\)]\s+', raw_text)
print(f"   Matches found: {matches}")

print("\n--- DIAGNOSTIC END ---")
