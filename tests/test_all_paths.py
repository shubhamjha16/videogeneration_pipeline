import requests
import time
import sys
import threading
import os

# Configuration
API_BASE = os.environ.get("FACTORY_API_BASE", "http://localhost:8000")
API_KEY  = os.environ.get("FACTORY_API_KEY", "your_factory_key")

def test_path(mode, topic, html):
    """Triggers a render and polls to completion."""
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "topic": topic,
        "html": html,
        "render_mode": mode,
        "video_type": "educational"
    }
    
    print(f"🚀 [INIT] Path: {mode.upper()} | Topic: {topic}")
    try:
        resp = requests.post(f"{API_BASE}/render", json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        job_id = resp.json().get("job_id")
        print(f"   [ID: {job_id}] Queued.")
    except Exception as e:
        print(f"   ❌ [ID: ERROR] Failed to submit {mode}: {e}")
        return False

    # Poll for completion
    start_t = time.time()
    while time.time() - start_t < 900: # 15 min max
        try:
            r = requests.get(f"{API_BASE}/status/{job_id}", headers=headers, timeout=5)
            r.raise_for_status()
            data = r.json()
            status = data.get("status")
            
            if status == "completed":
                print(f"✅ [SUCCESS] {mode.upper()}: {data.get('video_url')}")
                return True
            if status == "failed":
                print(f"❌ [FAILED] {mode.upper()}: {data.get('error')}")
                return False
        except Exception as e:
            pass # Silent retry on polling glitches
        time.sleep(15)
    
    print(f"⏰ [TIMEOUT] {mode.upper()}")
    return False

def run_all_tests():
    print("🧪 STARTING QUAD-PATH VALIDATION SUITE\n" + "="*40)
    
    tests = [
        ("manim", "Pythagorean Theorem", "<h1>Geometry</h1><p>a^2 + b^2 = c^2</p>"),
        ("presentation", "History of Rome", "<h1>History</h1><p>The rise and fall of the Roman Empire.</p>"),
        ("explainer", "The Water Cycle", "<h1>Science</h1><p>Evaporation, Condensation, Precipitation.</p>"),
        ("user_generated_video", "Safety Update", "<h1>Update</h1><p>Please wear your safety gear.</p>")
    ]
    
    threads = []
    for mode, topic, html in tests:
        t = threading.Thread(target=test_path, args=(mode, topic, html))
        threads.append(t)
        t.start()
        time.sleep(1) # Stagger start logs
        
    for t in threads:
        t.join()
        
    print("\n" + "="*40 + "\n🏁 ALL PATH TESTS CONCLUDED.")

if __name__ == "__main__":
    run_all_tests()
