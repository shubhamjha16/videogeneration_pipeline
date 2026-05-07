import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_URL = "http://localhost:8000/render"
API_KEY = os.environ.get("FACTORY_API_KEY", "")

def test_composite_input():
    print("🚀 Testing Composite Input (JSON + HTML + Markdown)...")
    
    payload = {
        "topic": "Composite Math Derivation Test",
        "json_data": [
            {"title": "Step 1: Initial Equation", "description": "Let us start with $E = mc^2$"}
        ],
        "html": "<h3>Step 2: Substitution</h3><p>Substitute $m = \\frac{m_0}{\\sqrt{1 - v^2/c^2}}$ into the equation.</p>",
        "markdown": "### Step 3: Final Form\n\nThe full derivation results in:\n\n$$E = \\frac{m_0 c^2}{\\sqrt{1 - v^2/c^2}}$$\n\nThis is the relativistic energy equation.",
        "render_mode": "manim",
        "video_type": "educational"
    }
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        job_id = data["job_id"]
        print(f"✅ Job queued successfully! Job ID: {job_id}")
        
        # Check logs/status if possible (requires waiting)
        print("Waiting for job to be initialized...")
        import time
        time.sleep(5)
        
        status_resp = requests.get(f"http://localhost:8000/status/{job_id}", headers=headers)
        status_data = status_resp.json()
        
        # Check logs for the initialization message
        logs = status_data.get("logs", [])
        init_msg = ""
        for log in logs:
            if "Job initialized" in log.get("msg", ""):
                init_msg = log["msg"]
                break
        
        print(f"\n--- Initialization Log ---")
        print(init_msg)
        
        if "Source: COMPOSITE (JSON+HTML+MARKDOWN)" in init_msg:
            print("\n✅ Verification Successful: Source type is correctly identified as COMPOSITE!")
        else:
            print("\n❌ Verification Failed: Source type is incorrect.")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")

if __name__ == "__main__":
    test_composite_input()
