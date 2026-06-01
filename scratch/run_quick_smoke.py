import os
import requests
import json

API_URL = "http://localhost:8000/render"
FACTORY_API_KEY = "etl_factory_prod_8291_secret"
headers = {
    "X-API-Key": FACTORY_API_KEY,
    "Content-Type": "application/json"
}

def trigger_job(payload):
    try:
        r = requests.post(API_URL, json=payload, headers=headers)
        r.raise_for_status()
        res = r.json()
        print(f"🚀 [Trigger] Successfully enqueued job: {res.get('job_id')} | Topic: '{payload['topic']}' | Render Mode: {payload.get('render_mode')}")
        return res.get('job_id')
    except Exception as e:
        print(f"❌ [Trigger] Failed for '{payload['topic']}': {e}")
        if 'r' in locals() and r.text:
            print(f"   Response: {r.text}")
        return None

if __name__ == "__main__":
    print("🎬 Starting Fast Webhook & Ingestion Smoke Tests...")

    # 1. Spring Boot SolutionV2 Ingestion test (Presentation Mode)
    payload_presentation = {
        "topic": "Cavernous Sinus Anatomy",
        "render_mode": "presentation",
        "solution_v2": [
            {
                "title": "Concept Explanation",
                "description": "The cavernous sinus is a critical paired venous structure at the skull base containing CN III, IV, V1, V2, VI, and the internal carotid artery."
            },
            {
                "title": "Final Answer",
                "description": "Option B — Internal carotid artery"
            }
        ]
    }

    # 2. Manim Mathematical Ingestion test
    payload_manim = {
        "topic": "Euler Identity Derivation",
        "render_mode": "manim",
        "markdown": "Verify that $e^{i\\pi} + 1 = 0$ using Taylor Series expansion."
    }

    # 3. Explainer Slides Ingestion test
    payload_explainer = {
        "topic": "Active Transport vs Passive Diffusion",
        "render_mode": "explainer",
        "html": "<h3>Active Transport</h3><p>Requires ATP to move molecules against concentration gradient.</p>"
    }

    job_1 = trigger_job(payload_presentation)
    job_2 = trigger_job(payload_manim)
    job_3 = trigger_job(payload_explainer)

    print("\n=== Active Pipeline Verification Status ===")
    for name, jid in [("Spring Boot Ingest", job_1), ("Manim Ingest", job_2), ("Explainer Ingest", job_3)]:
        if jid:
            status_url = f"http://localhost:8000/status/{jid}"
            try:
                r = requests.get(status_url, headers=headers)
                state = r.json()
                print(f"✅ {name}: Job {jid} is currently '{state.get('status')}' (Step: {state.get('current_step')})")
            except Exception as e:
                print(f"⚠️ {name}: Could not query job {jid}: {e}")
        else:
            print(f"❌ {name}: Failed to trigger")
