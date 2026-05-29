import os
import sys
from dotenv import load_dotenv

# Load env variables from .env
load_dotenv()

# Add parent directory to path so we can import the local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from heygen_generator import generate_heygen_avatar

print("🚀 Starting Local HeyGen Mock Video Agent verification test...")

# Temporarily delete API Key from env if it exists to force the Mock generator fallback
original_api_key = os.environ.get("HEYGEN_API_KEY")
if original_api_key:
    del os.environ["HEYGEN_API_KEY"]

prompt = "This is a premium talking avatar educational mock video. We have refactored the engine to be 100% ImageMagick-free, preventing any local compilation and library errors!"
output_path = "output/test_heygen_mock/heygen_mock_agent.mp4"

try:
    video_path, duration = generate_heygen_avatar(
        prompt=prompt,
        output_path=output_path,
        job_id="test-heygen-mock-run"
    )
    
    print("\n✅ Verification Test Successful!")
    print(f"🎥 Generated Mock Video Path: {video_path}")
    print(f"⏱️ Video Duration: {duration:.2f} seconds")
    
    # Restore original API Key if it existed
    if original_api_key:
        os.environ["HEYGEN_API_KEY"] = original_api_key
        
except Exception as e:
    print(f"\n❌ Verification Test Failed: {e}")
    if original_api_key:
        os.environ["HEYGEN_API_KEY"] = original_api_key
    sys.exit(1)
