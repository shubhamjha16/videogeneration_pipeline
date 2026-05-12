import base64
import os
from openai import OpenAI

# 1. SETUP
api_key = "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"
client = OpenAI(api_key=api_key)

image_path = "/Users/apple/.gemini/antigravity/brain/0c165762-124d-4e4f-913a-7eb35efc926c/media__1778147327317.jpg"

def encode_image(path):
    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

base64_image = encode_image(image_path)

# 2. PROMPT
# Asking GPT-4o-vision for the vertical breakpoints of the 8 logical sections
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Look at this medical infographic. I need to divide it into 8 vertical sections for a video reveal. Please provide the 9 vertical boundary points (from 0.0 top to 1.0 bottom) as a Python list. Ensure the boundaries do NOT cut through any text boxes or headers. They should be placed in the empty space between sections.\n\nSections needed:\n1. DIC Heading\n2. DIC Concept Box\n3. DIC Pathophysiology Flowchart\n4. DIC Option Analysis\n5. DIC Final Answer\n6. EEG Heading + Concept\n7. EEG Flowchart + Waves\n8. EEG Option Analysis + Final Answer\n\nReturn ONLY the list of 9 floats, like [0.0, 0.12, 0.25, ... 1.0]."},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                },
            ],
        }
    ],
    max_tokens=100,
)

print(response.choices[0].message.content)
