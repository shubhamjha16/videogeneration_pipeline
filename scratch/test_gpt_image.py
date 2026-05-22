import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

try:
    print("Testing gpt-image-2...")
    response = client.images.generate(
        model="gpt-image-2",
        prompt="A simple study note about heart failure.",
        size="1024x1792",
        quality="high",
        n=1,
    )
    print(f"gpt-image-2 Success!")
    print(f"Response: {response}")
    if response.data:
        print(f"URL: {response.data[0].url}")
    else:
        print("No data in response")
except Exception as e:
    print(f"gpt-image-2 Failed: {e}")
