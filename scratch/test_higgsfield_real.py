import os
import sys
from dotenv import load_dotenv

# Load env from .env file
load_dotenv()

from higgsfield_generator import generate_higgsfield_video

def test_single_gen():
    prompt = "A high-speed train traveling through a futuristic tunnel of light"
    output = "test_gen_video.mp4"
    print(f"Testing real Higgsfield generation for: {prompt}")
    try:
        path = generate_higgsfield_video(prompt, output)
        if os.path.exists(path):
            print(f"SUCCESS: Video generated at {path}")
            # Check if it's the placeholder (ffmpeg based) or real (requests based)
            # Placeholder is 2s, real is 5s
            import moviepy.editor as mp
            clip = mp.VideoFileClip(path)
            print(f"Video duration: {clip.duration}s")
            clip.close()
        else:
            print("FAILURE: File not found.")
    except Exception as e:
        print(f"ERROR during test: {e}")

if __name__ == "__main__":
    test_single_gen()
