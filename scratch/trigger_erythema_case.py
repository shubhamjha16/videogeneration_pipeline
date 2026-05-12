import requests
import json
import time

url = "http://localhost:8000/render"
payload = {
  "topic": "Erythema Multiforme",
  "solution_v2": [
    {
      "title": "Concept Explanation",
      "description": "Target lesions are hallmark of erythema multiforme with bull's eye appearance. Central dusky area surrounded by erythematous ring."
    },
    {
      "title": "Option Analysis",
      "description": "A. Pemphigus - flaccid bullae, wrong. B. Bullous pemphigoid - tense bullae, wrong. C. Erythema multiforme - target lesions, CORRECT. D. Dermatitis herpetiformis - grouped vesicles, wrong."
    },
    {
      "title": "Final Answer",
      "description": "Option C: Erythema multiforme"
    }
  ],
  "image_path": "https://upload.wikimedia.org/wikipedia/commons/a/a6/Erythema_multiforme.jpg",
  "render_mode": "manim",
  "overrides": {
    "has_static_image": True
  }
}

print(f"🚀 Triggering Erythema Multiforme render with SolutionV2 and Image Injection...")

# Internal graph trigger
from autonomous_graph import app, get_job_dir
import requests, shutil, os

job_id = f"erythema_{int(time.time())}"
job_dir = f"output/job_{job_id}"
os.makedirs(job_dir, exist_ok=True)

# 📸 Manual Image Injection (Simulating api_bridge)
image_url = payload["image_path"]
print(f"📸 Injecting image from URL: {image_url}")
try:
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}
    resp = requests.get(image_url, headers=headers, timeout=30)
    resp.raise_for_status()
    dest = os.path.join(job_dir, "tony_diagram.png")
    with open(dest, 'wb') as f:
        f.write(resp.content)
    print(f"✅ Image injected to: {dest} ({len(resp.content)} bytes)")
except Exception as e:
    print(f"⚠️ Failed to inject image: {e}")

state = {
    "topic": payload["topic"],
    "solution_v2": payload["solution_v2"],
    "raw_input": payload["solution_v2"],
    "image_path": payload["image_path"],
    "render_mode": payload["render_mode"],
    "overrides": payload["overrides"],
    "video_type": "educational",
    "attempt_count": 0,
    "ledger": {},
    "scenes": [],
    "job_id": job_id,
    "rendering_errors": "",
    "progress_logs": [],
    "with_avatar": False
}
for output in app.stream(state, {"configurable": {"thread_id": "erythema_test"}}):
        for node_name, node_state in output.items():
            print(f"\n--- Node: {node_name} ---")
            if "rendering_errors" in node_state and node_state["rendering_errors"]:
                print(f"❌ Error: {node_state['rendering_errors']}")
            if "output_path" in node_state and node_state["output_path"]:
                print(f"✅ FINAL VIDEO: {node_state['output_path']}")
