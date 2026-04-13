import os
import time
import requests


def generate_heygen_avatar(text: str, audio_path: str, output_path: str, avatar_id: str = None) -> str:
    """
    HeyGen API Integration (Production Ready).
    1. Uploads ElevenLabs generated audio to HeyGen as an Asset.
    2. Submits Video Generation task to HeyGen v2.
    3. Polls until completion and downloads mp4.
    """
    api_key = os.environ.get("HEYGEN_API_KEY")

    # Industrial Hardening: avatar_id from environment variable (set in ECS)
    avatar_id = avatar_id or os.environ.get("HEYGEN_AVATAR_ID") or os.environ.get("DEFAULT_HEYGEN_AVATAR") or "josh_video_20230607"




    if not api_key:
        print(f"❌ [HeyGen] HEYGEN_API_KEY not found! Returning high-fidelity mock: {output_path}")
        if not os.path.exists(output_path):
            from moviepy.editor import ColorClip, AudioFileClip, ImageClip, CompositeVideoClip
            aud = AudioFileClip(audio_path)
            # Create a more useful mock with a logo/static image
            bg = ColorClip(size=(1280, 720), color=(15, 15, 30), duration=aud.duration)
            
            # Try to add logo if it exists
            final_clip = bg
            logo_path = os.path.join(config.BASE_DIR, "factory_portal", "control_panel", "assets", "logo.png")
            if os.path.exists(logo_path):
                logo = ImageClip(logo_path).set_duration(aud.duration).resize(height=200).set_position(('center', 'center'))
                final_clip = CompositeVideoClip([bg, logo])
            
            final_clip = final_clip.set_audio(aud)
            try:
                final_clip.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
            finally:
                final_clip.close()
                aud.close()
        return output_path

    print(f"🚀 [HeyGen Gen] Initializing HeyGen avatar workflow for: {text[:30]}...")
    headers = {
        "x-api-key": api_key,
        "Accept": "application/json"
    }

    # 1. Upload Audio Asset
    print(f"   [HeyGen] Uploading audio asset...")
    upload_url = "https://api.heygen.com/v1/asset"
    try:
        with open(audio_path, 'rb') as f:
            files = {'file': (os.path.basename(audio_path), f, 'audio/mpeg')}
            # Content-Type must not be application/json for multipart
            res = requests.post(upload_url, headers={"x-api-key": api_key}, files=files, timeout=60)
        res.raise_for_status()
        audio_asset_id = res.json().get("data", {}).get("id")
        if not audio_asset_id:
            raise ValueError(f"Failed to get audio asset ID. Response: {res.text}")
    except Exception as e:
        print(f"❌ [HeyGen] Audio upload failed: {e}")
        return audio_path # Graceful degrade

    # 2. Add Video Task
    print(f"   [HeyGen] Triggering Video Generation (Avatar: {avatar_id})...")
    generate_url = "https://api.heygen.com/v2/video/generate"
    payload = {
        "video_inputs": [
            {
                "character": {
                    "type": "avatar", 
                    "avatar_id": avatar_id, 
                    "avatar_style": "normal"
                },
                "voice": {
                    "type": "audio",
                    "audio_asset_id": audio_asset_id
                }
            }
        ],
        "dimension": {"width": 1280, "height": 720}
    }
    header_json = {**headers, "Content-Type": "application/json"}
    
    try:
        res = requests.post(generate_url, json=payload, headers=header_json, timeout=30)
        res.raise_for_status()
        video_id = res.json().get("data", {}).get("video_id")
        if not video_id:
            raise ValueError(f"No video_id returned: {res.text}")
    except Exception as e:
        print(f"❌ [HeyGen] Generation request failed: {e}")
        return audio_path

    # 3. Poll for Status (v2 Protocol)
    print(f"   ⏳ [HeyGen] Task {video_id[:8]}... created. Polling for results...")
    poll_url = f"https://api.heygen.com/v2/video/get_status?video_id={video_id}"
    
    import urllib3
    session = requests.Session()
    retry = urllib3.util.retry.Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = requests.adapters.HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)

    for attempt in range(40): # Poll for up to 10 minutes
        try:
            res = session.get(poll_url, headers=header_json, timeout=10)
            data = res.json().get("data", {})
            status = data.get("status")
            
            if status in ["completed", "success"]:
                # v2 status response has video_url at top level of data
                video_url = data.get("video_url")
                if video_url:
                    print(f"   ✅ [HeyGen] Video ready! Downloading...")
                    with requests.get(video_url, stream=True, timeout=60) as r:
                         r.raise_for_status()
                         with open(output_path, 'wb') as f:
                             for chunk in r.iter_content(chunk_size=8192):
                                 f.write(chunk)
                    return output_path
            elif status in ["failed", "canceled"]:

                print(f"❌ [HeyGen] Generation failed: {data.get('error', 'unknown error')}")
                return None # Return None to trigger pipeline failure instead of corrupt output
        except Exception as e:
            print(f"   [Attempt {attempt}] [HeyGen] Polling warning: {e}")
            
        time.sleep(15)

    print("⚠️ [HeyGen] Polling timed out after 10 mins.")
    return None
