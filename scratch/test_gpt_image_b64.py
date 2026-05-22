import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

try:
    print("Testing gpt-image-2 with b64_json...")
    response = client.images.generate(
        model="gpt-image-2",
        prompt="A simple study note about heart failure.",
        size="1024x1792",
        quality="high",
        n=1,
        response_format="b64_json"
    )
    print(f"gpt-image-2 Success!")
    if response.data[0].b64_json:
        print("Got B64 JSON!")
    else:
        print("B64 JSON is None")
except Exception as e:
    print(f"gpt-image-2 Failed: {e}")
