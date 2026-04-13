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

def generate_audio(text: str, scene_idx: int, output_dir: str = ".") -> str:
    """
    Generates TTS audio using ElevenLabs API if key is present.
    Fallback hierarchy: ElevenLabs -> macOS native 'say' -> gTTS (Linux) -> Silent WAV.
    """
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    output_filename = os.path.join(output_dir, f"scene_{scene_idx}.m4a")
    
    FORCE_LOCAL_TTS = os.environ.get("FORCE_LOCAL_TTS", "false").lower() == "true"
    
    if ELEVENLABS_API_KEY and not FORCE_LOCAL_TTS:
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
            return output_filename
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
            return output_filename
        except Exception as e:
            print(f"❌ Mac FFmpeg conversion failed: {e}")
        finally:
            if os.path.exists(aiff_path):
                os.remove(aiff_path)
    
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
        return output_filename
    except Exception as e:
        print(f"❌ gTTS failed: {e} — falling back to Silent Sentinel")

        # Heuristic: ~12 words per second for a comfortable reading pace
        word_count = len(text.split())
        heuristic_duration = max(1.0, word_count / 3.0) 
        output_filename = _generate_silent_audio(output_filename, duration=heuristic_duration)
        return output_filename

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
