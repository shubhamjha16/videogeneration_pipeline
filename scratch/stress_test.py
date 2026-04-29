import requests
import json
import threading
import time

def trigger_job(topic, text):
    url = "http://localhost:8000/render"
    headers = {"X-API-Key": "etl_factory_prod_8291_secret"}
    payload = {
        "topic": topic,
        "markdown": text,
        "render_mode": "manim",
        "with_avatar": False
    }
    
    try:
        print(f"🚀 Triggering: {topic}")
        response = requests.post(url, json=payload, headers=headers)
        print(f"✅ {topic}: {response.status_code} - {response.json().get('job_id')}")
    except Exception as e:
        print(f"❌ {topic} Failed: {e}")

def run_stress_test():
    topics = [
        ("Gravity Stress Test", "# Gravity\nGravity is the force by which a planet or other body draws objects toward its center."),
        ("Optics Stress Test", "# Optics\nOptics is the branch of physics that studies the behaviour and properties of light."),
        ("Atoms Stress Test", "# Atoms\nAn atom is the smallest unit of ordinary matter that forms a chemical element.")
    ]
    
    threads = []
    for topic, text in topics:
        t = threading.Thread(target=trigger_job, args=(topic, text))
        threads.append(t)
        t.start()
        time.sleep(1) # Small stagger
        
    for t in threads:
        t.join()

if __name__ == "__main__":
    run_stress_test()
