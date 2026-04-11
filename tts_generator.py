import os
import json
import base64
import requests

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
VOICE_ID = "QTKSa2Iyv0yoxvXY2V8a" # Neha (Customer Care)

def generate_audio(text: str, scene_idx: int, output_dir: str = ".") -> str:
    """
    Generates TTS audio using ElevenLabs API if key is present.
    As a fallback on Mac, it uses the native 'say' command to rapidly
    create an audio file for local testing of the pipeline without paying API costs.
    """
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    output_filename = os.path.join(output_dir, f"scene_{scene_idx}.m4a")
    
    FORCE_LOCAL_TTS = os.environ.get("FORCE_LOCAL_TTS", "false").lower() == "true"
    
    if ELEVENLABS_API_KEY and not FORCE_LOCAL_TTS:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
        headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
        data = {"text": text, "model_id": "eleven_multilingual_v2"}
        response = requests.post(url, json=data, headers=headers, timeout=30)
        if response.status_code == 200:
            with open(output_filename, "wb") as f:
                f.write(response.content)
            print(f"Generated ElevenLabs audio for scene {scene_idx} -> {output_filename}")
        else:
            print(f"⚠️ ElevenLabs Error {response.status_code}: {response.text}")
            import time; time.sleep(0.5) 
            # Fallback to macOS if key is broken/out-of-credits
            if os.name == "posix" and os.path.exists("/usr/bin/say"):
                import subprocess, imageio_ffmpeg
                aiff_path = output_filename.replace(".m4a", ".aiff")
                mp3_path  = output_filename.replace(".m4a", ".mp3")
                subprocess.run(["say", "-v", "Samantha", "-o", aiff_path, text])
                subprocess.run(
                    [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", aiff_path,
                     "-ar", "44100", "-ab", "128k", mp3_path],
                    capture_output=True,
                )
                output_filename = mp3_path
                print(f"Generated Mac TTS fallback audio for scene {scene_idx} -> {output_filename}")
            else:
                # Absolute silent fallback
                import wave, struct
                output_filename = output_filename.replace(".m4a", ".wav")
                with wave.open(output_filename, "w") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(22050)
                    wf.writeframes(struct.pack("<" + "h" * 22050, *([0] * 22050)))
                print(f"⚠️ Generated silent audio fallback for scene {scene_idx}")
    elif os.name == "posix" and os.path.exists("/usr/bin/say"):
        # macOS native TTS — output aiff, convert to mp3 via ffmpeg for MoviePy compat
        import subprocess, imageio_ffmpeg
        aiff_path = output_filename.replace(".m4a", ".aiff")
        mp3_path  = output_filename.replace(".m4a", ".mp3")
        subprocess.run(["say", "-v", "Samantha", "-o", aiff_path, text])
        subprocess.run(
            [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", aiff_path,
             "-ar", "44100", "-ab", "128k", mp3_path],
            capture_output=True,
        )
        output_filename = mp3_path
        print(f"Generated Mac TTS audio for scene {scene_idx} -> {output_filename}")
    else:
        # Linux fallback — gTTS (works on ECS if ElevenLabs key missing)
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang="en", slow=False)
            mp3_path = output_filename.replace(".m4a", ".mp3")
            tts.save(mp3_path)
            output_filename = mp3_path
            print(f"Generated gTTS audio for scene {scene_idx} -> {output_filename}")
        except Exception as e:
            print(f"⚠️  gTTS failed: {e} — generating silent audio")
            # Write 1-second silent WAV as absolute last resort
            import wave, struct
            output_filename = output_filename.replace(".m4a", ".wav")
            with wave.open(output_filename, "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(22050)
                wf.writeframes(struct.pack("<" + "h" * 22050, *([0] * 22050)))
        
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
                subprocess.run(["say", "-v", "Samantha", "-o", filename_arg, text_arg])
                print(f"⚠️ Fallback native TTS Saved to: {filename_arg}")
        else:
            import subprocess
            subprocess.run(["say", "-v", "Samantha", "-o", filename_arg, text_arg])
            print(f"✅ Success! CLI native TTS Saved to: {filename_arg}")
