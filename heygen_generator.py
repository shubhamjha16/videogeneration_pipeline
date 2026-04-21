import os
import time
import subprocess
import requests
import config



def generate_heygen_avatar(text: str, audio_path: str, output_path: str, avatar_id: str = None) -> str:
    """
    HeyGen API Integration (Production Ready).
    1. Uploads ElevenLabs generated audio to HeyGen as an Asset.
    2. Submits Video Generation task to HeyGen v2.
    3. Polls until completion and downloads mp4.
    """
    api_key = os.environ.get("HEYGEN_API_KEY")

    # Industrial Hardening: avatar_id from environment variable (set in ECS)
    avatar_id = avatar_id or os.environ.get("HEYGEN_AVATAR_ID") or os.environ.get("DEFAULT_HEYGEN_AVATAR") or "Abigail_expressive_2024112501"




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
                duration = aud.duration
                aud.close()
        # Return path and duration for financial ledger
        from moviepy.editor import VideoFileClip
        try:
            with VideoFileClip(output_path) as clip:
                duration = clip.duration
        except:
            duration = 1.0 # fallback
        return output_path, duration

    print(f"🚀 [HeyGen Gen] Initializing HeyGen avatar workflow for: {text[:30]}...")
    headers = {
        "x-api-key": api_key,
        "Accept": "application/json"
    }

    # 1. Upload Audio Asset
    print(f"   [HeyGen] Uploading audio asset...")
    upload_url = "https://upload.heygen.com/v1/asset"

    # HeyGen only supports audio/mpeg (MP3). Convert m4a/wav to mp3 first.
    actual_audio_path = audio_path
    ext = os.path.splitext(audio_path)[1].lower()
    if ext in (".m4a", ".aac", ".wav", ".aiff"):
        mp3_path = audio_path.rsplit(".", 1)[0] + "_heygen.mp3"
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            subprocess.run(
                [ffmpeg_exe, "-y", "-i", audio_path, "-ar", "44100", "-ab", "128k", mp3_path],
                capture_output=True, check=True, timeout=60
            )
            actual_audio_path = mp3_path
            print(f"   [HeyGen] Converted {ext} → MP3 for upload: {os.path.basename(mp3_path)}")
        except Exception as conv_err:
            print(f"   ⚠️ [HeyGen] Audio conversion to MP3 failed ({conv_err}), uploading original {ext}")

    # Detect MIME type based on file extension
    upload_ext = os.path.splitext(actual_audio_path)[1].lower()
    mime_map = {".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".wav": "audio/wav", ".aac": "audio/aac"}
    content_type = mime_map.get(upload_ext, "audio/mpeg")

    try:
        with open(actual_audio_path, 'rb') as f:
            audio_binary = f.read()
            # Raw binary upload: data-binary instead of multipart
            res = requests.post(
                upload_url, 
                headers={
                    "x-api-key": api_key,
                    "Content-Type": content_type
                }, 
                data=audio_binary, 
                timeout=60
            )
        print(f"   [HeyGen] Upload response: {res.status_code} {res.reason}")
        res.raise_for_status()
        audio_asset_id = res.json().get("data", {}).get("id")
        if not audio_asset_id:
            raise ValueError(f"Failed to get audio asset ID. Response: {res.text}")
    except Exception as e:
        print(f"❌ [HeyGen] Audio upload failed: {e}")
        return None # Critical failure, return None to trigger fallback

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
        "dimension": {"width": 1280, "height": 720},
        "caption": True
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
        return None

    # 3. Poll for Status (v2 Protocol)
    print(f"   ⏳ [HeyGen] Task {video_id[:8]}... created. Polling for results...")
    poll_url = f"https://api.heygen.com/v1/video_status.get?video_id={video_id}"
    
    import urllib3
    session = requests.Session()
    retry = urllib3.util.retry.Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = requests.adapters.HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)

    for attempt in range(40): # Poll for up to 10 minutes
        try:
            res = session.get(poll_url, headers=header_json, timeout=10)
            if not res.text:
                print(f"   [Attempt {attempt}] [HeyGen] Warning: Empty API response (Status: {res.status_code}). Retrying...")
                time.sleep(15)
                continue

            try:
                data = res.json().get("data", {})
            except Exception as j:
                print(f"   [Attempt {attempt}] [HeyGen] JSON Error (Status: {res.status_code}): {j}. Body: {res.text[:100]}")
                time.sleep(15)
                continue

            status = data.get("status")
            print(f"   [Attempt {attempt}] [HeyGen] Task Status: {status}")
            
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
                    
                    # Return path and actual duration from API
                    actual_duration = data.get("duration", 0)
                    return output_path, actual_duration
            elif status in ["failed", "canceled"]:

                print(f"❌ [HeyGen] Generation failed: {data.get('error', 'unknown error')}")
                return None # Return None to trigger pipeline failure instead of corrupt output
        except Exception as e:
            print(f"   [Attempt {attempt}] [HeyGen] Polling warning (Status: {getattr(res, 'status_code', 'N/A')}): {e}")
            
        time.sleep(15)

    print("⚠️ [HeyGen] Polling timed out after 10 mins.")
    return None
