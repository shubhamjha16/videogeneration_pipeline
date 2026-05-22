import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

try:
    print("Testing DALL-E 2...")
    response = client.images.generate(
        model="dall-e-2",
        prompt="A simple study note about heart failure.",
        size="1024x1024",
        n=1,
    )
    print(f"DALL-E 2 Success! URL: {response.data[0].url}")
except Exception as e:
    print(f"DALL-E 2 Failed: {e}")

try:
    print("\nTesting DALL-E 3...")
    response = client.images.generate(
        model="dall-e-3",
        prompt="A simple study note about heart failure.",
        size="1024x1024",
        n=1,
    )
    print(f"DALL-E 3 Success! URL: {response.data[0].url}")
except Exception as e:
    print(f"DALL-E 3 Failed: {e}")
