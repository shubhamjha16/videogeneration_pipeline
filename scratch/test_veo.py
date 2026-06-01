import os
import time
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY", "")

try:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    
    model_name = "veo-3.0-fast-generate-001"
    print(f"Testing video generation with model: {model_name}...")
    
    operation = client.models.generate_videos(
        model=model_name,
        prompt="A cute corporate logo animation with simple shapes rotating on a blue background",
        config=types.GenerateVideosConfig(
            aspect_ratio="16:9",
            duration_seconds=6,
        ),
    )
    
    print("Operation started successfully!")
    print(f"Operation Name: {operation.name}")
    
    # Poll to see if it actually progresses
    for i in range(40):
        time.sleep(10)
        operation = client.operations.get(operation)
        print(f"Poll {i+1}: done={operation.done}")
        if operation.done:
            break
            
    print("\n--- Operation Details ---")
    print(f"Done: {operation.done}")
    print(f"Error: {operation.error}")
    print(f"Response Type: {type(operation.response)}")
    if operation.response:
        print(f"Response Attributes: {dir(operation.response)}")
        print(f"Response: {operation.response}")
        if hasattr(operation.response, "generated_videos") and operation.response.generated_videos:
            gen_video = operation.response.generated_videos[0]
            print(f"Video Type: {type(gen_video)}")
            print(f"Video Attributes: {dir(gen_video)}")
            print(f"Video: {gen_video}")
            if hasattr(gen_video, "video"):
                print(f"Inner Video Type: {type(gen_video.video)}")
                print(f"Inner Video Attributes: {dir(gen_video.video)}")
                print(f"Inner Video: {gen_video.video}")
except Exception as e:
    print(f"Error testing model: {e}")
