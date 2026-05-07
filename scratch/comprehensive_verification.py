import json
import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_URL = "http://localhost:8000/render"
API_KEY = os.environ.get("FACTORY_API_KEY", "")
headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

def wait_for_job(job_id, timeout=300):
    print(f"⏳ Waiting for job {job_id} to complete...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            r = requests.get(f"http://localhost:8000/status/{job_id}", headers=headers)
            r.raise_for_status()
            data = r.json()
            status = data.get("status")
            print(f"   Status: {status} ({data.get('progress', 0)}%)")
            
            if status == "completed":
                print(f"✅ Job {job_id} completed successfully!")
                return data
            if status == "failed":
                print(f"❌ Job {job_id} failed: {data.get('error')}")
                return data
        except Exception as e:
            print(f"   ⚠️ Error checking status: {e}")
        
        time.sleep(10)
    print(f"🛑 Timeout reached for job {job_id}")
    return None

def test_1_composite_math():
    print("\n--- Test 1: Composite Math Derivation ---")
    payload = {
        "topic": "Quadratic Formula Derivation",
        "json_data": [
            {"title": "Start", "description": "We start with the quadratic equation: $ax^2 + bx + c = 0$"}
        ],
        "html": "<div>Divide by $a$: $x^2 + \\frac{b}{a}x + \\frac{c}{a} = 0$</div>",
        "markdown": "Move the constant term:\n\n$x^2 + \\frac{b}{a}x = -\\frac{c}{a}$\n\nNow complete the square...",
        "render_mode": "manim"
    }
    r = requests.post(API_URL, json=payload, headers=headers)
    job_id = r.json()["job_id"]
    return wait_for_job(job_id)

def test_2_regression_mcq():
    print("\n--- Test 2: Regression - Medical MCQ (Single Format) ---")
    # Using a typical MCQ from past sessions
    payload = {
        "topic": "Pulmonary Edema Diagnosis",
        "html": """
        <h3>Clinical Case</h3>
        <p>A 65-year-old male presents with acute shortness of breath. CXR shows Kerley B lines and bat-wing opacities.</p>
        <p>A. Mitral Stenosis</p>
        <p>B. Pulmonary Embolism</p>
        <p>C. Pneumothorax</p>
        <p>D. Asthma</p>
        <p><strong>Correct Answer: A</strong></p>
        <p>Explanation: Kerley B lines are indicative of pulmonary congestion, often seen in Mitral Stenosis leading to heart failure.</p>
        """,
        "render_mode": "manim"
    }
    r = requests.post(API_URL, json=payload, headers=headers)
    job_id = r.json()["job_id"]
    return wait_for_job(job_id)

def test_3_adversarial_latex():
    print("\n--- Test 3: Adversarial LaTeX & Mixed Formats ---")
    payload = {
        "topic": "Complex LaTeX Merge",
        "json_data": {"title": "Nested Braces", "content": "Formula: $\\frac{1}{1 + \\frac{1}{x}}$"},
        "markdown": "Display math with mixed delimiters:\n\n$$ \\sum_{i=1}^{n} i = \\frac{n(n+1)}{2} $$\n\nAnd some $inline \\alpha$ here.",
        "render_mode": "manim"
    }
    r = requests.post(API_URL, json=payload, headers=headers)
    job_id = r.json()["job_id"]
    return wait_for_job(job_id)

if __name__ == "__main__":
    # Ensure server is reachable
    try:
        requests.get("http://localhost:8000/docs")
    except:
        print("❌ Server is not running on localhost:8000. Please start it first.")
        exit(1)

    results = []
    results.append(("Composite Math", test_1_composite_math()))
    results.append(("Regression MCQ", test_2_regression_mcq()))
    results.append(("Adversarial LaTeX", test_3_adversarial_latex()))

    print("\n\n=== FINAL SUMMARY ===")
    for name, res in results:
        if res and res.get("status") == "completed":
            print(f"✅ {name}: PASSED")
            print(f"   Video: {res.get('video_url')}")
        else:
            print(f"❌ {name}: FAILED")
