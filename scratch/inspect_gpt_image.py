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
    item = response.data[0]
    print(f"Item attributes: {dir(item)}")
    for attr in dir(item):
        if not attr.startswith("_"):
            print(f"- {attr}: {getattr(item, attr)}")
except Exception as e:
    print(f"gpt-image-2 Failed: {e}")
