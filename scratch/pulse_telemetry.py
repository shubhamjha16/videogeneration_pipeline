import json
import os
import time

JOBS_FILE = os.environ.get("JOBS_FILE_PATH", "jobs.json")

def pulse_research_log():
    if not os.path.exists(JOBS_FILE):
        print(f"❌ {JOBS_FILE} not found. skipping pulse.")
        return

    with open(JOBS_FILE, "r") as f:
        jobs = json.load(f)

    if not jobs:
        print("❌ No jobs found to pulse.")
        return

    # Take the first job and add a mock research log
    job_id = list(jobs.keys())[0]
    log_entry = {
        "node": "RESEARCH",
        "msg": "🔎 Mock Metasearch: 'Testing the new golden telemetry...'",
        "type": "info",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    
    if "logs" not in jobs[job_id]:
        jobs[job_id]["logs"] = []
    
    jobs[job_id]["logs"].append(log_entry)
    
    with open(JOBS_FILE, "w") as f:
        json.dump(jobs, f, indent=2)
    
    print(f"✅ Pulsed RESEARCH log to job {job_id}. Portal should now show golden highlight.")

if __name__ == "__main__":
    pulse_research_log()
