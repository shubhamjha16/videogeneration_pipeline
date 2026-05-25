import os
import json
import requests
import subprocess
import imageio_ffmpeg
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
HINDI_VOICE_ID = os.environ.get("HINDI_VOICE_ID", "QTKSa2Iyv0yoxvXY2V8a")  # default high-quality multilingual voice

SUPPORTED_LANGUAGES = {
    "hindi": "hi",
    "hinglish": "hi",  # Uses Hindi voice but Hinglish script
    "tamil": "ta",
    "telugu": "te",
    "bengali": "bn",
    "marathi": "mr",
    "kannada": "kn",
    "malayalam": "ml"
}


def translate_text(text: str, target_language: str) -> str:
    """Translate English text to target language using Groq (Llama 3)."""
    try:
        from groq import Groq
    except ImportError:
        raise ImportError("groq library not installed. Please use the project's virtual environment.")

    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not found in environment.")
    
    client = Groq(api_key=GROQ_API_KEY)
    
    if target_language.lower() == "hinglish":
        prompt = f"""Convert the following English educational text to Hinglish — a natural mix of Hindi and English commonly used by Indian students.
Rules:
- Keep all medical/scientific/technical terms in English (e.g. hypertension, mmHg, bronchoscopy)
- Use Hindi for connecting words, explanations, and transitions (e.g. "iska matlab hai", "yeh important hai", "dhyan rakhein")
- Sound like a friendly Indian teacher explaining to a student
- Return ONLY the Hinglish text, nothing else

Text: {text}"""
    else:
        prompt = f"""Translate the following English educational text to {target_language}.
Keep medical/scientific terms accurate. Keep the same tone — clear, educational, exam-focused.
Return ONLY the translated text, nothing else.

Text: {text}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a professional medical translator fluent in English and Indic languages."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0
    )
    
    return response.choices[0].message.content.strip()


def generate_dubbed_audio(text: str, output_path: str, target_language: str) -> str:
    """Generate audio for translated text via ElevenLabs with regional voice support."""
    lang_lower = target_language.lower()
    lang_code = SUPPORTED_LANGUAGES.get(lang_lower, "hi")
    
    # Allow language-specific voice overrides from env vars, falling back to HINDI_VOICE_ID
    env_var_name = f"{lang_lower.upper()}_VOICE_ID"
    voice_id = os.environ.get(env_var_name, HINDI_VOICE_ID)
    
    if ELEVENLABS_API_KEY:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
        data = {"text": text, "model_id": "eleven_multilingual_v2"}
        response = requests.post(url, json=data, headers=headers, timeout=30)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"✅ ElevenLabs dubbed audio ({target_language}): {output_path}")
            return output_path
        else:
            print(f"⚠️ ElevenLabs failed ({response.status_code}): {response.text}, falling back to gTTS")
    
    # Fallback: gTTS with correct target ISO code
    from gtts import gTTS
    tts = gTTS(text=text, lang=lang_code, slow=False)
    tts.save(output_path)
    print(f"✅ gTTS dubbed audio ({target_language}): {output_path}")
    return output_path


def swap_audio(video_path: str, audio_files: list, output_path: str) -> str:
    """Merge multiple audio files and swap into video using ffmpeg."""
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    
    # Step 1: Concatenate all audio files
    concat_list = output_path.replace(".mp4", "_concat.txt")
    with open(concat_list, "w") as f:
        for audio in audio_files:
            f.write(f"file '{os.path.abspath(audio)}'\n")
    
    merged_audio = output_path.replace(".mp4", "_merged.mp3")
    subprocess.run([
        ffmpeg, "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list, merged_audio
    ], check=True, capture_output=True)
    
    # Step 2: Swap audio into video
    subprocess.run([
        ffmpeg, "-y",
        "-i", video_path,
        "-i", merged_audio,
        "-c:v", "copy",
        "-c:a", "aac",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        output_path
    ], check=True, capture_output=True)
    
    # Cleanup
    os.remove(concat_list)
    os.remove(merged_audio)
    
    print(f"✅ Audio swapped: {output_path}")
    return output_path


def run_dub_pipeline(job_id: str, target_language: str = "hindi") -> dict:
    """
    Main entry point for Pipeline 6: Dub an existing job into target language.
    
    Args:
        job_id: Existing completed job ID
        target_language: Language to dub into (hindi, tamil, telugu, etc.)
    
    Returns:
        dict with dubbed_video_url and metadata
    """
    target_language_clean = target_language.lower().strip()
    if target_language_clean not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {target_language}. Supported: {list(SUPPORTED_LANGUAGES.keys())}")
    
    # Find job directory
    output_root = "output"
    job_dir = None
    for d in os.listdir(output_root):
        if job_id in d:
            job_dir = os.path.join(output_root, d)
            break
    
    if not job_dir:
        raise FileNotFoundError(f"Job directory not found for job_id: {job_id}")
    
    scenes_path = os.path.join(job_dir, "scenes.json")
    if not os.path.exists(scenes_path):
        raise FileNotFoundError(f"scenes.json not found — job may predate Pipeline 6")
    
    # Find original video
    video_files = [f for f in os.listdir(job_dir) if f.endswith(".mp4") and "dubbed" not in f]
    if not video_files:
        raise FileNotFoundError(f"No original video found in {job_dir}")
    original_video = os.path.join(job_dir, video_files[0])
    
    # Load scenes
    with open(scenes_path) as f:
        scenes = json.load(f)
    
    print(f"🎬 Starting Pipeline 6: Dubbing {job_id} → {target_language_clean} ({len(scenes)} scenes)")
    
    # Translate + generate audio per scene
    dub_dir = os.path.join(job_dir, f"dub_{target_language_clean}")
    os.makedirs(dub_dir, exist_ok=True)
    
    audio_files = []
    for i, scene in enumerate(scenes):
        english_text = scene["narration_text"]
        
        # Translate
        print(f"   🌐 Translating scene {i}...")
        translated = translate_text(english_text, target_language_clean)
        print(f"   ✅ Scene {i}: {translated[:60]}...")
        
        # Generate audio
        audio_path = os.path.join(dub_dir, f"scene_{i}_dubbed.mp3")
        generate_dubbed_audio(translated, audio_path, target_language_clean)
        audio_files.append(audio_path)
        
        # Save translation for reference
        scene[f"narration_{target_language_clean}"] = translated
    
    # Save translated scenes
    with open(os.path.join(dub_dir, "scenes_translated.json"), "w") as f:
        json.dump(scenes, f, indent=2, ensure_ascii=False)
    
    # Swap audio into video
    dubbed_video_path = os.path.join(job_dir, f"{os.path.splitext(video_files[0])[0]}_{target_language_clean}.mp4")
    swap_audio(original_video, audio_files, dubbed_video_path)
    
    print(f"🏆 Pipeline 6 Complete: {dubbed_video_path}")
    
    return {
        "job_id": job_id,
        "language": target_language_clean,
        "dubbed_video_path": dubbed_video_path,
        "scenes_translated": len(scenes)
    }



if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2:
        result = run_dub_pipeline(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "hindi")
        print(json.dumps(result, indent=2))
