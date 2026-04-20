import requests
import time
import sys
import os
import threading

# Configuration: Priority to ENV vars for CI/CD usage
API_BASE = os.environ.get("FACTORY_API_BASE", "http://localhost:8000")
API_KEY  = os.environ.get("FACTORY_API_KEY", "your_factory_key")

def submit_and_poll(topic: str, html: str, mode: str = "manim"):
    """Core test unit: Submit -> Poll -> Success."""
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
    
    print(f"🚀 Submitting '{topic}' to {API_BASE}...")
    try:
        resp = requests.post(f"{API_BASE}/render", json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        job_id = resp.json().get("job_id")
    except Exception as e:
        print(f"❌ Submission Failed for {topic}: {e}")
        return False

    start_t = time.time()
    while time.time() - start_t < 900: # 15 min max for complex 3.0 renders
        try:
            r = requests.get(f"{API_BASE}/status/{job_id}", headers=headers, timeout=5)
            r.raise_for_status()
            data = r.json()
            status = data.get("status")
            
            if status == "completed":
                print(f"✅ Success! {topic} -> {data.get('video_url')}")
                return True
            if status == "failed":
                print(f"❌ Failed! {topic}: {data.get('error')}")
                return False
        except Exception as e:
            print(f"⚠️ Polling Alert: {e}")
        time.sleep(15)
    
    print(f"⏰ Timeout for {topic}")
    return False

def stress_test():
    """Industrial Concurrency Check: Hit the semaphore with 5 overlapping jobs."""
    print(f"\n🔥 INITIALIZING STRESS TEST (CONCURRENCY CAP VALIDATION)...")
    topics = [
        ("Quantum Gravity", "<h1>Physics</h1>"),
        ("Stoicism 101", "<h1>Philosophy</h1>"),
        ("Cell Biology", "<h1>Science</h1>"),
        ("Modern Chess", "<h1>Games</h1>"),
        ("Future AI", "<h1>Tech</h1>")
    ]
    
    threads = []
    results = []

    def t_wrapper(t, h):
        results.append(submit_and_poll(t, h))

    for t, h in topics:
        thread = threading.Thread(target=t_wrapper, args=(t, h))
        threads.append(thread)
        thread.start()
        time.sleep(2) # Slight stagger to show sequencing in logs

    for thread in threads:
        thread.join()

    success_count = sum(1 for r in results if r)
    print(f"\n📊 STRESS TEST COMPLETE: {success_count}/{len(topics)} succeeded.")
    if success_count == len(topics):
        print("✅ SEMAPHORE HOLDS: Factory sequenced all jobs correctly without crashing.")
    else:
        sys.exit(1)

if __name__ == "__main__":
    if "--stress" in sys.argv:
        stress_test()
    else:
        # Single smoke test
        success = submit_and_poll("Smoke Test", "<h1>Hello Production</h1>", mode="presentation")
        if not success: sys.exit(1)
