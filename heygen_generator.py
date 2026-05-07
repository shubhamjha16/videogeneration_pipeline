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
    """Generate a placeholder video when no API key is available."""
    try:
        from moviepy.editor import ColorClip, TextClip, CompositeVideoClip

        duration = max(5.0, len(prompt) / 15.0)  # Rough estimate
        duration = min(duration, 30.0)

        bg = ColorClip(size=(1280, 720), color=(15, 15, 30), duration=duration)

        try:
            label = TextClip(
                "HeyGen Mock (No API Key)",
                fontsize=36, color="white", font="Helvetica",
            ).set_duration(duration).set_position("center")
            final = CompositeVideoClip([bg, label])
        except Exception:
            final = bg

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        final.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
        final.close()
        return output_path, duration
    except Exception as e:
        print(f"  Mock generation failed: {e}")
        return None, 0
