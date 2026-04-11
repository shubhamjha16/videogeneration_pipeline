import os
import requests
from dotenv import load_dotenv

load_dotenv()

def discover():
    api_id = os.environ.get("HIGGSFIELD_API_ID")
    api_key = os.environ.get("HIGGSFIELD_API_KEY")
    
    # Common Muapi/Aggregator patterns
    bases = [
        "https://api.muapi.ai/api/v1",
        "https://muapi.ai/api/v1",
        "https://api.muapi.ai",
        "https://muapi.ai"
    ]
    
    endpoints = [
        "/predictions",
        "/generate",
        "/predict",
        f"/models/{api_id}/predict",
        f"/models/{api_id}/generate",
        f"/{api_id}",
        "/generate_video",
        "/predictions/video"
    ]
    
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }

    print(f"🔍 Starting Muapi Endpoint Discovery (ID: {api_id[:8]}...)")
    
    found = False
    for base in bases:
        for ep in endpoints:
            url = f"{base}{ep}"
            try:
                # Use a dummy prompt to see if we get a 200, 201 or a specific Auth error
                # 404 means wrong path. 401/403 means right path, maybe wrong key or just auth rejected.
                # 422 means right path, wrong payload.
                response = requests.post(url, headers=headers, json={"prompt": "test"}, timeout=5)
                
                status = response.status_code
                print(f"   [{status}] {url}")
                
                if status in [200, 201, 202, 422]:
                    print(f"   ✨ POTENTIAL MATCH FOUND: {url}")
                    found = True
                elif status in [401, 403]:
                    # Some paths might require a key even to see they exist, but 401 is better than 404
                    print(f"   🔑 Valid path but Auth Denied: {url}")
                    found = True
                    
            except Exception as e:
                # print(f"   [ERR] {url}: {e}")
                pass
                
    if not found:
        print("   ❌ No valid endpoint found. Investigating alternative Higgsfield direct hosts...")
        # Try direct Higgsfield if Muapi is failing
        h_urls = ["https://api.higgsfield.ai/v1/generate", "https://api.higgsfield.ai/generate"]
        for h_url in h_urls:
            try:
                res = requests.post(h_url, headers={"Authorization": f"Bearer {api_key}"}, json={"prompt": "test"}, timeout=5)
                print(f"   [{res.status_code}] {h_url}")
            except: pass

if __name__ == "__main__":
    discover()
