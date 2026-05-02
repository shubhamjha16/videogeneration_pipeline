import requests
import time
import json

API_URL = "http://localhost:8000/render"
HEADERS = {"x-api-key": "etl_factory_prod_8291_secret"}

def trigger_render(name, steps):
    payload = {
        "topic": name,
        "markdown": f"# {name}\n\nMathematical Derivation:\n\n" + "\n\n".join([f"$${s}$$" for s in steps]),
        "options": {"quality": "low"},
        "render_mode": "manim"
    }
    print(f"🚀 Queueing job for: {name}")
    resp = requests.post(API_URL, json=payload, headers=HEADERS)
    if resp.status_code == 200:
        return resp.json()["job_id"]
    else:
        print(f"❌ Failed: {resp.text}")
        return None

# Test Cases
tests = [
    ("3-Step Math Derivation", ["A=B", "B=C", "A=C"]),
    ("7-Step Algebra Derivation", [f"x_{i} = x_{i-1} + 1" for i in range(1, 8)]),
    ("12-Step Calculus Proof", [f"\\frac{{d^{{{i}}}y}}{{dx^{{{i}}}}} = f^{{({i})}}(x)" for i in range(1, 13)]),
    ("Pythagorean Theorem Proof", ["a^2 + b^2 = c^2", "a^2 = c^2 - b^2", "a = \\sqrt{c^2 - b^2}"]),
    ("Cardiac Output Calculation", ["CO = HR \\times SV", "HR = 72", "SV = 70", "CO = 72 \\times 70", "CO = 5040 ml/min"])
]

job_ids = {}
for name, steps in tests:
    jid = trigger_render(name, steps)
    if jid:
        job_ids[name] = jid

print("\n📡 Jobs submitted. Monitoring status...")

while job_ids:
    for name, jid in list(job_ids.items()):
        s_resp = requests.get(f"http://localhost:8000/status/{jid}", headers=HEADERS)
        data = s_resp.json()
        status = data.get("status")
        if status == "completed":
            print(f"✅ {name} DONE: {data.get('video_url')}")
            del job_ids[name]
        elif status == "failed":
            print(f"❌ {name} FAILED: {data.get('error')}")
            del job_ids[name]
        else:
            print(f"⏳ {name}: {status} ({data.get('progress')}%)")
    time.sleep(10)
