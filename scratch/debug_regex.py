import re
import json

desc = "A. ASD - not part of ToF. B. Left Ventricular Hypertrophy - wrong, it is RVH. C. Tetralogy of Fallot - includes VSD and Pulmonary Stenosis, CORRECT. D. Transposition of Great Arteries - separate defect."

print(f"Interrogating string: {repr(desc)}")
print(f"Length: {len(desc)}")

# Test split
parts = re.split(r'\s*([A-D])[.\)]\s*', desc)
print(f"Parts count: {len(parts)}")
print(f"Parts: {parts}")

for i in range(1, len(parts), 2):
    if i + 1 < len(parts):
        letter = parts[i]
        content = parts[i+1]
        print(f"Detected: {letter} -> {content[:30]}...")
