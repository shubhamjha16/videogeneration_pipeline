import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = "http://localhost:8000/render"
API_KEY = os.environ.get("FACTORY_API_KEY", "")
headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

def test_appending_derivation():
    print("🚀 Testing Vertical Math Appending (formula_step_list)...")
    
    payload = {
        "topic": "Newton's Second Law",
        "markdown": """
        ### The Derivation
        The total energy of a particle is the sum of its rest energy and kinetic energy.
        
        1. $E^2 = (pc)^2 + (m_0 c^2)^2$
        2. For a particle at rest, $p = 0$.
        3. Therefore, $E^2 = (m_0 c^2)^2$
        4. Taking the square root: $E = m_0 c^2$
        """,
        "render_mode": "manim"
    }
    
    try:
        r = requests.post(API_URL, json=payload, headers=headers)
        r.raise_for_status()
        job_id = r.json()["job_id"]
        print(f"✅ Job queued successfully! Job ID: {job_id}")
        
        # We don't need to wait for full render, just check the scene plan in status logs
        import time
        for _ in range(10):
            time.sleep(5)
            status_resp = requests.get(f"http://localhost:8000/status/{job_id}", headers=headers)
            status_data = status_resp.json()
            
            logs = status_data.get("logs", [])
            for log in logs:
                if "[DIRECTOR]" in log.get("msg", "") and "Planned" in log.get("msg", ""):
                    print(f"\n--- Director's Plan ---")
                    print(log["msg"])
                    return
            
            print(f"Waiting for Director... (Status: {status_data.get('status')})")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_appending_derivation()
