import os
from openai import OpenAI
from dotenv import load_dotenv
import json

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

try:
    print("Testing gpt-image-2 and checking all response fields...")
    # Use raw request if possible to see everything
    response = client.images.with_raw_response.generate(
        model="gpt-image-2",
        prompt="A simple study note about heart failure.",
        size="1024x1792",
        quality="high",
        n=1
    )
    print("Success!")
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {response.headers}")
    print(f"Content: {response.text[:1000]}") # Only print first 1000 chars
except Exception as e:
    print(f"Failed: {e}")
