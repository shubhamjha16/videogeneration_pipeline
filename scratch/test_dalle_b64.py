import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

try:
    print("Testing dall-e-3 with b64_json...")
    response = client.images.generate(
        model="dall-e-3",
        prompt="A simple red apple on a dark background",
        size="1024x1024",
        n=1,
        response_format="b64_json"
    )
    print("Success!")
except Exception as e:
    print(f"Failed: {e}")
