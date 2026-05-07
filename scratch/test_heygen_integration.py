import requests
import json
import time

def test_heygen_render():
    url = "http://localhost:8000/render"
    headers = {
        "X-API-Key": "etl_factory_prod_8291_secret",
        "Content-Type": "application/json"
    }
    
    payload = {
        "topic": "HeyGen Direct Mode Test",
        "markdown": "# HeyGen AI Avatar\nThis is a test of the direct professional AI avatar generation using HeyGen.",
        "render_mode": "heygen",
        "with_avatar": True
    }
    
    print(f"🚀 Submitting HeyGen render request...")
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        job_id = response.json()["job_id"]
        print(f"✅ Job {job_id} queued. Polling for status...")
        
        for _ in range(30): # Poll for 5 minutes
            status_url = f"http://localhost:8000/status/{job_id}"
            status_res = requests.get(status_url, headers=headers)
            status_data = status_res.json()
            print(f"[{time.strftime('%H:%M:%S')}] Status: {status_data['status']} | Progress: {status_data['progress']}%")
            
            if status_data["status"] == "completed":
                print(f"🏆 Render Completed!")
                print(f"🎬 Video URL: {status_data['video_url']}")
                return
            elif status_data["status"] == "failed":
                print(f"❌ Render Failed: {status_data['error']}")
                return
            
            time.sleep(10)

if __name__ == "__main__":
    test_heygen_render()
