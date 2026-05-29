import os
import requests
from dotenv import load_dotenv

load_dotenv()
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
VOICE_ID = "QTKSa2Iyv0yoxvXY2V8a"

def _generate_silent_audio(output_filename: str, duration: float = 1.0) -> str:
    """The Engine of Last Resort: Produces a silent WAV to prevent pipeline crashes."""
    import wave, struct
    output_filename = output_filename.replace(".m4a", ".wav").replace(".mp3", ".wav")

    print(f"⚠️  Ironclad Fallback: Generating {duration}s silent audio -> {output_filename}")
    with wave.open(output_filename, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(22050)
        # 16-bit silence
        count = int(22050 * duration)
        frames = struct.pack("<" + "h" * count, *([0] * count))
        wf.writeframes(frames)
    return output_filename

def generate_audio(text: str, scene_idx: int, output_dir: str = ".", use_elevenlabs: bool = None, job_id: str = None) -> tuple[str, int]:
    """
    Generates TTS audio.
    Hierarchy: 
      1. passed use_elevenlabs (if specified)
      2. FORCE_LOCAL_TTS env var
      3. ELEVENLABS_API_KEY presence
    """
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    output_filename = os.path.join(output_dir, f"scene_{scene_idx}.m4a")
    
    if os.path.exists(output_filename) and os.path.getsize(output_filename) > 0:
        print(f"   ℹ️  TTS narration file already exists: {output_filename}. Bypassing ElevenLabs call.")
        return output_filename, 0
    
    # 1. Determine preference
    force_local = os.environ.get("FORCE_LOCAL_TTS", "false").lower() == "true"
    
    # Use explicitly passed boolean, otherwise fallback to global env
    engage_elevenlabs = use_elevenlabs if use_elevenlabs is not None else (not force_local)
    
    if engage_elevenlabs and ELEVENLABS_API_KEY:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/with-timestamps"
        headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
        data = {"text": text, "model_id": "eleven_multilingual_v2"}
        response = requests.post(url, json=data, headers=headers, timeout=30)
        if response.status_code == 200:
            import base64, json
            res_data = response.json()
            audio_bytes = base64.b64decode(res_data["audio_base64"])
            with open(output_filename, "wb") as f:
                f.write(audio_bytes)
            
            # Save alignment data for kinetic subtitles
            alignment_path = output_filename.replace(".m4a", ".json").replace(".mp3", ".json")
            with open(alignment_path, "w") as f:
                json.dump(res_data.get("alignment", {}), f)
                
            print(f"Generated ElevenLabs audio + timestamps for scene {scene_idx} -> {output_filename}")
            try:
                from cost_tracker import LedgerManager
                LedgerManager.record_tts_call(job_id, "elevenlabs", len(text))
            except Exception as e:
                print(f"⚠️ Failed to log TTS cost: {e}")
            return output_filename, len(text)
        else:
            print(f"⚠️ ElevenLabs Error {response.status_code}: {response.text}")
            import time; time.sleep(0.5) 
    
    # Fallback Path 1: macOS 'say'
    if os.name == "posix" and os.path.exists("/usr/bin/say"):
        import subprocess, imageio_ffmpeg
        aiff_path = output_filename.replace(".m4a", ".aiff")
        mp3_path  = output_filename.replace(".m4a", ".mp3")
        subprocess.run(["say", "-v", "Samantha", "-o", aiff_path, text], check=True, timeout=120, env=os.environ)
        try:
            subprocess.run(
                [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", aiff_path,
                 "-ar", "44100", "-ab", "128k", mp3_path],
                capture_output=True,
                check=True,
                timeout=60,
                env=os.environ
            )
            output_filename = mp3_path
            print(f"Generated Mac TTS fallback audio for scene {scene_idx} -> {output_filename}")
            # Non-billable fallback
            try:
                from cost_tracker import LedgerManager
                LedgerManager.record_tts_call(job_id, "macos_say", len(text), cost_per_char=0.0)
            except Exception as e: print(f"⚠️ [tts_generator] failed to record macOS TTS cost: {e}")
            return output_filename, 0
        except Exception as e:
            print(f"❌ Mac FFmpeg conversion failed: {e}")
        finally:
            if os.path.exists(aiff_path):
                os.remove(aiff_path)
    
    # Fallback Path 1.5: Linux native offline 'espeak' or 'espeak-ng'
    import shutil
    espeak_exe = shutil.which("espeak") or shutil.which("espeak-ng")
    if espeak_exe and os.name == "posix":
        import subprocess, imageio_ffmpeg
        wav_path = output_filename.replace(".m4a", ".wav").replace(".mp3", ".wav")
        mp3_path = output_filename.replace(".m4a", ".mp3")
        try:
            print(f"   [TTS Fallback] Found espeak at {espeak_exe}. Generating offline speech...")
            subprocess.run([espeak_exe, "-w", wav_path, text], check=True, timeout=120, env=os.environ)
            subprocess.run(
                [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", wav_path,
                 "-ar", "44100", "-ab", "128k", mp3_path],
                capture_output=True,
                check=True,
                timeout=60,
                env=os.environ
            )
            output_filename = mp3_path
            print(f"Generated Linux espeak fallback audio for scene {scene_idx} -> {output_filename}")
            try:
                from cost_tracker import LedgerManager
                LedgerManager.record_tts_call(job_id, "linux_espeak", len(text), cost_per_char=0.0)
            except Exception as e: print(f"⚠️ [tts_generator] failed to record espeak TTS cost: {e}")
            return output_filename, 0
        except Exception as e:
            print(f"❌ Linux espeak fallback/FFmpeg conversion failed: {e}")
        finally:
            if os.path.exists(wav_path):
                try: os.remove(wav_path)
                except Exception as e: print(f"⚠️ [tts_generator] failed to remove temp WAV {wav_path}: {e}")

    # Fallback Path 2: Linux gTTS (Hardened for Hindi/Indic)
    try:
        from gtts import gTTS
        # Detection: If text contains Devanagari characters, use 'hi'
        # Range for Devanagari: \u0900-\u097F
        import re
        lang = "hi" if re.search("[\u0900-\u097F]", text) else "en"
        
        print(f"   [TTS Fallback] Detected language: {lang}")
        tts = gTTS(text=text, lang=lang, slow=False)
        mp3_path = output_filename.replace(".m4a", ".mp3")
        tts.save(mp3_path)
        output_filename = mp3_path
        print(f"Generated gTTS ({lang}) audio for scene {scene_idx} -> {output_filename}")
        # Non-billable fallback
        try:
            from cost_tracker import LedgerManager
            LedgerManager.record_tts_call(job_id, "gtts", len(text), cost_per_char=0.0)
        except Exception as e: print(f"⚠️ [tts_generator] failed to record gTTS cost: {e}")
        return output_filename, 0
    except Exception as e:
        print(f"❌ gTTS failed: {e} — falling back to Silent Sentinel")

        # Heuristic: ~12 words per second for a comfortable reading pace
        word_count = len(text.split())
        heuristic_duration = max(1.0, word_count / 12.0)
        output_filename = _generate_silent_audio(output_filename, duration=heuristic_duration)
        # Silent fallback — no API was called, zero billable chars
        return output_filename, 0

    # Note: Returning actual characters used for billing
    return output_filename, len(text)

if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()
    
    if len(sys.argv) > 2:
        text_arg = sys.argv[1]
        filename_arg = sys.argv[2]
        # Hack to support direct filename output for masterclass runs
        VOICE_ID = "QTKSa2Iyv0yoxvXY2V8a"
        ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
        
        if ELEVENLABS_API_KEY:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
            headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
            data = {"text": text_arg, "model_id": "eleven_multilingual_v2"}
            response = requests.post(url, json=data, headers=headers, timeout=30)
            if response.status_code == 200:
                with open(filename_arg, "wb") as f:
                    f.write(response.content)
                print(f"✅ Success! CLI TTS Saved to: {filename_arg}")
            else:
                print(f"❌ ElevenLabs Error {response.status_code}: {response.text}")
                # Fallback to local
                import subprocess
                aiff_path = filename_arg.replace(".mp3", ".aiff").replace(".m4a", ".aiff")
                subprocess.run(["say", "-v", "Samantha", "-o", aiff_path, text_arg], check=True)
                try:
                    import imageio_ffmpeg
                    subprocess.run(
                        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", aiff_path,
                         "-ar", "44100", "-ab", "128k", filename_arg],
                        capture_output=True,
                        check=True
                    )
                finally:
                    if os.path.exists(aiff_path):
                        os.remove(aiff_path)
                print(f"⚠️ Fallback native TTS Saved to: {filename_arg}")
        else:
            import subprocess
            aiff_path = filename_arg.replace(".mp3", ".aiff").replace(".m4a", ".aiff")
            subprocess.run(["say", "-v", "Samantha", "-o", aiff_path, text_arg], check=True, timeout=120, env=os.environ)

            try:
                import imageio_ffmpeg
                subprocess.run(
                    [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", aiff_path,
                     "-ar", "44100", "-ab", "128k", filename_arg],
                    capture_output=True,
                    check=True
                )
            finally:
                if os.path.exists(aiff_path):
                    os.remove(aiff_path)
            print(f"✅ Success! CLI native TTS Saved to: {filename_arg}")
