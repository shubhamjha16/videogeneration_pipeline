import os
import base64
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

image_names = [
    "media__1778938401123.png",
    "media__1778938417516.png",
    "media__1778938436704.png",
    "media__1778938450471.png",
    "media__1778938465827.png"
]

brain_dir = "/Users/apple/.gemini/antigravity/brain/880c4146-29cb-4a83-a684-4ce33f9f6ccb"

for img_name in image_names:
    img_path = os.path.join(brain_dir, img_name)
    if not os.path.exists(img_path):
        print(f"File not found: {img_path}")
        continue
    
    with open(img_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
    print(f"\n--- Analyzing {img_name} ---")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this educational slide image in detail. Focus on: 1) Overall layout structure, 2) Visual style/aesthetic (colors, fonts, margins), 3) The nature and complexity of the diagrams/illustrations/visuals used, 4) The balance between text and visuals, 5) How text elements (titles, headers, bullet points) are formatted and styled. We want to program DALL-E 3 (gpt-image-2) to generate educational slides that perfectly match this standard."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=600
        )
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"Error analyzing image: {e}")
