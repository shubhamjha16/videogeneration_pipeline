import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from heygen_generator import generate_heygen_avatar

def test_heygen_logic():
    print("🏗️  Testing HeyGen Path Logic (Industrialization Test)")
    
    # Use a dummy audio file or a real one if exists
    test_audio = "tests/test_assets/test_audio.mp3"
    os.makedirs("tests/test_assets", exist_ok=True)
    
    # Create fake audio if missing
    if not os.path.exists(test_audio):
        import subprocess
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=f=440:d=2", test_audio], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    output_path = "output/test_heygen_render.mp4"
    os.makedirs("output", exist_ok=True)

    print(f"🎬 Running generator for topic: 'Test Avatar'...")
    # This should hit the HIGH-FIDELITY MOCK because we haven't set the key yet
    result = generate_heygen_avatar("This is a test of the HeyGen industrialization path.", test_audio, output_path)
    
    if os.path.exists(result):
        print(f"✅ SUCCESS: Generated asset at {result}")
        # Verify file size
        size = os.path.getsize(result)
        print(f"📊 File Size: {size / 1024 / 1024:.2f} MB")
    else:
        print("❌ FAILURE: No asset generated.")

if __name__ == "__main__":
    test_heygen_logic()
