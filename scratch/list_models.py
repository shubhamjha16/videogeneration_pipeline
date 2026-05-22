import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

try:
    models = client.models.list()
    print("Available Models:")
    for m in models.data:
        if "dalle" in m.id or "gpt" in m.id:
            print(f"- {m.id}")
except Exception as e:
    print(f"Failed to list models: {e}")
