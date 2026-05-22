import os
import time
from openai import OpenAI, Timeout
from dotenv import load_dotenv

load_dotenv()

# Set up client with generous read timeout
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    timeout=Timeout(connect=5.0, read=90.0, write=5.0, pool=5.0)
)

try:
    print("🎨 Requesting gpt-image-2 with standard 1024x1024 size...")
    start_time = time.time()
    response = client.images.generate(
        model="gpt-image-2",
        prompt="A high-quality study note explaining Heart Failure, whiteboard style, with grid lines and a diagram of the heart.",
        size="1024x1024",
        n=1
    )
    elapsed = time.time() - start_time
    print(f"✅ Success! Took {elapsed:.2f} seconds.")
    print(f"Data: {response.data[0]}")
    if hasattr(response.data[0], 'url') and response.data[0].url:
        print(f"URL: {response.data[0].url}")
    if hasattr(response.data[0], 'b64_json') and response.data[0].b64_json:
        print("Got B64 JSON data!")
except Exception as e:
    print(f"❌ Failed: {e}")
