import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

try:
    print("Testing gpt-image-2...")
    response = client.images.generate(
        model="gpt-image-2",
        prompt="A simple whiteboard sketch representing a clean grammatical comparison between direct and indirect speech.",
        size="1024x1024",
        quality="high",
        n=1,
    )
    print(f"gpt-image-2 Success! URL: {response.data[0].url}")
except Exception as e:
    print(f"gpt-image-2 Failed: {e}")
