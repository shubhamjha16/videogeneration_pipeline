import os
import sys
import time
import threading
import requests
import uvicorn
from datetime import datetime

# Set up test environment
os.environ["FACTORY_API_KEY"] = "load_test_key"
os.environ["JOBS_FILE_PATH"] = "jobs_load_test.json"

# Import api_bridge after setting env
import api_bridge

# Store metrics
job_states = {}  # job_id -> [(timestamp, status)]
metrics_lock = threading.Lock()

# Custom mock for _run_pipeline to simulate work safely under Semaphore
def mock_run_pipeline(job_id, topic, html, source_type="html", overrides=None):
    global job_states
    
    # 1. Start in queue
    with metrics_lock:
        if job_id not in job_states:
            job_states[job_id] = []
        job_states[job_id].append((time.time(), "queued"))
        
    # Wait for RENDER_SEMAPHORE slot
    with api_bridge.RENDER_SEMAPHORE:
        # Transition to processing
        with metrics_lock:
            if job_id not in job_states:
                job_states[job_id] = []
            job_states[job_id].append((time.time(), "processing"))
            
        with api_bridge._jobs_lock:
            api_bridge.jobs[job_id]["status"] = "processing"
            api_bridge.jobs[job_id]["progress"] = 10
            api_bridge.jobs[job_id]["updated_at"] = datetime.utcnow().isoformat() + "Z"
        api_bridge._safe_save_jobs(f"mock pipeline start ({job_id})")
        
        print(f"   🟢 [SEMAPHORE ACQUIRED] Job {job_id} is now processing...")
        time.sleep(3)  # Simulate 3 seconds of render work
        
        # Transition to completed
        with metrics_lock:
            if job_id not in job_states:
                job_states[job_id] = []
            job_states[job_id].append((time.time(), "completed"))
            
        with api_bridge._jobs_lock:
            api_bridge.jobs[job_id]["status"] = "completed"
            api_bridge.jobs[job_id]["progress"] = 100
            api_bridge.jobs[job_id]["video_url"] = f"https://cdn.easetolearn.com/videos/{job_id}.mp4"
            api_bridge.jobs[job_id]["updated_at"] = datetime.utcnow().isoformat() + "Z"
        api_bridge._safe_save_jobs(f"mock pipeline complete ({job_id})")
        print(f"   🔴 [SEMAPHORE RELEASED] Job {job_id} completed.")

# Apply the mock to api_bridge
api_bridge._run_pipeline = mock_run_pipeline

def start_server():
    """Starts the FastAPI server on port 8001"""
    uvicorn.run(api_bridge.app, host="127.0.0.1", port=8001, log_level="warning")

def submit_render(topic, index):
    """Submits a single render job to the API"""
    url = "http://127.0.0.1:8001/render"
    headers = {
        "X-API-Key": "load_test_key",
        "Content-Type": "application/json"
    }
    payload = {
        "topic": topic,
        "html": f"<h1>{topic}</h1><p>Teacher {index} lesson content.</p>",
        "render_mode": "explainer"
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=5)
        resp.raise_for_status()
        job_id = resp.json().get("job_id")
        with metrics_lock:
            if job_id not in job_states:
                job_states[job_id] = []
            job_states[job_id].append((time.time(), "submitted"))
        return job_id
    except Exception as e:
        print(f"❌ Failed to submit job {index}: {e}")
        return None

def run_stress_test():
    print("=" * 60)
    print("🚀 STARTING CONCURRENCY & RENDER_SEMAPHORE LOAD TEST")
    print("🎯 Simulating 10 teachers triggering renders simultaneously...")
    print("=" * 60)

    # 1. Start Server
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(2)  # Allow server to boot
    
    # 2. Trigger 10 concurrent requests
    threads = []
    job_ids = []
    
    print("\n🔥 Submitting 10 overlapping render requests...")
    for i in range(10):
        topic = f"Math Lesson Part {i+1}"
        job_id = submit_render(topic, i+1)
        if job_id:
            job_ids.append(job_id)
        time.sleep(0.1)  # Stagger slightly to represent realistic button clicks
        
    print(f"✅ Successfully queued {len(job_ids)} jobs on the factory.")
    print("⏳ Monitoring concurrency transitions (takes ~15 seconds)...")

    # 3. Wait for all background threads to complete rendering
    start_monitoring = time.time()
    while True:
        # Check active status of jobs
        all_completed = True
        for jid in job_ids:
            with api_bridge._jobs_lock:
                status = api_bridge.jobs[jid]["status"]
                if status not in ["completed", "failed"]:
                    all_completed = False
                    break
        if all_completed or (time.time() - start_monitoring > 30):
            break
        time.sleep(0.5)

    print("\n" + "=" * 60)
    print("📊 ANALYZING SEMAPHORE CONCURRENCY METRICS")
    print("=" * 60)

    # Analyze state changes over time
    # We want to measure the number of active "processing" jobs at any single timestamp.
    active_jobs = {k: v for k, v in job_states.items() if v}
    if not active_jobs:
        print("❌ ERROR: No active job events recorded!")
        sys.exit(1)
        
    min_time = min(events[0][0] for events in active_jobs.values())
    max_time = max(events[-1][0] for events in active_jobs.values())
    
    timeline_steps = int((max_time - min_time) / 0.1)
    max_concurrent_processing = 0
    concurrency_violated = False

    print(f"Timeline analyzed: {max_time - min_time:.2f} seconds")
    print("\nActive slots sample:")
    
    for step in range(timeline_steps):
        t = min_time + (step * 0.1)
        active_processing_count = 0
        
        for jid, events in active_jobs.items():
            # Find the state of this job at time t
            current_state = "unknown"
            for event_time, state in events:
                if event_time <= t:
                    current_state = state
                else:
                    break
            if current_state == "processing":
                active_processing_count += 1
                
        if active_processing_count > max_concurrent_processing:
            max_concurrent_processing = active_processing_count
            
        if active_processing_count > 2:
            concurrency_violated = True
            
        # Log active slots occasionally for visualization
        if step % 10 == 0:
            slots = "█" * active_processing_count + "░" * (2 - active_processing_count) if active_processing_count <= 2 else "█" * active_processing_count
            print(f"  Time {t - min_time:.1f}s: Slots [{slots}] ({active_processing_count} processing)")

    print("\n" + "=" * 60)
    print("🏁 LOAD TEST CONCLUSION")
    print("=" * 60)
    print(f"Max Concurrent Processing Jobs observed: {max_concurrent_processing}")
    print(f"Expected Maximum Concurrency Cap     : 2 (from RENDER_SEMAPHORE)")
    
    # Cleanup temp file
    if os.path.exists("jobs_load_test.json"):
        os.remove("jobs_load_test.json")
        
    if max_concurrent_processing == 2 and not concurrency_violated:
        print("\n✅ PASS: Concurrency Limit was strictly enforced!")
        print("✅ The BoundedSemaphore successfully restricted active processing slots to exactly 2.")
        print("✅ Remaining jobs safely queued, sequencing automatically as slots opened.")
        sys.exit(0)
    else:
        print("\n❌ FAIL: Concurrency Cap was violated or not met!")
        print(f"Observed concurrent processing limit: {max_concurrent_processing}")
        sys.exit(1)

if __name__ == "__main__":
    run_stress_test()
