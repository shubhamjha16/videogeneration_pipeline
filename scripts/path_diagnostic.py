import os
import subprocess
import requests
from dotenv import load_dotenv

def check_env():
    load_dotenv()
    print("🔍 [Diagnostic] Environment Audit")
    keys = [
        "ANTHROPIC_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY", 
        "HIGGSFIELD_API_KEY", "HEYGEN_API_KEY",
        "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "S3_BUCKET"
    ]
    for k in keys:
        status = "✅ Found" if os.environ.get(k) else "❌ MISSING"
        print(f"   - {k:25}: {status}")

def check_engines():
    print("\n🔍 [Diagnostic] Local Engine Audit")
    
    # 1. Manim
    try:
        res = subprocess.run(["manim", "--version"], capture_output=True, text=True)
        print(f"   - Manim CLI                : ✅ Found ({res.stdout.splitlines()[0]})")
    except:
        print("   - Manim CLI                : ❌ NOT FOUND (Path 1 will fail)")

    # 2. FFmpeg
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        res = subprocess.run([exe, "-version"], capture_output=True, text=True)
        print(f"   - FFmpeg (imageio)         : ✅ Found ({res.stdout.splitlines()[0][:30]}...)")
    except:
        print("   - FFmpeg (imageio)         : ❌ NOT FOUND (All paths will fail)")

def check_apis():
    print("\n🔍 [Diagnostic] API Connectivity Audit")
    
    # 1. Groq (Fastest check)
    try:
        from groq import Groq
        client = Groq()
        client.models.list()
        print("   - Groq API Connectivity    : ✅ OK")
    except Exception as e:
        print(f"   - Groq API Connectivity    : ❌ FAILED ({str(e)[:50]})")

    # 2. HeyGen (Connectivity check via avatars endpoint)
    try:
        api_key = os.environ.get("HEYGEN_API_KEY")
        res = requests.get("https://api.heygen.com/v2/avatars", headers={"x-api-key": api_key}, timeout=5)
        if res.status_code == 200 or res.status_code == 401: # 401 means key is checked but maybe wrong, 200 is success
            print(f"   - HeyGen API (v2 Avatars) : ✅ Response {res.status_code}")
        else:
            print(f"   - HeyGen API (v2 Avatars) : ⚠️  Response {res.status_code}")
    except Exception as e:
        print(f"   - HeyGen API               : ❌ FAILED ({str(e)[:50]})")

if __name__ == "__main__":
    check_env()
    check_engines()
    check_apis()
