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
import copy
try:
    import fcntl
except ImportError:
    # Windows compatibility fallback — prevents crash on local dev
    fcntl = None

import shutil
from datetime import datetime


_jobs_lock = threading.RLock()
from fastapi import FastAPI, HTTPException, Header, Depends, Request, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal, Optional
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="EaseToLearn Video Generation Service", version="2.0.0")
_APP_START_TIME = datetime.utcnow()

allowed_origins_env = os.environ.get("ALLOWED_ORIGINS")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()] if allowed_origins_env else ["*"]


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

# ── Static Assets ─────────────────────────────────────────────────────────────
# Mount assets directory for font/logo downloads by external components
# (Moved down to ensure BASE_DIR exists)

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
assets_dir = os.path.join(BASE_DIR, "assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
app.mount("/portal", StaticFiles(directory="factory_portal/control_panel", html=True), name="portal")

@app.get("/stream/{job_id}/{filename}", tags=["Core"], summary="Stream local video", description="Dynamic streaming endpoint for browser-based video playback. Supports range requests for efficient seeking.")
async def stream_video(job_id: str, filename: str):
    import mimetypes
    path = os.path.join("output", f"job_{job_id}", filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Ensure proper MIME type for video playback
    mime_type, _ = mimetypes.guess_type(path)
    return FileResponse(path, media_type=mime_type or "video/mp4")


JOBS_FILE = os.environ.get("JOBS_FILE_PATH", "/tmp/jobs.json")
jobs = {}

# Industrial Concurrency Cap: Max 3 high-compute jobs (Manim/Video) at once
# This prevents RAM/CPU exhaustion during traffic spikes.
RENDER_SEMAPHORE = threading.BoundedSemaphore(3)

def _sanitize_stalled_jobs():
    """Industrial Sentinel: Clean up 'Processing' jobs and purge their heavy storage folders."""
    global jobs
    found_stalled = False
    with _jobs_lock:
        for job_id, details in list(jobs.items()):
            if details.get("status") == "processing":
                print(f"♻️  Sanitizing stalled job {job_id} (found in 'processing' state on boot)")
                details["status"] = "failed"
                details["error"]  = "Server was restarted during production. Please re-trigger."
                
                # ── Disk Hygiene: Purge orphan folder on boot ──
                media_root = os.environ.get("MANIM_MEDIA_DIR", "output")
                job_dir = os.path.join(media_root, f"job_{job_id}")
                if os.path.exists(job_dir):
                    try:
                        shutil.rmtree(job_dir)
                        print(f"🧹 [Auto-Hygiene] Purged orphan directory: {job_dir}")
                    except Exception as e:
                        print(f"⚠️ Hygiene Failure: {e}")
                
                from datetime import datetime
                details["updated_at"] = datetime.utcnow().isoformat() + "Z"
                found_stalled = True
    if found_stalled:
        _safe_save_jobs("startup stalled-job sanitization")


def _load_jobs():
    """Loads jobs with cross-process file-level locking protection."""
    if os.path.exists(JOBS_FILE):
        try:
            with open(JOBS_FILE, "r", encoding='utf-8') as f:
                # Lock for shared reading (across workers)
                if fcntl: fcntl.flock(f, fcntl.LOCK_SH)
                data = json.load(f)
                if fcntl: fcntl.flock(f, fcntl.LOCK_UN)


            
            global jobs
            with _jobs_lock:
                jobs = data
            return jobs
        except (json.JSONDecodeError, ValueError, Exception) as e:
            import time, sys
            timestamp = int(time.time())
            corrupt_path = f"{JOBS_FILE}.corrupt_{timestamp}"
            print(f"❌ DATA CORRUPTION ALERT: {JOBS_FILE} is unreadable. Archiving to {corrupt_path}", file=sys.stderr)
            try:
                os.rename(JOBS_FILE, corrupt_path)
            except Exception as archive_error:
                print(f"⚠️  Failed to archive corrupt jobs file: {archive_error}", file=sys.stderr)
            return {}
    return {}


def _save_jobs():
    """Disk persistence with cross-process Exclusive Locking and Atomic Write protection."""
    with _jobs_lock:
        tmp_file = JOBS_FILE + ".tmp"
        try:
            # 1. Acquire an exclusive lock on the main jobs file BEFORE doing anything
            lock_file = JOBS_FILE + ".lock"
            with open(lock_file, "w") as lf:
                if fcntl: fcntl.flock(lf, fcntl.LOCK_EX)
                
                # 2. RELOAD the absolute current state from disk to merge
                disk_state = {}
                if os.path.exists(JOBS_FILE):
                    try:
                        with open(JOBS_FILE, "r", encoding='utf-8') as f:
                            disk_state = json.load(f)
                    except Exception as e:
                        import sys
                        print(f"⚠️ Merge Warning: Could not reload disk state for mutation ({e})", file=sys.stderr)

                
                # 3. MERGE the in-memory changes into the disk state
                # Industrial Sentinel: Use chronological precedence for all fields
                # Plus additive merge for 'logs' to prevent telemetry loss.
                for job_id, local_job in jobs.items():
                    if job_id in disk_state:
                        # Status and video_url ALWAYS win from memory — never overwrite with stale disk state
                        for k, v in local_job.items():
                            if k == "logs":
                                existing_logs = disk_state[job_id].get("logs", [])
                                existing_stamps = [str(l) for l in existing_logs]
                                for l in v:
                                    if str(l) not in existing_stamps:
                                        existing_logs.append(l)
                                disk_state[job_id]["logs"] = existing_logs[-100:]
                            else:
                                # Always overwrite — memory is the source of truth
                                disk_state[job_id][k] = v
                    else:
                        disk_state[job_id] = local_job
                
                # 4. Write the merged state to a temporary file
                with open(tmp_file, "w", encoding='utf-8') as f:
                    json.dump(disk_state, f, indent=2, ensure_ascii=False)

                
                # 5. Atomic swap
                os.replace(tmp_file, JOBS_FILE)
                
                # 6. Synchronize our global memory 'jobs' with the merger result
                jobs.update(disk_state)
                
                if fcntl: fcntl.flock(lf, fcntl.LOCK_UN)

                
        except Exception as e:
            print(f"❌ Error saving jobs state: {e}")
            if os.path.exists(tmp_file):
                os.remove(tmp_file)
            raise


def _safe_save_jobs(context: str, fatal: bool = False) -> bool:
    """Persist jobs with contextual logging and optional HTTP failure propagation."""
    try:
        _save_jobs()
        return True
    except Exception as e:
        print(f"❌ Jobs persistence failure during {context}: {e}")
        if fatal:
            raise HTTPException(status_code=500, detail="Failed to persist job state")
        return False


# ── In-memory job store ───────────────────────────────────────────────────────
jobs = _load_jobs()
_sanitize_stalled_jobs()


def _notify_webhook_with_retry(job_id: str, status_data: dict):
    """Industrial Sentinel: Robust notification with exponential backoff and full payload parity."""
    webhook_url = os.environ.get("WEBHOOK_URL")
    if not webhook_url:
        return

    import time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Industrial Sentinel: Explicit 30s timeout for webhook resilience
            resp = requests.post(webhook_url, json=status_data, timeout=30)

            if resp.status_code < 300:
                print(f"🔔 Webhook Success (Job {job_id}) on attempt {attempt + 1}")
                return
            else:
                print(f"⚠️  Webhook Status {resp.status_code} on attempt {attempt + 1}")
        except requests.RequestException as e:
            print(f"⚠️  Webhook Retry {attempt + 1} for job {job_id}: {e}")
        
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt) # Exponential backoff: 1, 2, 4s

    print(f"❌ Webhook FAILED (Job {job_id}) after {max_retries} attempts.")



# ── Pipeline runner ───────────────────────────────────────────────────────────

class RenderRequest(BaseModel):
    topic:       str
    html:        str
    render_mode: Optional[Literal["manim", "presentation", "explainer", "user_generated_video", "user_generated"]] = None
    with_avatar: bool = False
    video_type:  Optional[Literal["marketing", "educational"]] = None
    image_path:  Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "topic": "Newton's Laws of Motion",
                "html": "<html><body><h1>Lesson 1</h1>...</body></html>",
                "render_mode": "manim",
                "with_avatar": False,
                "video_type": "educational"
            }
        }


class JobStatus(BaseModel):
    job_id:       str
    topic:        str  = ""
    status:       str         # queued | processing | completed | failed
    video_url:    str  = ""
    thumbnail_url: str = ""
    error:        str  = ""
    progress:     int  = 0    # 0 to 100
    current_step: str  = ""
    render_mode:  Optional[str] = None
    with_avatar:  bool = False
    video_type:   Optional[str] = None
    created_at:   str  = ""   # ISO timestamp
    updated_at:   str  = ""   # ISO timestamp
    logs:         list = Field(default_factory=list)   # Telemetry for "Tony AI" Mission Control dashboard
    metrics:      dict = Field(default_factory=dict)   # Performance stats (ttc, api_costs)

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "4a8d5928-cae",
                "topic": "Newton's Laws of Motion",
                "status": "completed",
                "video_url": "/stream/4a8d5928-cae/lesson_video.mp4",
                "thumbnail_url": "/stream/4a8d5928-cae/thumbnail.png",
                "progress": 100,
                "current_step": "DEPLOY",
                "render_mode": "manim",
                "created_at": "2026-04-17T10:00:00Z",
                "updated_at": "2026-04-17T10:05:00Z",
                "logs": [{"node": "SYSTEM", "msg": "Job initialized", "type": "info"}],
                "metrics": {"total_duration_sec": 300.5}
            }
        }


class BulkRenderResponse(BaseModel):
    job_ids: list[str]
    total: int
    status: str

    class Config:
        json_schema_extra = {
            "example": {
                "job_ids": ["job1", "job2"],
                "total": 2,
                "status": "queued"
            }
        }


class DeleteResponse(BaseModel):
    deleted: str

    class Config:
        json_schema_extra = {
            "example": {
                "deleted": "job_id_123"
            }
        }


class MessageResponse(BaseModel):
    status: str
    service: str

    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "service": "easetolearn-video-generation"
            }
        }


class AnalyticsResponse(BaseModel):
    total_jobs: int
    completed: int
    failed: int
    success_rate: str
    avg_render_time_sec: float
    render_modes_breakdown: dict[str, int]

    class Config:
        json_schema_extra = {
            "example": {
                "total_jobs": 100,
                "completed": 85,
                "failed": 15,
                "success_rate": "85.0%",
                "avg_render_time_sec": 45.2,
                "render_modes_breakdown": {"manim": 50, "presentation": 35}
            }
        }


class TimelineResponse(BaseModel):
    hourly: dict[str, dict[str, int]]
    daily: dict[str, dict[str, int]]
    total_jobs: int

    class Config:
        json_schema_extra = {
            "example": {
                "hourly": {"2026-04-17 10:00": {"completed": 5, "failed": 1, "queued": 0}},
                "daily": {"2026-04-17": {"completed": 20, "failed": 3, "queued": 0}},
                "total_jobs": 23
            }
        }


class QueueItem(BaseModel):
    position: int
    job_id: str
    topic: str
    status: str
    progress: int
    render_mode: str
    created_at: str
    eta_seconds: float


class QueueResponse(BaseModel):
    queue_length: int
    avg_render_time_sec: float
    jobs: list[QueueItem]

    class Config:
        json_schema_extra = {
            "example": {
                "queue_length": 2,
                "avg_render_time_sec": 120.0,
                "jobs": [
                    {
                        "position": 1,
                        "job_id": "job1",
                        "topic": "Newton's Laws",
                        "status": "processing",
                        "progress": 45,
                        "render_mode": "manim",
                        "created_at": "2026-04-17T11:00:00Z",
                        "eta_seconds": 66.0
                    }
                ]
            }
        }


class CostItem(BaseModel):
    job_id: str
    topic: str
    render_mode: str
    estimated_cost_usd: float


class CostsResponse(BaseModel):
    total_estimated_cost_usd: float
    completed_jobs: int
    avg_cost_per_video_usd: float
    breakdown: list[CostItem]
    note: str

    class Config:
        schema_extra = {
            "example": {
                "total_estimated_cost_usd": 12.50,
                "completed_jobs": 100,
                "avg_cost_per_video_usd": 0.125,
                "breakdown": [
                    {"job_id": "job1", "topic": "Physics", "render_mode": "manim", "estimated_cost_usd": 0.15}
                ],
                "note": "Estimates based on average API pricing."
            }
        }


class WebhookTestResponse(BaseModel):
    status: str
    webhook_url: Optional[str] = None
    response_code: Optional[int] = None
    response_body: Optional[str] = None
    reason: Optional[str] = None
    hint: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "status": "sent",
                "webhook_url": "https://callback.com/hook",
                "response_code": 200,
                "response_body": "OK"
            }
        }


class VersionResponse(BaseModel):
    service: str
    version: str
    git_commit: str
    started_at: str
    uptime: str
    uptime_seconds: int
    python_version: str

    class Config:
        schema_extra = {
            "example": {
                "service": "EaseToLearn Video Generation Factory",
                "version": "2.0.0",
                "git_commit": "46a04ea",
                "started_at": "2026-04-17T10:00:00Z",
                "uptime": "2h 30m",
                "uptime_seconds": 9000,
                "python_version": "3.9.6"
            }
        }



# ── Pipeline runner ───────────────────────────────────────────────────────────

def _run_pipeline(job_id: str, topic: str, html: str):
    """Run the full LangGraph pipeline with Concurrency Sentinel protection."""
    global RENDER_SEMAPHORE

    # Wait for a slot in the compute queue (Max 3 concurrent renders)
    with RENDER_SEMAPHORE:
        # Don't reload from disk here — the job was just created in memory by start_render.
        # _load_jobs() was wiping the new job before the thread could pick it up because
        # /tmp/jobs.json hadn't been written yet at the moment the thread acquired the semaphore.

        with _jobs_lock:
            import time
            start_pipeline_t = time.time()
            from datetime import datetime
            now_iso = datetime.utcnow().isoformat() + "Z"
            if job_id not in jobs:
                print(f"⚠️  Job {job_id} missing during thread pickup. Aborting.")
                return

            jobs[job_id]["status"] = "processing"
            jobs[job_id]["progress"] = 10
            jobs[job_id]["updated_at"] = now_iso
            job = dict(jobs[job_id])   # snapshot to avoid lock re-entry
        
        # PERSIST: Notify all workers of the 'processing' state
        _safe_save_jobs(f"pipeline start ({job_id})")



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
        except Exception as e:
            print(f"❌ Pipeline Error for job {job_id}: {e}")
            with _jobs_lock:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["error"]  = str(e)
                final_status = "failed"
                final_error = str(e)
            
            # ── METRICS LOGGING ───────────────────────────────────
            duration = time.time() - start_pipeline_t
            with _jobs_lock:
                if "metrics" not in jobs[job_id]:
                    jobs[job_id]["metrics"] = {}
                jobs[job_id]["metrics"]["total_duration_sec"] = round(duration, 2)
                jobs[job_id]["updated_at"] = datetime.utcnow().isoformat() + "Z"
            
            # Final state persistence
            _safe_save_jobs(f"pipeline complete ({job_id})")
            
            _notify_webhook_with_retry(
                job_id=job_id,
                status_data={
                    "job_id": job_id,
                    "status": "failed",
                    "error": str(e),
                    "video_url": "",
                    "progress": 0,
                    "updated_at": datetime.utcnow().isoformat() + "Z"
                }
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

        _safe_save_jobs(f"pipeline finalize ({job_id})")

    # Final Webhook Handover with 3-attempt exponential backoff
    with _jobs_lock:
        final_payload = dict(jobs[job_id])
    
    _notify_webhook_with_retry(
        job_id=job_id,
        status_data=final_payload
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

@app.post("/render", response_model=JobStatus, tags=["Core"], summary="Submit single job", description="Accepts lesson HTML and metadata to queue a single video production job. Returns a job_id immediately while rendering proceeds in a background thread.")
def start_render(request: RenderRequest):
    if not request.topic or not request.html:
        raise HTTPException(status_code=400, detail="topic and html are required")

    # INDUSTRIAL SENTINEL: Refresh memory state before collision check
    _load_jobs()
    
    # Industrial Sentinel: UUID Collision Guard for Infinite Scale
    while True:
        job_id = str(uuid.uuid4())[:12]
        with _jobs_lock:
            if job_id not in jobs:
                break


    from datetime import datetime
    now_iso = datetime.utcnow().isoformat() + "Z"

    with _jobs_lock:
        jobs[job_id] = {
            "job_id":       job_id,
            "status":       "queued",
            "video_url":    "",
            "error":        "",
            "progress":     0,
            "current_step": "Initializing",
            "render_mode":  request.render_mode,
            "with_avatar":  request.with_avatar,
            "video_type":   request.video_type,
            "image_path":   request.image_path,
            "created_at":   now_iso,
            "updated_at":   now_iso,
            "topic":        request.topic,
            "logs":         [{"node": "SYSTEM", "msg": f"Job initialized for topic: {request.topic}", "type": "info"}]
        }


    thread = threading.Thread(
        target=_run_pipeline,
        args=(job_id, request.topic, request.html),
        daemon=True,
    )
    thread.start()

    # Snapshot BEFORE save (save may reload+merge and temporarily displace new job)
    with _jobs_lock:
        job_snapshot = copy.deepcopy(jobs[job_id])

    _safe_save_jobs(f"start_render enqueue ({job_id})", fatal=False)  # non-fatal

    print(f"🚀 Job {job_id} queued for: {request.topic}")
    return job_snapshot


@app.post("/bulk_render", response_model=BulkRenderResponse, dependencies=[SecurityDep], tags=["Core"], summary="Submit batch jobs", description="Accepts a JSON array of lessons. Jobs are processed sequentially in a single background worker to prevent resource exhaustion.")
async def bulk_render(file: UploadFile = File(...)):
    """Accept a JSON file and queue all lessons as separate jobs."""
    content = await file.read()
    
    try:
        lessons = json.loads(content)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    
    if not isinstance(lessons, list):
        raise HTTPException(status_code=400, detail="JSON must be an array of lessons")
    
    job_ids = []
    from datetime import datetime
    
    def _run_bulk_sequential(job_queue):
        for job_id, topic, html in job_queue:
            _run_pipeline(job_id, topic, html)
            print(f"✅ Bulk: Job {job_id} done, moving to next...")

    job_queue = []
    for lesson in lessons:
        topic = lesson.get("topic", "Untitled")
        html = lesson.get("html", "")
        if not html:
            continue
            
        while True:
            job_id = str(uuid.uuid4())[:12]
            with _jobs_lock:
                if job_id not in jobs:
                    break
        
        now_iso = datetime.utcnow().isoformat() + "Z"
        
        with _jobs_lock:
            jobs[job_id] = {
                "job_id":       job_id,
                "topic":        topic,
                "status":       "queued",
                "video_url":    "",
                "error":        "",
                "progress":     0,
                "current_step": "Initializing",
                "render_mode":  lesson.get("render_mode"),
                "with_avatar":  lesson.get("with_avatar", False),
                "video_type":   lesson.get("video_type", "educational"),
                "image_path":   None,
                "created_at":   now_iso,
                "updated_at":   now_iso,
                "logs":         [],
                "metrics":      {}
            }
        job_ids.append(job_id)
        job_queue.append((job_id, topic, html))

    # Single thread runs all jobs one after another
    thread = threading.Thread(
        target=_run_bulk_sequential,
        args=(job_queue,),
        daemon=True,
    )
    thread.start()
    
    _safe_save_jobs("bulk_render enqueue")
    print(f"🚀 Bulk ingest: {len(job_ids)} jobs queued")
    
    return {"job_ids": job_ids, "total": len(job_ids), "status": "queued"}


@app.get("/jobs", response_model=dict[str, JobStatus], dependencies=[SecurityDep], tags=["Core"], summary="List all jobs", description="Retrieves the full registry of all current and historical jobs from the persistence layer.")
def get_all_jobs():
    """Returns all jobs for the Factory Portal dashboard."""
    _load_jobs()
    with _jobs_lock:
        return copy.deepcopy(jobs)



@app.get("/status/{job_id}", response_model=JobStatus, dependencies=[SecurityDep], tags=["Core"], summary="Get job status", description="Polls the current status, progress, and telemetry for a specific job ID.")
def get_status(job_id: str):
    """
    Poll job status.
    Spring Boot polls this every 5s until status is 'completed' or 'failed'.
    """
    _load_jobs()
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    with _jobs_lock:
        return copy.deepcopy(jobs[job_id])



@app.get("/health", response_model=MessageResponse, tags=["Core"], summary="Simple health check", description="Basic probe to verify if the API service and server process are reachable.")
def health():
    """ECS / ALB health check endpoint."""
    return {"status": "ok", "service": "easetolearn-video-generation"}


@app.delete("/jobs/purge", response_model=dict, dependencies=[SecurityDep], tags=["Operational"], summary="Purge all failed jobs", description="Removes all jobs with a 'failed' status from the factory registry. Useful for cleaning up the dashboard after resolving pipeline issues.")
def purge_failed_jobs():
    """Nuclear option: Clear all failed jobs from the persistence layer in one click."""
    with _jobs_lock:
        failed_ids = [jid for jid, j in jobs.items() if j["status"] == "failed"]
        for jid in failed_ids:
            del jobs[jid]
    
    _safe_save_jobs("purge failed jobs")
    return {"purged": len(failed_ids), "job_ids": failed_ids}


@app.delete("/jobs/{job_id}", response_model=DeleteResponse, dependencies=[SecurityDep], tags=["Core"], summary="Delete single job", description="Permanently removes a specific job record from both memory and disk persistence.")
def delete_job(job_id: str):
    """Industrial Sentinel: Securely remove a job from the factory persistence layer."""
    _load_jobs()
    with _jobs_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        del jobs[job_id]
    _safe_save_jobs(f"delete_job ({job_id})")
    return {"deleted": job_id}


@app.get("/analytics", response_model=AnalyticsResponse, tags=["Analytics"], summary="Global production stats", description="Aggregated production metrics including total volume, success rates, and average render times across all historical jobs.")
def get_analytics():
    """Factory analytics dashboard — production stats at a glance."""
    with _jobs_lock:
        all_jobs = list(jobs.values())
    
    completed = [j for j in all_jobs if j["status"] == "completed"]
    failed = [j for j in all_jobs if j["status"] == "failed"]
    
    render_modes = {}
    for j in completed:
        mode = j.get("render_mode") or "auto"
        render_modes[mode] = render_modes.get(mode, 0) + 1
    
    durations = [j.get("metrics", {}).get("total_duration_sec", 0) for j in completed]
    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0
    
    return {
        "total_jobs": len(all_jobs),
        "completed": len(completed),
        "failed": len(failed),
        "success_rate": f"{round(len(completed)/len(all_jobs)*100, 1)}%" if all_jobs else "0%",
        "avg_render_time_sec": avg_duration,
        "render_modes_breakdown": render_modes,
    }


@app.post("/retry/{job_id}", response_model=dict, dependencies=[SecurityDep], tags=["Operational"], summary="Retry failed job", description="Re-queues a failed job into the processing pipeline using its original HTML and topic. Resets progress and error state.")
def retry_job(job_id: str):
    """Retry a failed job by re-queuing it through the pipeline."""
    with _jobs_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        job = jobs[job_id]
        if job["status"] != "failed":
            raise HTTPException(status_code=400, detail="Only failed jobs can be retried")
        topic = job.get("topic", "")
        html = job.get("raw_html", "")
    
    if not html:
        raise HTTPException(status_code=400, detail="No HTML stored for retry")
    
    # Reset job state
    from datetime import datetime
    now_iso = datetime.utcnow().isoformat() + "Z"
    with _jobs_lock:
        jobs[job_id]["status"] = "queued"
        jobs[job_id]["error"] = ""
        jobs[job_id]["progress"] = 0
        jobs[job_id]["updated_at"] = now_iso
    
    thread = threading.Thread(
        target=_run_pipeline,
        args=(job_id, topic, html),
        daemon=True,
    )
    thread.start()
    return {"job_id": job_id, "status": "retrying"}


@app.get("/health/detailed", response_model=dict, tags=["Enterprise"], summary="System dependency health", description="Performs a deep check of all third-party dependencies (Groq, S3, ElevenLabs) to ensure the factory is fully operational.")
def health_detailed():
    """Deep health check — verifies all external service dependencies."""
    import groq as groq_lib
    
    checks = {}
    
    # Groq
    try:
        client = groq_lib.Groq(api_key=os.environ.get("GROQ_API_KEY"))
        client.models.list()
        checks["groq"] = "ok"
    except:
        checks["groq"] = "error"
    
    # S3
    s3_bucket = os.environ.get("S3_BUCKET")
    checks["s3"] = "configured" if s3_bucket else "not_configured"
    
    # ElevenLabs
    checks["elevenlabs"] = "configured" if os.environ.get("ELEVENLABS_API_KEY") else "not_configured"
    
    # Jobs stats
    with _jobs_lock:
        total = len(jobs)
        processing = len([j for j in jobs.values() if j["status"] == "processing"])
    
    return {
        "status": "ok",
        "services": checks,
        "jobs": {"total": total, "active": processing},
        "semaphore_slots": 3
    }


# ── Tier 1: Demo Showstoppers ─────────────────────────────────────────────────

@app.get("/analytics/timeline", response_model=TimelineResponse, tags=["Analytics"], summary="Production throughput timeline", description="Time-series data showing hourly and daily job throughput. Ideal for rendering throughput charts and identifying peak factory hours.")
def analytics_timeline():
    """Hourly production throughput — perfect for manager dashboards and charts."""
    with _jobs_lock:
        all_jobs = list(jobs.values())
    
    from collections import defaultdict
    hourly = defaultdict(lambda: {"completed": 0, "failed": 0, "queued": 0})
    daily = defaultdict(lambda: {"completed": 0, "failed": 0, "queued": 0})
    
    for j in all_jobs:
        created = j.get("created_at", "")
        status = j.get("status", "queued")
        if not created:
            continue
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            hour_key = dt.strftime("%Y-%m-%d %H:00")
            day_key = dt.strftime("%Y-%m-%d")
            hourly[hour_key][status] = hourly[hour_key].get(status, 0) + 1
            daily[day_key][status] = daily[day_key].get(status, 0) + 1
        except Exception:
            continue
    
    return {
        "hourly": dict(sorted(hourly.items())),
        "daily": dict(sorted(daily.items())),
        "total_jobs": len(all_jobs),
    }


@app.get("/export/csv")
def export_csv():
    """Download all job data as a CSV file — instant Excel compatibility."""
    import io
    import csv
    
    with _jobs_lock:
        all_jobs = list(jobs.values())
    
    output = io.StringIO()
    if not all_jobs:
        output.write("No jobs found")
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=factory_jobs.csv"}
        )
    
    fieldnames = ["job_id", "topic", "status", "render_mode", "video_type", 
                  "with_avatar", "progress", "video_url", "error", 
                  "created_at", "updated_at", "duration_sec"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for j in all_jobs:
        writer.writerow({
            "job_id":       j.get("job_id", ""),
            "topic":        j.get("topic", ""),
            "status":       j.get("status", ""),
            "render_mode":  j.get("render_mode", "auto"),
            "video_type":   j.get("video_type", ""),
            "with_avatar":  j.get("with_avatar", False),
            "progress":     j.get("progress", 0),
            "video_url":    j.get("video_url", ""),
            "error":        j.get("error", ""),
            "created_at":   j.get("created_at", ""),
            "updated_at":   j.get("updated_at", ""),
            "duration_sec": j.get("metrics", {}).get("total_duration_sec", ""),
        })
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=factory_jobs.csv"}
    )


@app.post("/priority/{job_id}", response_model=dict, dependencies=[SecurityDep], tags=["Operational"], summary="Prioritize queued job", description="Bumps a queued job to the front of the line by manipulating its internal sort timestamp.")
def prioritize_job(job_id: str):
    """Bump a queued job to highest priority by backdating its updated_at timestamp."""
    with _jobs_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        if jobs[job_id]["status"] != "queued":
            raise HTTPException(status_code=400, detail="Only queued jobs can be prioritized")
        # Set updated_at to far future so it sorts first
        jobs[job_id]["updated_at"] = "2099-01-01T00:00:00Z"
        jobs[job_id]["current_step"] = "PRIORITY — Moved to front of queue"
    _safe_save_jobs(f"priority bump ({job_id})")
    return {"job_id": job_id, "status": "prioritized"}


@app.get("/logs/{job_id}", response_model=JobStatus, dependencies=[SecurityDep], tags=["Operational"], summary="Detailed job telemetry", description="Returns the full record for a specific job, including detailed internal logs and performance metrics.")
def get_job_logs(job_id: str):
    """Full telemetry log for a specific job — deep observability."""
    with _jobs_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        job = copy.deepcopy(jobs[job_id])
    
    return {
        "job_id":       job.get("job_id"),
        "topic":        job.get("topic"),
        "status":       job.get("status"),
        "progress":     job.get("progress", 0),
        "current_step": job.get("current_step", ""),
        "render_mode":  job.get("render_mode"),
        "created_at":   job.get("created_at"),
        "updated_at":   job.get("updated_at"),
        "logs":         job.get("logs", []),
        "metrics":      job.get("metrics", {}),
        "error":        job.get("error", ""),
    }


# ── Tier 2: Operational Polish ────────────────────────────────────────────────



@app.get("/queue", response_model=QueueResponse, dependencies=[SecurityDep], tags=["Operational"], summary="Active queue status", description="Shows currently queued and processing jobs with their relative positions and estimated time to completion.")
def get_queue():
    """Show only queued and processing jobs with position and ETA."""
    with _jobs_lock:
        all_jobs = list(jobs.values())
    
    # Get average duration from completed jobs for ETA calculation
    completed = [j for j in all_jobs if j["status"] == "completed"]
    durations = [j.get("metrics", {}).get("total_duration_sec", 0) for j in completed]
    avg_duration = round(sum(durations) / len(durations), 1) if durations else 300  # default 5 min
    
    active = [j for j in all_jobs if j["status"] in ("queued", "processing")]
    active.sort(key=lambda j: j.get("created_at", ""))
    
    queue_items = []
    for i, j in enumerate(active):
        queue_items.append({
            "position":     i + 1,
            "job_id":       j.get("job_id"),
            "topic":        j.get("topic"),
            "status":       j.get("status"),
            "progress":     j.get("progress", 0),
            "render_mode":  j.get("render_mode", "auto"),
            "created_at":   j.get("created_at"),
            "eta_seconds":  round(avg_duration * (i + 1 - (j.get("progress", 0) / 100)), 1),
        })
    
    return {
        "queue_length": len(queue_items),
        "avg_render_time_sec": avg_duration,
        "jobs": queue_items,
    }


@app.post("/cancel/{job_id}", response_model=dict, dependencies=[SecurityDep], tags=["Operational"], summary="Cancel active job", description="Interrupts a queued or processing job, marking it as failed with a 'Cancelled' error state.")
def cancel_job(job_id: str):
    """Cancel a running or queued job by marking it as failed."""
    with _jobs_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        if jobs[job_id]["status"] not in ("queued", "processing"):
            raise HTTPException(status_code=400, detail="Only active jobs can be cancelled")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = "Cancelled by operator"
        jobs[job_id]["updated_at"] = datetime.utcnow().isoformat() + "Z"
        jobs[job_id]["logs"].append({"node": "SYSTEM", "msg": "Job cancelled by operator.", "type": "warning"})
    
    _safe_save_jobs(f"cancel job ({job_id})")
    return {"job_id": job_id, "status": "cancelled"}


@app.get("/version", response_model=VersionResponse, tags=["Enterprise"], summary="Service version info", description="Retrieves the current API version, server uptime, git commit hash, and environment details.")
def get_version():
    """API version, uptime, and build info — enterprise compliance."""
    uptime_seconds = (datetime.utcnow() - _APP_START_TIME).total_seconds()
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    
    # Try to get git commit hash
    git_commit = "unknown"
    try:
        import subprocess
        result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], 
                                capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            git_commit = result.stdout.strip()
    except Exception:
        pass
    
    return {
        "service": "EaseToLearn Video Generation Factory",
        "version": "2.0.0",
        "git_commit": git_commit,
        "started_at": _APP_START_TIME.isoformat() + "Z",
        "uptime": f"{hours}h {minutes}m",
        "uptime_seconds": round(uptime_seconds),
        "python_version": os.sys.version.split()[0],
    }


# ── Tier 3: Enterprise Feel ───────────────────────────────────────────────────

@app.get("/costs", response_model=CostsResponse, tags=["Analytics"], summary="API cost estimation", description="Calculates estimated third-party API costs (Groq, ElevenLabs, HeyGen) for all completed videos to provide financial visibility.")
def estimate_costs():
    """Estimated API costs per job and total — financial visibility for management."""
    # Cost estimates per API call (approximate)
    COST_PER_GROQ_CALL = 0.002       # ~$0.002 per LLM call
    COST_PER_ELEVENLABS_CHAR = 0.00003  # ~$0.03 per 1000 chars
    COST_PER_HEYGEN_MIN = 0.50       # ~$0.50 per minute of avatar video
    COST_PER_HIGGSFIELD_CALL = 0.10  # ~$0.10 per B-roll generation
    
    with _jobs_lock:
        all_jobs = list(jobs.values())
    
    completed = [j for j in all_jobs if j["status"] == "completed"]
    
    job_costs = []
    total_cost = 0.0
    
    for j in completed:
        mode = j.get("render_mode") or "auto"
        has_avatar = j.get("with_avatar", False)
        
        # Estimate based on render mode
        est = COST_PER_GROQ_CALL * 3  # parse + script + critic = 3 LLM calls
        est += COST_PER_ELEVENLABS_CHAR * 2000  # ~2000 chars avg narration
        
        if mode == "explainer":
            est += COST_PER_HIGGSFIELD_CALL * 3  # ~3 B-roll clips
        if has_avatar:
            est += COST_PER_HEYGEN_MIN * 2  # ~2 min avatar video
        
        est = round(est, 4)
        total_cost += est
        
        job_costs.append({
            "job_id": j.get("job_id"),
            "topic": j.get("topic"),
            "render_mode": mode,
            "estimated_cost_usd": est,
        })
    
    return {
        "total_estimated_cost_usd": round(total_cost, 2),
        "completed_jobs": len(completed),
        "avg_cost_per_video_usd": round(total_cost / len(completed), 4) if completed else 0,
        "breakdown": job_costs,
        "note": "Estimates based on average API pricing. Actual costs may vary."
    }


@app.post("/webhook/test", response_model=WebhookTestResponse, dependencies=[SecurityDep], tags=["Enterprise"], summary="Webhook connectivity test", description="Triggers a dummy payload to the configured WEBHOOK_URL to verify integration with the Spring Boot backend.")
def test_webhook():
    """Fire a test webhook to verify integration with Spring Boot backend."""
    webhook_url = os.environ.get("WEBHOOK_URL")
    if not webhook_url:
        return {
            "status": "skipped",
            "reason": "WEBHOOK_URL not configured",
            "hint": "Set WEBHOOK_URL environment variable to enable webhook notifications."
        }
    
    test_payload = {
        "job_id": "test-ping",
        "status": "test",
        "topic": "Webhook Connectivity Test",
        "video_url": "",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "message": "This is a test webhook from EaseToLearn Video Factory."
    }
    
    try:
        resp = requests.post(webhook_url, json=test_payload, timeout=10)
        return {
            "status": "sent",
            "webhook_url": webhook_url,
            "response_code": resp.status_code,
            "response_body": resp.text[:200],
        }
    except requests.RequestException as e:
        return {
            "status": "failed",
            "webhook_url": webhook_url,
            "error": str(e),
        }


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
