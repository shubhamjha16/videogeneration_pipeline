import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

def generate_lip_sync(video_path, audio_path, output_path):
    """
    Calls the ElevenLabs Lip-Sync API to animate a video with a given audio file.
    """
    if not ELEVENLABS_API_KEY:
        print("❌ Error: ELEVENLABS_API_KEY missing.")
        return None

    url = "https://api.elevenlabs.io/v1/video/lip-sync"
    headers = {"xi-api-key": ELEVENLABS_API_KEY}
    
    # Files to upload with context management
    try:
        with open(video_path, "rb") as video_file, open(audio_path, "rb") as audio_file:
            files = {
                "video": video_file,
                "audio": audio_file
            }
            print(f"👄 Launching ElevenLabs Lip-Sync job for {os.path.basename(audio_path)}...")
            response = requests.post(url, headers=headers, files=files)
            
            if response.status_code != 200:
                print(f"❌ Lip-Sync Job Failed: {response.text}")
                return None
    except Exception as e:
        print(f"❌ File/Network Error in Lip-Sync: {e}")
        return None
    
    job_id = response.json().get("job_id")
    print(f"⏳ Job created: {job_id}. Waiting for completion...")

    # Polling for completion
    poll_url = f"https://api.elevenlabs.io/v1/lip_sync/{job_id}"
    while True:
        poll_resp = requests.get(poll_url, headers=headers)
        status = poll_resp.json().get("status")
        
        if status == "finished":
            # Download the resulting video
            video_resp = requests.get(poll_resp.json().get("video_url"))
            with open(output_path, "wb") as f:
                f.write(video_resp.content)
            print(f"✅ Lip-Sync Success: {output_path}")
            return output_path
        elif status == "failed":
            print(f"❌ Lip-Sync Failed locally.")
            return None
        
        print("...")
        time.sleep(5) # Wait 5 seconds before polling again

if __name__ == "__main__":
    # Test path (will fail if files don't exist)
    # generate_lip_sync("base_avatar.mp4", "narration.m4a", "output_lip_sync.mp4")
    pass
