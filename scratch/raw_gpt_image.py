import os
from openai import OpenAI
from dotenv import load_dotenv
import json

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

try:
    print("Testing gpt-image-2 raw response...")
    response = client.images.generate(
        model="gpt-image-2",
        prompt="A simple study note about heart failure.",
        size="1024x1792",
        quality="high",
        n=1
    )
    print("Success!")
    print(f"Full Response JSON: {response.model_dump_json(indent=2)}")
except Exception as e:
    print(f"Failed: {e}")
