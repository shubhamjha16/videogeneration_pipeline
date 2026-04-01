import os
import json
import base64
import requests

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
VOICE_ID = "EXAVITQu4vr4xnSDxMaL" # Rachel or similar

def generate_audio(text: str, scene_idx: int, output_dir: str = ".") -> str:
    """
    Generates TTS audio using ElevenLabs API if key is present.
    As a fallback on Mac, it uses the native 'say' command to rapidly
    create an audio file for local testing of the pipeline without paying API costs.
    """
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    output_filename = os.path.join(output_dir, f"scene_{scene_idx}.m4a")
    
    if ELEVENLABS_API_KEY:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
        headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
        data = {"text": text, "model_id": "eleven_multilingual_v2"}
        response = requests.post(url, json=data, headers=headers)
        with open(output_filename, "wb") as f:
            f.write(response.content)
        print(f"Generated ElevenLabs audio for scene {scene_idx} -> {output_filename}")
    else:
        # Fallback to Mac native TTS
        # -o outputs an aiff or m4a file natively
        cmd = f'say -v "Samantha" -o {output_filename} "{text}"'
        os.system(cmd)
        print(f"Generated Free Mac audio for scene {scene_idx} -> {output_filename}")
        
    return output_filename
