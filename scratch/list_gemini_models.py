import os
import requests
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

url = f"https://generativelanguage.googleapis.com/v1/models?key={GEMINI_API_KEY}"
response = requests.get(url)
print(response.status_code)
print(response.json())
