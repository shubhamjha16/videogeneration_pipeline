import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

def generate_lip_sync(video_path, audio_path, output_path, job_id: str = None):
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
            response = requests.post(url, headers=headers, files=files, timeout=60)
            
            if response.status_code != 200:
                print(f"❌ Lip-Sync Job Failed: {response.text}")
                return None
    except Exception as e:
        print(f"❌ File/Network Error in Lip-Sync: {e}")
        return None
    
    try:
        job_id = response.json().get("job_id")
        if not job_id:
            print("❌ Lip-Sync Job Failed: No job_id returned.")
            return None
    except Exception as e:
        print(f"❌ Lip-Sync JSON Parse Error: {e}")
        return None
    print(f"⏳ Job created: {job_id}. Waiting for completion...")

    # Polling for completion
    poll_url = f"https://api.elevenlabs.io/v1/video/lip-sync/{job_id}"
    max_attempts = 60
    for attempt in range(max_attempts):
        try:
            poll_resp = requests.get(poll_url, headers=headers, timeout=10)
            status = poll_resp.json().get("status")
            
            if status == "finished":
                # Download the resulting video
                video_url = poll_resp.json().get("video_url")
                if video_url:
                    video_resp = requests.get(video_url, timeout=30)
                    tmp_path = output_path + ".tmp"
                    try:
                        with open(tmp_path, "wb") as f:
                            f.write(video_resp.content)
                        os.replace(tmp_path, output_path)
                    finally:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
                    print(f"✅ Lip-Sync Success: {output_path}")
                    
                    # Record cost if job_id is provided
                    try:
                        from cost_tracker import LedgerManager
                        LedgerManager.record_vision_call(job_id, model="eleven-lip-sync") # Use vision call logic for now or add specific
                    except Exception as e:
                        print(f"⚠️ Failed to log lip-sync cost: {e}")

                    return output_path
                else:
                    print("❌ Lip-Sync finished but no video_url provided.")
                    return None
            elif status == "failed":
                print(f"❌ Lip-Sync Failed locally.")
                return None
                
        except Exception as e:
            print(f"⚠️ Lip-Sync polling error: {e}")
        
        print("...")
        time.sleep(5) # Wait 5 seconds before polling again
        
    print("❌ Lip-Sync polling timed out.")
    return None

if __name__ == "__main__":
    # Test path (will fail if files don't exist)
    # generate_lip_sync("base_avatar.mp4", "narration.m4a", "output_lip_sync.mp4")
    pass
