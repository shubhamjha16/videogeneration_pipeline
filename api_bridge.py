"""
API Bridge — EaseToLearn Video Generation Service
Receives lesson HTML from Tony AI Spring Boot backend,
runs the full LangGraph pipeline, and returns a video URL.

Endpoints:
  POST /render          — start a video generation job
  GET  /status/{job_id} — poll job status
  GET  /health          — health check for ECS / load balancer

Flow:
  Spring Boot → POST /render {topic, html}
              ← {job_id}
  Spring Boot → GET /status/{job_id}
              ← {status: "completed", video_url: "https://s3..."}
  OR webhook  ← POST to WEBHOOK_URL {job_id, status, video_url}
"""

import os
import uuid
import threading
import requests
import json

_jobs_lock = threading.Lock()
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="EaseToLearn Video Generation Service", version="2.0.0")

# CORS — allow Spring Boot backend on same VPC
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # restrict to Spring Boot IP in production via env
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# ── Persistence Helper ────────────────────────────────────────────────────────
JOBS_FILE = "jobs.json"

def _load_jobs():
    if os.path.exists(JOBS_FILE):
        try:
            with open(JOBS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def _save_jobs():
    with _jobs_lock:
        with open(JOBS_FILE, "w") as f:
            json.dump(jobs, f, indent=2)

# ── In-memory job store ───────────────────────────────────────────────────────
jobs: dict = _load_jobs()


# ── Request / Response schemas ────────────────────────────────────────────────

class RenderRequest(BaseModel):
    topic: str
    html:  str


class JobStatus(BaseModel):
    job_id:    str
    status:    str        # queued | processing | completed | failed
    video_url: str = ""
    error:     str = ""


# ── Pipeline runner ───────────────────────────────────────────────────────────

def _run_pipeline(job_id: str, topic: str, html: str):
    """Run the full LangGraph pipeline in a background thread."""
    with _jobs_lock:
        jobs[job_id]["status"] = "processing"

    try:
        from autonomous_graph import app as graph

        final_state = graph.invoke({
            "raw_input":         html,
            "topic":             topic,
            "attempt_count":     0,
            "parsed_facts":      None,
            "render_mode":       None,
            "scenes":            None,
            "image_path":        None,
            "audio_files":       None,
            "manim_script_path": None,
            "output_path":       None,
            "video_url":         None,
            "rendering_errors":  None,
        })

        video_url = final_state.get("video_url") or ""

        with _jobs_lock:
            if video_url:
                jobs[job_id]["status"]    = "completed"
                jobs[job_id]["video_url"] = video_url
                print(f"✅ Job {job_id} completed: {video_url}")
            else:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["error"]  = final_state.get("rendering_errors", "No output produced")
                print(f"❌ Job {job_id} failed: {jobs[job_id]['error']}")

    except Exception as e:
        with _jobs_lock:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"]  = str(e)
        print(f"❌ Job {job_id} exception: {e}")

    _save_jobs()

    # ── Webhook callback to Spring Boot ───────────────────────────────────────
    webhook_url = os.environ.get("WEBHOOK_URL")
    if webhook_url:
        try:
            requests.post(webhook_url, json=jobs[job_id], timeout=10)
            print(f"📡 Webhook sent to {webhook_url}")
        except Exception as e:
            print(f"⚠️  Webhook failed: {e}")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/render", response_model=JobStatus)
def start_render(request: RenderRequest):
    """
    Start a video generation job.
    Spring Boot calls this with the Tony AI lesson HTML.
    Returns job_id immediately — video is generated in background.
    """
    if not request.topic or not request.html:
        raise HTTPException(status_code=400, detail="topic and html are required")

    job_id = str(uuid.uuid4())[:12]
    jobs[job_id] = {
        "job_id":    job_id,
        "status":    "queued",
        "video_url": "",
        "error":     "",
    }

    thread = threading.Thread(
        target=_run_pipeline,
        args=(job_id, request.topic, request.html),
        daemon=True,
    )
    thread.start()
    _save_jobs()

    print(f"🚀 Job {job_id} queued for: {request.topic}")
    return jobs[job_id]


@app.get("/status/{job_id}", response_model=JobStatus)
def get_status(job_id: str):
    """
    Poll job status.
    Spring Boot polls this every 5s until status is 'completed' or 'failed'.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@app.get("/health")
def health():
    """ECS / ALB health check endpoint."""
    return {"status": "ok", "service": "easetolearn-video-generation"}


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
