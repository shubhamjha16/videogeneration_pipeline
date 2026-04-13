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

_jobs_lock = threading.RLock()
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal, Optional
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="EaseToLearn Video Generation Service", version="2.0.0")

allowed_origins_env = os.environ.get("ALLOWED_ORIGINS")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",")] if allowed_origins_env else ["*"]

if not allowed_origins_env and not os.environ.get("FACTORY_API_KEY"):
    print("⚠️  SECURITY WARNING: ALLOWED_ORIGINS and FACTORY_API_KEY both unset. API is completely open!")

# CORS — strictly restrict origins via env var (REQUIRED in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["X-API-Key", "Content-Type", "Authorization"],
    allow_credentials=True,
)

# ── Security Sentinel ──────────────────────────────────────────────────────────

def verify_api_key(api_key: str = Header(None, alias="X-API-Key")):
    """Industrial Sentinel: Checks for X-API-Key if FACTORY_API_KEY is set."""
    expected_key = os.environ.get("FACTORY_API_KEY")
    if expected_key and api_key != expected_key:
        raise HTTPException(status_code=403, detail="Unauthorized: Invalid Factory API Key")
    return api_key

SecurityDep = Depends(verify_api_key)


# ── Persistence Helper ────────────────────────────────────────────────────────# Persistence
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JOBS_FILE = os.environ.get("JOBS_FILE_PATH", "/tmp/jobs.json")
jobs = {}

# Industrial Concurrency Cap: Max 3 high-compute jobs (Manim/Video) at once
# This prevents RAM/CPU exhaustion during traffic spikes.
RENDER_SEMAPHORE = threading.BoundedSemaphore(3)

def _sanitize_stalled_jobs():
    """Industrial Sentinel: Clean up 'Processing' jobs that were abandoned by a crash/restart."""
    global jobs
    found_stalled = False
    with _jobs_lock:
        for job_id, details in jobs.items():
            if details.get("status") == "processing":
                print(f"♻️  Sanitizing stalled job {job_id} (found in 'processing' state on boot)")
                details["status"] = "failed"
                details["error"]  = "Server was restarted during production. Please re-trigger."
                found_stalled = True
    if found_stalled:
        _save_jobs()

def _load_jobs():
    if os.path.exists(JOBS_FILE):
        try:
            with open(JOBS_FILE, "r") as f:
                data = json.load(f)
            # Perform Disaster Recovery sanitization logic
            global jobs
            jobs = data
            _sanitize_stalled_jobs()
            return jobs
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}

def _save_jobs():
    """Disk persistence for jobs DB with Atomic Write protection."""
    with _jobs_lock:
        tmp_file = JOBS_FILE + ".tmp"
        try:
            with open(tmp_file, "w") as f:
                json.dump(jobs, f, indent=2)
            # Atomic swap ensures jobs.json is never corrupted by partial writes
            os.replace(tmp_file, JOBS_FILE)
        except Exception as e:
            print(f"❌ Error saving jobs state: {e}")
            if os.path.exists(tmp_file):
                os.remove(tmp_file)

# ── In-memory job store ───────────────────────────────────────────────────────
jobs = _load_jobs()


def _notify_webhook_with_retry(job_id: str, status: str, video_url: str = "", error: str = ""):
    """Industrial Sentinel: Robust notification with exponential backoff."""
    webhook_url = os.environ.get("WEBHOOK_URL")
    if not webhook_url:
        return

    payload = {
        "job_id":      job_id,
        "status":      status,
        "video_url":   video_url,
        "error":       error,
    }

    import time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.post(webhook_url, json=payload, timeout=15)
            if resp.status_code < 300:
                print(f"🔔 Webhook Success (Job {job_id}) on attempt {attempt + 1}")
                return
            else:
                print(f"⚠️  Webhook Status {resp.status_code} on attempt {attempt + 1}")
        except Exception as e:
            print(f"⚠️  Webhook Retry {attempt + 1} for job {job_id}: {e}")
        
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt) # Exponential backoff: 1, 2, 4s

    print(f"❌ Webhook FAILED (Job {job_id}) after {max_retries} attempts.")


# ── Pipeline runner ───────────────────────────────────────────────────────────

class RenderRequest(BaseModel):
    topic:       str
    html:        str
    render_mode: Optional[Literal["manim", "presentation", "explainer", "user_generated_video"]] = None
    with_avatar: bool = False
    video_type:  Optional[Literal["marketing", "educational"]] = None
    image_path:  Optional[str] = None


class JobStatus(BaseModel):
    job_id:      str
    status:      str        # queued | processing | completed | failed
    video_url:   str  = ""
    error:       str  = ""
    render_mode: str  = None   # echoed back so callers know which path ran
    with_avatar: bool = False
    video_type:  str  = None   # echoed back: "marketing" | "educational"


# ── Pipeline runner ───────────────────────────────────────────────────────────

def _run_pipeline(job_id: str, topic: str, html: str):
    """Run the full LangGraph pipeline with Concurrency Sentinel protection."""
    global RENDER_SEMAPHORE

    # Wait for a slot in the compute queue (Max 3 concurrent renders)
    with RENDER_SEMAPHORE:
        with _jobs_lock:
            jobs[job_id]["status"] = "processing"
            job = dict(jobs[job_id])   # snapshot to avoid lock re-entry

        # Industrial Path Sanity: Use absolute MEDIA_DIR from environment
        media_root = os.environ.get("MANIM_MEDIA_DIR", "output")
        job_dir = os.path.join(media_root, f"job_{job_id}")
        os.makedirs(job_dir, exist_ok=True)

        # If caller provided an image, copy it to the job folder as tony_diagram.png
        injected_image = job.get("image_path")
        if injected_image and os.path.exists(injected_image):
            import shutil
            dest = os.path.join(job_dir, "tony_diagram.png")
            shutil.copy2(injected_image, dest)
            print(f"📸 Using injected image in isolated dir: {dest}")

        try:
            from autonomous_graph import app as graph

            final_state = graph.invoke({
                "job_id":            job_id,
                "raw_input":         html,
                "topic":             topic,
                "attempt_count":     0,
                "parsed_facts":      None,
                "render_mode":       job.get("render_mode"),
                "with_avatar":       job.get("with_avatar", False),
                "video_type":        job.get("video_type"),
                "no_vision":         False,
                "scenes":            None,
                "image_path":        None,
                "image_paths":       None,
                "audio_files":       None,
                "manim_script_path": None,
                "output_path":       None,
                "video_url":         None,
                "rendering_errors":  None,
                "slides":             None,
                "slide_paths":        None,
                "clip_paths":         None,
                "critic_feedback":    None,
                "ppt_attempt_count":  0,
                "visual_prompts":     None,
                "heygen_video_path":  None,
                "subtitle_style":     None,
            })
        except BaseException as e:
            print(f"❌ Pipeline Error for job {job_id}: {e}")
            with _jobs_lock:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["error"]  = str(e)
                final_status = "failed"
                final_error = str(e)
            _save_jobs()
            
            _notify_webhook_with_retry(
                job_id=job_id,
                status=final_status,
                video_url="",
                error=final_error
            )
            return

        # ── Post-Render Phase (Network I/O) ──
        # Semaphore is held during state persistence to avoid race conditions.
        video_url = final_state.get("video_url") or ""
        error_msg = final_state.get("rendering_errors", "")

        with _jobs_lock:
            if video_url:
                jobs[job_id]["status"]    = "completed"
                jobs[job_id]["video_url"] = video_url
                jobs[job_id]["logs"].append({"node": "DEPLOY", "msg": "Video production finalized and uploaded.", "type": "success"})
                print(f"✅ Job {job_id} completed: {video_url}")
            else:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["error"]  = error_msg or "No output produced"
                jobs[job_id]["logs"].append({"node": "SYSTEM", "msg": f"Failure: {jobs[job_id]['error']}", "type": "warning"})
                print(f"❌ Job {job_id} failed: {jobs[job_id]['error']}")

            final_status = jobs[job_id]["status"]
            final_error  = jobs[job_id]["error"]

        _save_jobs()

    # Final Webhook Handover with 3-attempt exponential backoff
    _notify_webhook_with_retry(
        job_id=job_id,
        status=final_status,
        video_url=video_url,
        error=final_error
    )

    # RECURSIVE HYGIENE: Final check to ensure failed/successful job dirs are purged from EFS
    if os.environ.get("AUTO_DELETE_JOB_DIR", "false").lower() == "true":
        import shutil
        media_root = os.environ.get("MANIM_MEDIA_DIR", "output")
        job_dir = os.path.join(media_root, f"job_{job_id}")
        if os.path.exists(job_dir):
            try:
                shutil.rmtree(job_dir)
                print(f"🧹 [Auto-Cleanup] Absolute path purged: {job_dir}")
            except Exception as e:
                print(f"⚠️  Hygiene Alert for {job_id}: {e}")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/render", response_model=JobStatus, dependencies=[SecurityDep])
def start_render(request: RenderRequest):
    """
    Start a video generation job.
    Spring Boot calls this with the Tony AI lesson HTML.
    Returns job_id immediately — video is generated in background.
    """
    if not request.topic or not request.html:
        raise HTTPException(status_code=400, detail="topic and html are required")

    # Industrial Sentinel: UUID Collision Guard for Infinite Scale
    while True:
        job_id = str(uuid.uuid4())[:12]
        with _jobs_lock:
            if job_id not in jobs:
                break

    with _jobs_lock:
        jobs[job_id] = {
            "job_id":      job_id,
            "status":      "queued",
            "video_url":   "",
            "error":       "",
            "render_mode": request.render_mode,
            "with_avatar": request.with_avatar,
            "video_type":  request.video_type,
            "image_path":  request.image_path,
            "logs":        [{"node": "SYSTEM", "msg": f"Job initialized for topic: {request.topic}", "type": "info"}]
        }

    thread = threading.Thread(
        target=_run_pipeline,
        args=(job_id, request.topic, request.html),
        daemon=True,
    )
    thread.start()
    _save_jobs()

    print(f"🚀 Job {job_id} queued for: {request.topic}")
    with _jobs_lock:
        return dict(jobs[job_id])


@app.get("/jobs", dependencies=[SecurityDep])
def get_all_jobs():
    """Returns all jobs for the Factory Portal dashboard."""
    return jobs


@app.get("/status/{job_id}", response_model=JobStatus, dependencies=[SecurityDep])
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
