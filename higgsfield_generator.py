import os
import time
import requests
import json
from PIL import Image
from dotenv import load_dotenv

# Compatibility for Pillow 10.0+ 
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

# Load credentials from .env
load_dotenv()

def generate_higgsfield_video(prompt: str, output_path: str) -> str:
    """
    Industrialized Higgsfield/Muapi Integration.
    Tries multiple endpoints to ensure delivery even if one provider is down.
    """
    api_id = os.environ.get("HIGGSFIELD_API_ID")
    api_key = os.environ.get("HIGGSFIELD_API_KEY")

    if not api_id or not api_key:
        print("   ⚠️ Missing Higgsfield credentials - falling back to placeholder.")
        return _generate_placeholder(prompt, output_path)

    # Strategy: Try 3 different paths
    # 1. Official Higgsfield Cloud (Latest V2 style)
    # 2. Muapi Aggregator (Bridge style)
    # 3. Local Metaphor (Safety)

    print(f"🚀 [Higgsfield] Attempting Video Gen for: {prompt[:40]}...")

    # --- PATH A: Higgsfield Cloud Direct ---
    try:
        # Header for direct cloud.higgsfield.ai authentication
        headers = {
            "Authorization": f"Key {api_id}:{api_key}",
            "Content-Type": "application/json"
        }
        submit_url = "https://api.higgsfield.ai/v1/generations"
        payload = {
            "model": "higgsfield-v1-text-to-video",
            "prompt": prompt,
            "duration": 5,
            "aspect_ratio": "16:9"
        }
        
        response = requests.post(submit_url, json=payload, headers=headers, timeout=30)
        if response.status_code in [200, 201]:
            task_id = response.json().get("id") or response.json().get("generation_id")
            if task_id:
                return _poll_and_download(task_id, output_path, headers, "https://api.higgsfield.ai/v1/generations")
    except Exception as e:
        print(f"   ℹ️ Path A (Direct) failed: {e}")

    # --- PATH B: Muapi Bridge (Fallback) ---
    try:
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }
        # Many Muapi models use the ID as the endpoint name
        submit_url = f"https://api.muapi.ai/api/v1/{api_id}"
        payload = {
            "prompt": prompt,
            "negative_prompt": "blurry, low quality",
            "aspect_ratio": "16:9"
        }
        
        response = requests.post(submit_url, json=payload, headers=headers, timeout=30)
        if response.status_code in [200, 201, 202]:
            task_id = response.json().get("request_id") or response.json().get("id")
            if task_id:
                return _poll_and_download(task_id, output_path, headers, "https://api.muapi.ai/api/v1/predictions")
    except Exception as e:
        print(f"   ℹ️ Path B (Bridge) failed: {e}")

    # --- FINAL FALLBACK: Local Metaphor ---
    print("   ⚠️ All AI video endpoints exhausted. Generating local cinematic placeholder...")
    return _generate_placeholder(prompt, output_path)

def _poll_and_download(task_id: str, output_path: str, headers: dict, poll_base: str) -> str:
    """Polls for completion and downloads the video file streamingly."""
    print(f"   ⏳ Task {task_id[:8]}... created. Polling for results...")
    
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            # Flexible polling URL logic
            if "predictions" in poll_base:
                poll_url = f"{poll_base}/{task_id}/result"
            else:
                poll_url = f"{poll_base}/{task_id}"
                
            res = requests.get(poll_url, headers=headers, timeout=10)
            try:
                data = res.json()
            except (json.JSONDecodeError, ValueError):
                print(f"   ⚠️ Received non-JSON response from API (Attempt {attempt}). Retrying...")
                continue
                
            status = data.get("status", "").lower()
            if status in ["succeeded", "completed", "success"]:
                video_url = data.get("output", {}).get("video") or data.get("output_url") or data.get("output")
                if video_url:
                    print(f"   ✅ Video ready! Downloading...")
                    return _download_file(video_url, output_path)
            
            if status in ["failed", "canceled"]:
                print(f"   ❌ Generation failed: {data.get('error', 'unknown error')}")
                break
                
        except Exception as e:
            print(f"   [Attempt {attempt}] Polling error: {e}")
            
        time.sleep(10)
    
    return _generate_placeholder("Polling timed out", output_path)

def _download_file(url: str, dest_path: str) -> str:
    tmp_path = dest_path + ".tmp"
    try:
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(tmp_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        # Rename only after successful download to avoid corrupted cache
        os.replace(tmp_path, dest_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    return dest_path

def _generate_placeholder(prompt: str, output_path: str) -> str:
    """Creates a high-quality local placeholder if the API fails entirely."""
    if os.path.exists(output_path): return output_path
    
    import subprocess
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", "cellauto=s=1280x720:ratio=0.5",
        "-t", "5", "-vf", f"hue=s=0,format=yuv420p", "-c:v", "libx264", output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return output_path

if __name__ == "__main__":
    # Rapid verification
    print(generate_higgsfield_video("A futuristic city at sunrise", "test_debug.mp4"))
