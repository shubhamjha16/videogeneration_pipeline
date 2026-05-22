import os
from openai import OpenAI
from dotenv import load_dotenv
import json
import base64

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

try:
    print("Testing gpt-image-2 via Multimodal Chat Completions...")
    # Futuristic multimodal call
    response = client.chat.completions.create(
        model="gpt-image-2",
        modalities=["text", "image"],
        messages=[
            {
                "role": "user",
                "content": "Generate a high-fidelity educational infographic about Heart Failure. Portrait layout, dense notes style.",
            }
        ],
    )
    
    print("Success!")
    print(f"Response Type: {type(response)}")
    
    # Inspect choices
    for i, choice in enumerate(response.choices):
        print(f"\nChoice {i}:")
        message = choice.message
        print(f"Message content: {message.content}")
        
        # Check for image in content list (multimodal response)
        if hasattr(message, "content") and isinstance(message.content, list):
            for part in message.content:
                print(f"- Part Type: {getattr(part, 'type', 'unknown')}")
                if getattr(part, "type", "") == "image":
                    print("Found Image Part!")
                    # Try to get base64
                    image_data = getattr(part, "image", None)
                    if image_data:
                        print("Found Image Data!")
                        # In some futuristic schemas, it might be in 'data' or 'base64'
                        b64 = getattr(image_data, "base64", None) or getattr(image_data, "data", None)
                        if b64:
                            print(f"Got Base64 (len: {len(b64)})")
                            with open("scratch/multimodal_test.png", "wb") as f:
                                f.write(base64.b64decode(b64))
                            print("Saved to scratch/multimodal_test.png")
        
        # Also check for legacy-style attachment if any
        if hasattr(message, "audio"): print("Found Audio!")
        if hasattr(message, "image"): print("Found Image!")

except Exception as e:
    print(f"Multimodal Chat Failed: {e}")
    import traceback
    traceback.print_exc()
