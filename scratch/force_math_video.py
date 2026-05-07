import requests
import json
import time

API_URL = "http://localhost:8000/render"

# Simple, bulletproof LaTeX derivation to ensure rendering success
curriculum = """
# 10-Step Derivation Stress Test
Watch as the history appends vertically with dynamic scaling.

### The Derivation
1. $$f(x) = x^2 + 2x + 1$$
2. $$f'(x) = \\frac{d}{dx}(x^2 + 2x + 1)$$
3. $$f'(x) = 2x + 2$$
4. $$f''(x) = \\frac{d}{dx}(2x + 2)$$
5. $$f''(x) = 2$$
6. $$f'''(x) = 0$$
7. $$Integral: \\int f(x) dx$$
8. $$= \\int (x^2 + 2x + 1) dx$$
9. $$= \\frac{x^3}{3} + x^2 + x + C$$
10. $$Done!$$
"""

payload = {
    "topic": "Pythagorean Theorem Derivation",
    "markdown": curriculum,
    "options": {
        "aspect_ratio": "16:9",
        "resolution": "1080p",
        "quality": "high"
    }
}

print(f"🚀 Triggering high-fidelity math video render...")
headers = {"x-api-key": "etl_factory_prod_8291_secret"}
response = requests.post(API_URL, json=payload, headers=headers)

if response.status_code == 200:
    job_id = response.json().get("job_id")
    print(f"✅ Job queued: {job_id}")
    
    # Poll for completion
    while True:
        status_resp = requests.get(f"http://localhost:8000/status/{job_id}", headers=headers)
        data = status_resp.json()
        status = data.get("status")
        progress = data.get("progress", 0)
        
        print(f"⏳ Status: {status} | Progress: {progress}%")
        
        if status == "completed":
            print(f"\n🎉 VIDEO RENDERED SUCCESSFULLY!")
            print(f"📁 Path: {data.get('video_url')}")
            break
        elif status == "failed":
            print(f"\n❌ Render failed. Error: {data.get('error')}")
            break
            
        time.sleep(5)
else:
    print(f"❌ Failed to queue job: {response.text}")
