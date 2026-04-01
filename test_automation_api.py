import requests
import time

# The URL of our locally running FastAPI server
API_URL = "http://localhost:8000/generate"

def test_auto_pilot(topic, text):
    print(f"🚀 Sending text to EaseToLearn Video Factory...")
    print(f"📂 Topic: {topic}")
    print(f"📝 Text: {text[:50]}...")
    
    payload = {
        "topic": topic,
        "text": text,
        "mode": "auto" # The server will decide if it's Math or Bio
    }
    
    try:
        response = requests.post(API_URL, json=payload)
        data = response.json()
        
        if response.status_code == 200:
            job_id = data['job_id']
            print(f"✅ Job Queued! ID: {job_id}")
            print(f"⏳ Waiting for background process to start...")
            
            # Poll for status
            while True:
                status_resp = requests.get(f"http://localhost:8000/status/{job_id}")
                status = status_resp.json()['status']
                print(f"📢 Current Status: {status}")
                
                if status == "Completed":
                    print(f"\n🎉 SUCCESS! Your video is ready in the 'output' folder.")
                    break
                elif "Error" in status:
                    print(f"\n❌ FAILED: {status}")
                    break
                
                time.sleep(5)
        else:
            print(f"❌ Error: {data}")
            
    except Exception as e:
        print(f"❌ Connection Error: Is the 'main.py' server running?")

if __name__ == "__main__":
    # Test with a Physics problem
    test_auto_pilot(
        topic="Gravity Test",
        text="Explain why objects fall at 9.8 m/s^2. It is because of Earth's gravitational pull."
    )
