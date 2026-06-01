import os
import time
import requests
import config


# Startup validation
HEYGEN_AVATAR_ID = os.environ.get("HEYGEN_AVATAR_ID") or config.HEYGEN_AVATAR_ID
if not os.environ.get("HEYGEN_AVATAR_ID"):
    print(f"[HeyGen] HEYGEN_AVATAR_ID not set in env. Using config default: {HEYGEN_AVATAR_ID}")
else:
    print(f"[HeyGen] Active Avatar ID: {HEYGEN_AVATAR_ID}")


def generate_heygen_avatar(
    prompt: str,
    output_path: str,
    avatar_id: str = None,
    voice_id: str = None,
    job_id: str = None,
) -> tuple[str | None, float]:
    """
    HeyGen v3 Video Agents API.

    Sends the narration text directly to HeyGen. HeyGen handles
    TTS, lip-sync, and avatar rendering internally. No audio upload needed.

    Args:
        prompt:      Full narration script for the video.
        output_path: Local path to save the downloaded .mp4.
        avatar_id:   Optional HeyGen avatar ID (falls back to env/config).
        voice_id:    Optional HeyGen voice ID.
        job_id:      Pipeline job ID for cost ledgering.

    Returns:
        (output_path, duration_seconds) on success, (None, 0) on failure.
    """
    api_key = os.environ.get("HEYGEN_API_KEY")
    avatar_id = avatar_id or HEYGEN_AVATAR_ID

    if not api_key:
        print(f"[HeyGen] HEYGEN_API_KEY not found. Generating local mock: {output_path}")
        return _generate_mock_video(prompt, output_path)

    print(f"[HeyGen v3] Submitting prompt ({len(prompt)} chars) to Video Agents API...")

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # --- Step 1: Submit generation request ---
    payload = {
        "prompt": prompt,
        "avatar_id": avatar_id,
    }
    if voice_id:
        payload["voice_id"] = voice_id

    try:
        res = requests.post(
            "https://api.heygen.com/v3/video-agents",
            json=payload,
            headers=headers,
            timeout=30,
        )
        res.raise_for_status()
        video_id = res.json().get("data", {}).get("video_id")
        if not video_id:
            raise ValueError(f"No video_id in response: {res.text[:200]}")
    except Exception as e:
        print(f"[HeyGen v3] Submission failed: {e}")
        return None, 0

    # --- Step 2: Poll for completion ---
    print(f"[HeyGen v3] Task {video_id[:12]}... created. Polling...")
    poll_url = f"https://api.heygen.com/v1/video_status.get?video_id={video_id}"

    import urllib3
    session = requests.Session()
    retry = urllib3.util.retry.Retry(
        total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]
    )
    session.mount("https://", requests.adapters.HTTPAdapter(max_retries=retry))

    for attempt in range(40):  # Up to ~10 minutes
        try:
            res = session.get(poll_url, headers=headers, timeout=15)
            if not res.text:
                print(f"  [Attempt {attempt}] Empty response (HTTP {res.status_code}). Retrying...")
                time.sleep(15)
                continue

            data = res.json().get("data", {})
            status = data.get("status")
            print(f"  [Attempt {attempt}] Status: {status}")

            if status in ("completed", "success"):
                video_url = data.get("video_url")
                if not video_url:
                    print(f"  [HeyGen v3] Completed but no video_url in response.")
                    return None, 0

                # Download the MP4
                print(f"  [HeyGen v3] Downloading video...")
                with requests.get(video_url, stream=True, timeout=120) as dl:
                    dl.raise_for_status()
                    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                    with open(output_path, "wb") as f:
                        for chunk in dl.iter_content(chunk_size=8192):
                            f.write(chunk)

                duration_sec = data.get("duration", 0)

                # Ledger: $0.0333/sec
                try:
                    from cost_tracker import LedgerManager
                    LedgerManager.record_heygen_call(job_id, duration_sec)
                except Exception as le:
                    print(f"  Failed to log HeyGen cost: {le}")

                print(f"  [HeyGen v3] Done. Duration: {duration_sec}s -> {output_path}")
                return output_path, duration_sec

            elif status in ("failed", "canceled"):
                error = data.get("error", "unknown")
                print(f"  [HeyGen v3] Generation failed: {error}")
                return None, 0

        except Exception as e:
            print(f"  [Attempt {attempt}] Polling error: {e}")

        time.sleep(15)

    print("[HeyGen v3] Polling timed out after ~10 minutes.")
    return None, 0


def _generate_mock_video(prompt: str, output_path: str) -> tuple[str, float]:
    """Generate a placeholder video when no API key is available using a premium Pillow whiteboard style."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        from moviepy.editor import ImageClip
        
        duration = max(5.0, len(prompt) / 15.0)  # Rough estimate
        duration = min(duration, 30.0)
        
        w, h = 1280, 720
        # Create premium off-white/teal background
        img = Image.new("RGB", (w, h), "#F4F7F7")
        draw = ImageDraw.Draw(img)
        
        # Grid lines
        grid_spacing = 40
        for x in range(0, w, grid_spacing):
            draw.line([(x, 0), (x, h)], fill="#EBF2F2", width=1)
        for y in range(0, h, grid_spacing):
            draw.line([(0, y), (w, y)], fill="#EBF2F2", width=1)
            
        # Draw frame
        draw.rounded_rectangle([20, 20, w - 20, h - 20], radius=15, outline="#088A8F", width=4)
        
        def get_font(size, bold=False):
            paths = []
            if bold:
                paths = [
                    "/Library/Fonts/Arial Unicode.ttf",
                    "/System/Library/Fonts/Helvetica.ttc",
                    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                    "/Library/Fonts/Arial Bold.ttf",
                    "/System/Library/Fonts/HelveticaNeue.dfont",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
                ]
            else:
                paths = [
                    "/Library/Fonts/Arial Unicode.ttf",
                    "/System/Library/Fonts/Helvetica.ttc",
                    "/System/Library/Fonts/Supplemental/Arial.ttf",
                    "/Library/Fonts/Arial.ttf",
                    "/System/Library/Fonts/Helvetica.dfont",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
                ]
            for p in paths:
                if os.path.exists(p):
                    try: return ImageFont.truetype(p, size)
                    except Exception: continue
            return ImageFont.load_default()
            
        font_title = get_font(32, bold=True)
        font_body = get_font(20, bold=False)
        font_dur = get_font(18, bold=True)
        
        # Content Card
        draw.rounded_rectangle([300, 100, 980, 620], radius=12, fill="#FFFFFF", outline="#E2E8F0", width=2)
        
        # Avatar Silhouette placeholder in top-center of the card
        draw.ellipse([600, 130, 680, 210], fill="#E5F4F4", outline="#088A8F", width=2)
        draw.ellipse([625, 145, 655, 175], fill="#088A8F") # Head
        draw.chord([610, 175, 670, 215], 180, 360, fill="#088A8F") # Shoulders
        
        draw.text((340, 230), "Personalized Avatar Narrator", fill="#088A8F", font=font_title)
        
        # Wrapped narration prompt
        def wrap_text(text, font, max_width):
            words = text.split()
            lines = []
            current_line = []
            for word in words:
                test_line = " ".join(current_line + [word])
                try:
                    tw = draw.textlength(test_line, font=font)
                except Exception:
                    tw = len(test_line) * (font.size * 0.6)
                if tw <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(" ".join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(" ".join(current_line))
            return lines
            
        wrapped = wrap_text(prompt, font_body, 600)
        curr_y = 290
        for line in wrapped[:7]: # limit to 7 lines inside mockup
            draw.text((340, curr_y), line, fill="#2E2E2E", font=font_body)
            curr_y += 28
            
        # Draw duration status at the bottom of the card
        draw.text((340, 560), f"Status: Mock Agent Active | Estimated Duration: {duration:.1f}s", fill="#088A8F", font=font_dur)
        
        temp_img_path = output_path.replace(".mp4", "_mock.png")
        os.makedirs(os.path.dirname(os.path.abspath(temp_img_path)), exist_ok=True)
        img.save(temp_img_path)
        
        # Overlay logo watermarking if logo file exists
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.png")
        if os.path.exists(logo_path):
            try:
                slide_img = Image.open(temp_img_path).convert("RGBA")
                logo_img = Image.open(logo_path).convert("RGBA")
                
                target_width = 140
                w_percent = (target_width / float(logo_img.size[0]))
                target_height = int((float(logo_img.size[1]) * float(w_percent)))
                logo_resized = logo_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                
                pos_x = w - target_width - 30
                pos_y = h - target_height - 30
                
                slide_img.paste(logo_resized, (pos_x, pos_y), logo_resized)
                slide_img.convert("RGB").save(temp_img_path)
            except Exception as le:
                print(f"  [HeyGen Mock] Failed to watermark mock: {le}")
                
        # Generate final mock video from static image
        clip = ImageClip(temp_img_path).set_duration(duration)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        clip.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
        clip.close()
        
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)
            
        return output_path, duration
        
    except Exception as e:
        print(f"  Mock generation failed: {e}")
        return None, 0

