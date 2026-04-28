import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

try:
    print("Testing gpt-image-2 without response_format...")
    response = client.images.generate(
        model="gpt-image-2",
        prompt="A simple red apple on a dark background",
        size="1024x1024",
        n=1
    )
    print("Success!")
    print(f"URL: {response.data[0].url}")
except Exception as e:
    print(f"Failed: {e}")
