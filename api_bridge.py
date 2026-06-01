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
from pathlib import Path
import json
import copy
import time
import markdown
import config
from datetime import datetime
from typing import List, Dict, Any
try:
    import fcntl
except ImportError:
    # Windows compatibility fallback — prevents crash on local dev
    if os.environ.get("ENV", "dev").lower().strip() in ("production", "staging"):
        raise
    fcntl = None


import shutil
from dub_pipeline import run_dub_pipeline
from datetime import datetime
from caching.redis_client import get_cache, generate_idempotency_key


_jobs_lock = threading.RLock()
from fastapi import FastAPI, HTTPException, Header, Depends, Request, UploadFile, File, Body
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal, Optional
from dotenv import load_dotenv

load_dotenv()

def utcnow() -> datetime:
    from datetime import timezone
    return datetime.now(timezone.utc).replace(tzinfo=None)

app = FastAPI(title="EaseToLearn Video Generation Service", version="2.0.0")
_APP_START_TIME = utcnow()

# ── Database Initialization ──────────────────────────────────────────────────
try:
    from db.engine import init_db
    success = init_db()
    if not success and config.ENV in ("production", "staging"):
        raise RuntimeError("Database table verification/creation returned False.")
except Exception as e:
    print(f"⚠️  Critical: Database initialization failed: {e}")
    if config.ENV in ("production", "staging"):
        import sys
        sys.exit(1)


allowed_origins_env = os.environ.get("ALLOWED_ORIGINS")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()] if allowed_origins_env else ["*"]


if not allowed_origins_env and not os.environ.get("FACTORY_API_KEY"):
    print("⚠️  SECURITY WARNING: ALLOWED_ORIGINS and FACTORY_API_KEY both unset. API is completely open!")

# CORS — strictly restrict origins via env var (REQUIRED in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["X-API-Key", "Content-Type", "Authorization", "Idempotency-Key"],
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


def to_clean_python(val):
    if hasattr(val, 'to_dict'):
        return val.to_dict()
    if hasattr(val, 'to_list'):
        return val.to_list()
    if isinstance(val, dict):
        return {k: to_clean_python(v) for k, v in val.items()}
    if isinstance(val, list):
        return [to_clean_python(v) for v in val]
    return val

def wrap_value(val, on_mutation):
    if isinstance(val, dict) and not isinstance(val, ObservedDict):
        return ObservedDict(val, on_mutation)
    elif isinstance(val, list) and not isinstance(val, ObservedList):
        return ObservedList(val, on_mutation)
    return val

class ObservedDict(dict):
    def __init__(self, initial_dict, on_mutation):
        self._on_mutation = on_mutation
        wrapped = {k: wrap_value(v, on_mutation) for k, v in initial_dict.items()}
        super().__init__(wrapped)

    def __setitem__(self, key, value):
        super().__setitem__(key, wrap_value(value, self._on_mutation))
        self._on_mutation()

    def __delitem__(self, key):
        super().__delitem__(key)
        self._on_mutation()

    def update(self, *args, **kwargs):
        temp = dict(*args, **kwargs)
        wrapped = {k: wrap_value(v, self._on_mutation) for k, v in temp.items()}
        super().update(wrapped)
        self._on_mutation()

    def setdefault(self, key, default=None):
        if key in self:
            return self[key]
        wrapped = wrap_value(default, self._on_mutation)
        super().__setitem__(key, wrapped)
        self._on_mutation()
        return wrapped

    def pop(self, key, *args):
        res = super().pop(key, *args)
        self._on_mutation()
        return res

    def popitem(self):
        res = super().popitem()
        self._on_mutation()
        return res

    def clear(self):
        super().clear()
        self._on_mutation()

    def to_dict(self):
        return {k: to_clean_python(v) for k, v in self.items()}

    def __deepcopy__(self, memo):
        return copy.deepcopy(to_clean_python(self), memo)

class ObservedList(list):
    def __init__(self, initial_list, on_mutation):
        self._on_mutation = on_mutation
        wrapped = [wrap_value(v, on_mutation) for v in initial_list]
        super().__init__(wrapped)

    def append(self, item):
        super().append(wrap_value(item, self._on_mutation))
        self._on_mutation()

    def extend(self, iterable):
        wrapped = [wrap_value(v, self._on_mutation) for v in iterable]
        super().extend(wrapped)
        self._on_mutation()

    def insert(self, index, item):
        super().insert(index, wrap_value(item, self._on_mutation))
        self._on_mutation()

    def pop(self, *args):
        res = super().pop(*args)
        self._on_mutation()
        return res

    def remove(self, value):
        super().remove(value)
        self._on_mutation()

    def clear(self):
        super().clear()
        self._on_mutation()

    def __setitem__(self, index, value):
        super().__setitem__(index, wrap_value(value, self._on_mutation))
        self._on_mutation()

    def __delitem__(self, index):
        super().__delitem__(index)
        self._on_mutation()

    def to_list(self):
        return [to_clean_python(v) for v in self]

    def __deepcopy__(self, memo):
        return copy.deepcopy(to_clean_python(self), memo)

class CentralizedJobStore(dict):
    """
    Centralized proxy store for jobs.
    In development mode: acts as a thread-safe local dictionary + jobs.json persistence.
    In staging/production mode: acts as a Redis-backed centralized store.
    """
    def __init__(self):
        super().__init__()
        self._local_jobs = {}
        self._lock = threading.RLock()
        self._redis_client = None
        self._redis_active = False
        try:
            cache = get_cache()
            if cache.available:
                self._redis_client = cache.client
                self._redis_active = True
                print("🚀 CentralizedJobStore: Redis is active. Using Redis as single source of truth.")
            else:
                print("⚠️ CentralizedJobStore: Redis not available. Falling back to local in-memory store.")
        except Exception as e:
            print(f"⚠️ CentralizedJobStore: Failed to check Redis ({e}). Falling back to local in-memory store.")
            
        # Seed local cache from Redis on startup if active
        if self._redis_active:
            try:
                keys = self._redis_client.smembers("factory:job_keys")
                for k in keys:
                    raw = self._redis_client.get(f"factory:job:{k}")
                    if raw:
                        self._local_jobs[k] = json.loads(raw)
                print(f"🚀 CentralizedJobStore: Seeded {len(self._local_jobs)} jobs from Redis.")
            except Exception as e:
                print(f"⚠️ CentralizedJobStore: Failed to seed from Redis ({e})")

        # ── HIGH-SCALE REFINEMENTS ───────────────────────────────────────────
        from concurrent.futures import ThreadPoolExecutor
        self._executor = ThreadPoolExecutor(max_workers=5)
        self._last_db_sync = {}       # job_id -> float (timestamp)
        self._pending_syncs = {}      # job_id -> dict (latest state)
        self._sync_timers = {}        # job_id -> threading.Timer
        self._sync_generations = {}   # job_id -> int (epoch token for concurrency safety)
        self._sync_lock = threading.Lock()

    def _sync_job_to_store(self, job_id: str, job_dict: dict):
        clean_dict = to_clean_python(job_dict)
        with self._lock:
            self._local_jobs[job_id] = clean_dict
            if self._redis_active:
                try:
                    self._redis_client.set(f"factory:job:{job_id}", json.dumps(clean_dict))
                    self._redis_client.sadd("factory:job_keys", job_id)
                except Exception as e:
                    print(f"⚠️ CentralizedJobStore: Redis write failed for job {job_id}: {e}")
            
        # Throttled sync to the relational MySQL database
        self._enqueue_db_sync(job_id, clean_dict)

    def _enqueue_db_sync(self, job_id: str, clean_dict: dict):
        import time
        import threading
        
        status = clean_dict.get("status", "queued")
        # Terminal statuses bypass throttling to guarantee immediate persistence of final results
        is_terminal = status in ("completed", "failed", "cancelled")
        
        with self._sync_lock:
            # Increment and track active generation epoch to prevent race conditions from canceled timers
            gen = self._sync_generations.get(job_id, 0) + 1
            self._sync_generations[job_id] = gen
            
            # 1. Buffering: Store absolute latest state for eventual writing
            self._pending_syncs[job_id] = clean_dict
            
            # 2. De-duplication: Cancel any active sync timers for this job
            if job_id in self._sync_timers:
                self._sync_timers[job_id].cancel()
                del self._sync_timers[job_id]
                
            now = time.time()
            last_sync = self._last_db_sync.get(job_id, 0.0)
            time_since_last = now - last_sync
            
            if is_terminal or time_since_last >= 2.0:
                # Bypass / Over-interval: Submit immediately on the background thread pool
                self._last_db_sync[job_id] = now
                if job_id in self._pending_syncs:
                    del self._pending_syncs[job_id]
                self._executor.submit(self._sync_job_to_db, job_id, clean_dict)
            else:
                # Active throttle: schedule deferred commit after remaining delay
                delay = 2.0 - time_since_last
                
                def deferred_sync(current_gen=gen):
                    with self._sync_lock:
                        # Safety Check: Ignore timer execution if a newer enqueue epoch has started
                        if self._sync_generations.get(job_id) != current_gen:
                            return
                        if job_id not in self._pending_syncs:
                            return
                        latest_dict = self._pending_syncs.pop(job_id)
                        if job_id in self._sync_timers:
                            del self._sync_timers[job_id]
                        self._last_db_sync[job_id] = time.time()
                    # Execute on background thread pool
                    try:
                        self._executor.submit(self._sync_job_to_db, job_id, latest_dict)
                    except RuntimeError:
                        pass
                    
                timer = threading.Timer(delay, deferred_sync)
                self._sync_timers[job_id] = timer
                timer.start()

    def _sync_job_to_db(self, job_id: str, job_dict: dict):
        try:
            from db.engine import get_session
            from db.models import RenderJob
            from decimal import Decimal
            
            session = get_session()
            if not session:
                return
                
            try:
                job = session.query(RenderJob).filter(RenderJob.job_id == job_id).first()
                if not job:
                    # Create job record if it doesn't exist
                    try:
                        job = RenderJob(
                            job_id=job_id,
                            topic=job_dict.get("topic", "N/A"),
                            source_type=job_dict.get("source_type", "html"),
                            priority=job_dict.get("priority", 100),
                            callback_url=job_dict.get("webhook_url", ""),
                            status=job_dict.get("status", "queued")
                        )
                        session.add(job)
                        session.commit()
                    except Exception as commit_err:
                        # Another concurrent thread already inserted it. Rollback, re-fetch, and update.
                        session.rollback()
                        job = session.query(RenderJob).filter(RenderJob.job_id == job_id).first()
                        if not job:
                            raise commit_err
                
                # Update status
                status = job_dict.get("status", "queued")
                if status in ("queued", "processing", "completed", "failed", "cancelled"):
                    job.status = status
                
                # Update URLs
                if "video_url" in job_dict:
                    job.final_video_url = job_dict["video_url"]
                if "thumbnail_url" in job_dict:
                    job.thumbnail_url = job_dict["thumbnail_url"]
                if "error" in job_dict:
                    job.error_message = job_dict["error"]
                
                # Update costs and metrics
                if "metrics" in job_dict:
                    metrics = job_dict["metrics"]
                    if "total_duration_sec" in metrics:
                        job.duration_seconds = Decimal(str(metrics["total_duration_sec"]))
                    elif "duration_sec" in metrics:
                        job.duration_seconds = Decimal(str(metrics["duration_sec"]))
                
                # Sunk cost / ledger cost
                if "ledger" in job_dict and "total_cost_usd" in job_dict["ledger"]:
                    job.total_cost_usd = Decimal(str(job_dict["ledger"]["total_cost_usd"]))
                elif "total_cost" in job_dict:
                    job.total_cost_usd = Decimal(str(job_dict["total_cost"]))

                # Timestamps
                if status == "processing" and not job.started_at:
                    job.started_at = utcnow()
                elif status in ("completed", "failed", "cancelled") and not job.completed_at:
                    job.completed_at = utcnow()
                
                session.commit()
            except Exception as e:
                session.rollback()
                print(f"⚠️ CentralizedJobStore: DB sync transaction failed for {job_id}: {e}")
            finally:
                session.close()
        except Exception as e:
            # We don't crash primary pipeline on DB log sync failures
            pass

    def __getitem__(self, job_id):
        with self._lock:
            source_dict = None
            if self._redis_active:
                try:
                    raw = self._redis_client.get(f"factory:job:{job_id}")
                    if raw:
                        source_dict = json.loads(raw)
                except Exception as e:
                    print(f"⚠️ CentralizedJobStore: Redis read failed for job {job_id}: {e}")
            
            if source_dict is None:
                if job_id not in self._local_jobs:
                    raise KeyError(job_id)
                source_dict = self._local_jobs[job_id]

            # Create ObservedDict; callback serializes the observed dict itself
            observed = ObservedDict(source_dict, lambda: None)  # placeholder
            def _on_mutate(obs=observed, jid=job_id):
                self._sync_job_to_store(jid, to_clean_python(obs))
            observed._on_mutation = _on_mutate
            # Re-wrap all children with the real callback
            for k, v in list(observed.items()):
                super(ObservedDict, observed).__setitem__(k, wrap_value(v, _on_mutate))
            return observed

    def __setitem__(self, job_id, value):
        with self._lock:
            clean_value = to_clean_python(value)
            self._sync_job_to_store(job_id, clean_value)

    def __delitem__(self, job_id):
        with self._lock:
            if job_id in self._local_jobs:
                del self._local_jobs[job_id]
            if self._redis_active:
                try:
                    self._redis_client.delete(f"factory:job:{job_id}")
                    self._redis_client.srem("factory:job_keys", job_id)
                except Exception as e:
                    print(f"⚠️ CentralizedJobStore: Redis delete failed for job {job_id}: {e}")

    def __contains__(self, job_id):
        with self._lock:
            if self._redis_active:
                try:
                    return bool(self._redis_client.sismember("factory:job_keys", job_id))
                except Exception as e:
                    print(f"⚠️ CentralizedJobStore: Redis sismember failed for job {job_id}: {e}")
            return job_id in self._local_jobs

    def get(self, job_id, default=None):
        try:
            return self[job_id]
        except KeyError:
            return default

    def keys(self):
        with self._lock:
            if self._redis_active:
                try:
                    return list(self._redis_client.smembers("factory:job_keys"))
                except Exception as e:
                    print(f"⚠️ CentralizedJobStore: Redis smembers failed: {e}")
            return list(self._local_jobs.keys())

    def values(self):
        with self._lock:
            return [self[k] for k in self.keys()]

    def items(self):
        with self._lock:
            return [(k, self[k]) for k in self.keys()]

    def __iter__(self):
        return iter(self.keys())

    def __len__(self):
        return len(self.keys())

    def clear(self):
        with self._lock:
            for k in list(self.keys()):
                del self[k]

    def __deepcopy__(self, memo):
        with self._lock:
            res = {}
            for k in self.keys():
                res[k] = copy.deepcopy(to_clean_python(self[k]), memo)
            return res


JOBS_FILE = os.environ.get("JOBS_FILE_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobs.json"))
jobs = CentralizedJobStore()


# Industrial Concurrency Cap: Max 2 high-compute jobs (Manim/Video) at once
# Reduced from 3 to 2 to prevent OOM on ECS during concurrent renders.
RENDER_SEMAPHORE = threading.BoundedSemaphore(2)

# ── Idempotency Cache ─────────────────────────────────────────────────────────
# Prevents duplicate jobs when Spring Boot retries on network blips.
# Maps Idempotency-Key → {job_id, created_at} with a 1-hour TTL.
#
# NOTE: This cache is in-memory and does NOT survive server restarts.
# Accepted risk: during a deploy (typically <30s), a retry could create a
# duplicate job. For zero-downtime deploys, back this with Redis or the
# jobs.json file itself.

_IDEMPOTENCY_TTL_SECONDS = int(os.environ.get("IDEMPOTENCY_TTL", 3600))

def _idempotency_lookup(key: str) -> str | None:
    """Return existing job_id if a non-expired entry exists for this key."""
    if not key:
        return None
    cache = get_cache()
    if not cache.available:
        return None # Graceful degradation
    
    return cache.get(f"idempotency:{key}")

def _idempotency_register(key: str, job_id: str):
    """Store a new idempotency mapping in the persistent cache."""
    if not key:
        return
    cache = get_cache()
    if cache.available:
        cache.set(f"idempotency:{key}", job_id, ttl_seconds=_IDEMPOTENCY_TTL_SECONDS)


# ── Webhook Dead-Letter Queue (DLQ) ──────────────────────────────────────────
# Persists failed webhook payloads to disk so they can be replayed.

DLQ_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webhook_dlq.json")

_dlq_lock = threading.Lock()

def _dlq_persist(job_id: str, payload: dict, webhook_url: str = "", last_status_code: int | None = None, last_error: str = ""):
    """Append a failed webhook payload to the dead-letter queue file."""
    entry = {
        "job_id": job_id,
        "webhook_url": webhook_url,
        "payload": payload,
        "failed_at": utcnow().isoformat() + "Z",
        "last_status_code": last_status_code,
        "last_error": last_error,
        "retries_exhausted": True,
    }
    with _dlq_lock:
        try:
            existing = []
            if os.path.exists(DLQ_FILE):
                with open(DLQ_FILE, "r") as f:
                    existing = json.load(f)
            existing.append(entry)
            with open(DLQ_FILE, "w") as f:
                json.dump(existing, f, indent=2)
            print(f"📬 [DLQ] Persisted failed webhook for job {job_id}")
        except Exception as e:
            print(f"⚠️  [DLQ] Failed to persist webhook for job {job_id}: {e}")


def _sanitize_stalled_jobs():
    """Industrial Sentinel: Clean up 'Processing' jobs and purge their heavy storage folders."""
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
                
                details["updated_at"] = utcnow().isoformat() + "Z"
                found_stalled = True
    if found_stalled:
        _safe_save_jobs("startup stalled-job sanitization")
    
    # ── [NEW] Disk Hygiene Janitor ───────────────────────────────────────────
    # This runs periodically to purge old staging files from output/
    
    def _perform_disk_hygiene():
        """Industrial Janitor: Scan output/ and purge old or orphaned folders."""
        print("🧼 [Hygiene Janitor] Starting scheduled cleanup pass...")
        media_root = os.environ.get("MANIM_MEDIA_DIR", "output")
        if not os.path.exists(media_root):
            return
            
        now = utcnow()
        retention_hours = config.HYGIENE_RETENTION_HOURS
        purged_count = 0
        
        # Reload jobs to get latest timestamps
        all_jobs = _load_jobs()
        
        for item in os.listdir(media_root):
            item_path = os.path.join(media_root, item)
            if not os.path.isdir(item_path) or not item.startswith("job_"):
                continue
                
            job_id = item.replace("job_", "")
            
            # 1. Determine if it's an orphan or stale
            should_purge = False
            reason = ""
            
            if job_id not in all_jobs:
                should_purge = True
                reason = "orphan (no job record)"
            else:
                job_data = all_jobs[job_id]
                created_at_str = job_data.get("created_at")
                if created_at_str:
                    try:
                        # Handle potential Z suffix
                        clean_stamp = created_at_str.replace("Z", "")
                        created_at = datetime.fromisoformat(clean_stamp)
                        age = now - created_at
                        if (age.total_seconds() / 3600) > retention_hours:
                            should_purge = True
                            reason = f"stale (age: {round(age.total_seconds()/3600, 1)}h > {retention_hours}h)"
                    except Exception as e:
                        print(f"⚠️ Hygiene Warning: Could not parse timestamp for job {job_id}: {e}")
            
            # 2. Execute Purge
            if should_purge:
                try:
                    shutil.rmtree(item_path)
                    print(f"🧹 [Hygiene Janitor] Purged {reason}: {item}")
                    purged_count += 1
                except Exception as e:
                    print(f"⚠️ Hygiene Failure on {item_path}: {e}")

        if purged_count > 0:
            print(f"✅ [Hygiene Janitor] Cleanup complete. Purged {purged_count} directories.")
        else:
            print("✨ [Hygiene Janitor] Cleanup complete. Disk is tidy.")

    def _run_hygiene_daemon():
        """Internal background loop for the Janitor daemon."""
        # Initial sleep to let the server warm up
        time.sleep(30)
        while True:
            try:
                _perform_disk_hygiene()
            except Exception as e:
                print(f"⚠️  Hygiene Daemon Error: {e}")
            
            # Wait for next interval
            check_interval = config.HYGIENE_CHECK_INTERVAL_SECONDS
            time.sleep(check_interval)

    # Launch Janitor as a background daemon
    hygiene_thread = threading.Thread(target=_run_hygiene_daemon, daemon=True, name="HygieneJanitor")
    hygiene_thread.start()


def _load_jobs():
    """Industrial Sentinel: Loads jobs from disk and merges into CentralizedJobStore."""
    if not os.path.exists(JOBS_FILE):
        return jobs

    try:
        data = {}
        with open(JOBS_FILE, "r", encoding='utf-8') as f:
            if fcntl: fcntl.flock(f, fcntl.LOCK_SH)
            data = json.load(f)
            if fcntl: fcntl.flock(f, fcntl.LOCK_UN)


        with _jobs_lock:
            # INDUSTRIAL MERGE: Don't just reassign. Update existing entries 
            # to preserve in-memory-only updates (like logs or progress)
            # while bringing in new jobs from disk.
            for jid, jdata in data.items():
                if jid not in jobs:
                    jobs[jid] = jdata
                else:
                    # If job is in memory, only overwrite if local state is stale (not processing)
                    existing = jobs.get(jid)
                    if existing and to_clean_python(existing).get("status") not in ("processing", "queued"):
                        # Merge disk data into CentralizedJobStore
                        merged = to_clean_python(existing)
                        merged.update(jdata)
                        jobs[jid] = merged
        return jobs
    except Exception as e:
        import sys
        print(f"⚠️ Persistence Warning: Could not load jobs ({e})", file=sys.stderr)
        return jobs


def _save_jobs():
    """Industrial Sentinel: Disk persistence with Atomic Write protection."""
    with _jobs_lock:
        # Snapshot the current state — use to_clean_python to strip ObservedDict wrappers
        snapshot = {}
        for k in jobs.keys():
            try:
                snapshot[k] = to_clean_python(jobs[k])
            except Exception as e:
                print(f"⚠️ [_save_jobs] Failed to snapshot job {k}: {e}")

    tmp_file = JOBS_FILE + ".tmp"
    lock_file = JOBS_FILE + ".lock"
    
    try:
        # 1. Acquire cross-process exclusive lock
        with open(lock_file, "w") as lf:
            if fcntl: fcntl.flock(lf, fcntl.LOCK_EX)
            
            # 2. Re-load current disk state for merger
            disk_state = {}
            if os.path.exists(JOBS_FILE):
                try:
                    with open(JOBS_FILE, "r", encoding='utf-8') as f:
                        disk_state = json.load(f)
                except Exception as e:
                    print(f"⚠️ [_save_jobs] Failed to read disk state: {e}")

            # 3. Merger logic: Memory snapshot wins for active records
            for jid, jval in snapshot.items():
                if jid in disk_state:
                    # Logic: Only merge if memory has higher progress or terminal state
                    mem_status = jval.get("status")
                    disk_status = disk_state[jid].get("status")
                    
                    if mem_status in ("completed", "failed", "processing") or disk_status == "queued":
                        disk_state[jid].update(jval)
                else:
                    disk_state[jid] = jval

            # 4. Atomic Write
            with open(tmp_file, "w", encoding='utf-8') as f:
                json.dump(disk_state, f, indent=2, ensure_ascii=False)
            
            os.replace(tmp_file, JOBS_FILE)
            if fcntl: fcntl.flock(lf, fcntl.LOCK_UN)
            
        return True
    except Exception as e:
        print(f"❌ Error persisting factory state: {e}")
        if os.path.exists(tmp_file):
            try: os.remove(tmp_file)
            except Exception as e: print(f"⚠️ [_save_jobs] Failed to clean tmp file: {e}")
        return False


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


# ── Load persisted job store from disk into CentralizedJobStore ──────────────
_load_jobs()

def _start_telegram_bot_loop():
    """Runs a daemon thread to poll the Telegram Bot API and handle interactive commands securely."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id_target = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id_target:
        print("ℹ️ Telegram Bot Loop skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured.")
        return
        
    print("🤖 Starting interactive Telegram Bot thread...")
    
    import time
    import uuid
    import threading
    import copy
    offset = 0
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
            params = {"offset": offset, "timeout": 20}
            resp = requests.get(url, params=params, timeout=30)
            
            if resp.status_code != 200:
                time.sleep(10)
                continue
                
            updates = resp.json().get("result", [])
            for update in updates:
                offset = update.get("update_id", 0) + 1
                
                message = update.get("message")
                if not message:
                    continue
                    
                chat = message.get("chat", {})
                chat_id = str(chat.get("id", ""))
                text = str(message.get("text", "")).strip()
                
                if chat_id != str(chat_id_target):
                    # Unauthorized: Reply with a denial to prevent abuse
                    try:
                        deny_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                        requests.post(deny_url, json={
                            "chat_id": chat_id,
                            "text": "❌ <b>Unauthorized access.</b> Contact administrator to whitelist your Chat ID.",
                            "parse_mode": "HTML"
                        }, timeout=5)
                    except Exception:
                        pass
                    continue
                    
                # Authorized commands
                if not text.startswith("/"):
                    continue
                    
                parts = text.split(maxsplit=1)
                cmd = parts[0].lower().split("@")[0]
                arg = parts[1].strip() if len(parts) > 1 else ""
                
                reply_text = ""

                
                if cmd in ["/start", "/help"]:
                    reply_text = (
                        "👋 <b>Welcome to the EaseToLearn Video Factory Bot!</b>\n\n"
                        "Use me to monitor and control your explainer video compilation pipeline in real-time.\n\n"
                        "<b>Available Commands:</b>\n"
                        "• <code>/status</code> - List active & recent compilation jobs\n"
                        "• <code>/cost</code> - View standard ledgers & API pricing\n"
                        "• <code>/draft &lt;topic&gt;</code> - Get instant AI storyboard drafts\n"
                        "• <code>/render &lt;topic&gt;</code> - Dispatch full HD video compile\n"
                    )
                elif cmd == "/status":
                    _load_jobs()
                    job_list = list(jobs.items())
                    if not job_list:
                        reply_text = "ℹ️ No compilation jobs in registry."
                    else:
                        reply_text = "<b>📋 Recent Compilation Queue:</b>\n\n"
                        for j_id, j_data in sorted(job_list, key=lambda x: x[1].get("created_at", ""), reverse=True)[:5]:
                            status = j_data.get("status", "unknown").upper()
                            topic = j_data.get("topic", "N/A")
                            cost = j_data.get("usd_cost", 0.0)
                            prog = j_data.get("progress", 0)
                            
                            emoji = "⏳"
                            if status == "COMPLETED": emoji = "✅"
                            elif status == "FAILED": emoji = "❌"
                            elif status == "COMPILING": emoji = "⚙️"
                            
                            reply_text += f"{emoji} <b>Job ID:</b> <code>{j_id}</code>\n"
                            reply_text += f"   <b>Topic:</b> {topic}\n"
                            reply_text += f"   <b>Status:</b> {status} ({prog}%)\n"
                            reply_text += f"   <b>Cost:</b> ${cost:.4f}\n\n"
                elif cmd == "/cost":
                    reply_text = (
                        "<b>💳 EaseToLearn Live Cost Ledgers:</b>\n\n"
                        "• <b>Groq LLM Tokens:</b> $0.00015 / 1k tokens\n"
                        "• <b>ElevenLabs TTS:</b> $0.00030 / character\n"
                        "• <b>DALL-E Doodles:</b> $0.04000 / slide\n"
                        "• <b>HeyGen Lip-Sync:</b> $0.15000 / video-sec\n"
                    )
                elif cmd == "/draft":
                    if not arg:
                        reply_text = "⚠️ <b>Usage:</b> <code>/draft &lt;topic&gt;</code>\nExample: <code>/draft Pythagorean Theorem</code>"
                    else:
                        try:
                            # Send initial placeholder reply to indicate work
                            interim_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                            requests.post(interim_url, json={
                                "chat_id": chat_id,
                                "text": f"⏳ <i>Drafting storyboard blueprint for topic: \"{arg}\"...</i>",
                                "parse_mode": "HTML"
                            }, timeout=5)
                            
                            # Run parser & director
                            from html_parser import parse_tony_html
                            parsed = parse_tony_html(f"<h1>{arg}</h1><p>Generate a comprehensive explainer tutorial.</p>", topic_hint=arg)
                            
                            from director_agent import run_director
                            director_output, _ = run_director(
                                parsed_facts=parsed,
                                job_id="tg-draft"
                            )
                            
                            scenes = director_output.scenes
                            reply_text = f"<b>📝 Storyboard Draft for: \"{arg}\"</b>\n"
                            reply_text += f"Proposed render path: <code>{director_output.render_mode}</code>\n\n"
                            
                            for i, s in enumerate(scenes[:4]): # limit to 4 to prevent message overflow
                                reply_text += f"<b>Slide {i+1} ({s.visual_type}):</b>\n"
                                reply_text += f"🎙️ <i>\"{s.narration_text[:60]}...\"</i>\n"
                                if s.tony_pose:
                                    reply_text += f"👤 Pose: <code>{s.tony_pose}</code>\n"
                                reply_text += "\n"
                            if len(scenes) > 4:
                                reply_text += f"<i>...and {len(scenes)-4} more slides.</i>"
                        except Exception as e:
                            reply_text = f"❌ <b>Drafting failed:</b> {e}"
                elif cmd == "/render":
                    if not arg:
                        reply_text = "⚠️ <b>Usage:</b> <code>/render &lt;topic&gt;</code>\nExample: <code>/render Pythagorean Theorem</code>"
                    else:
                        try:
                            interim_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                            requests.post(interim_url, json={
                                "chat_id": chat_id,
                                "text": f"🚀 <i>Initializing HD Video Compile for: \"{arg}\"...</i>",
                                "parse_mode": "HTML"
                            }, timeout=5)
                            
                            # Build standard request payload and dispatch
                            from html_parser import parse_tony_html
                            parsed = parse_tony_html(f"<h1>{arg}</h1><p>Interactive tutorial outline.</p>", topic_hint=arg)
                            
                            from director_agent import run_director
                            director_output, _ = run_director(
                                parsed_facts=parsed,
                                job_id="tg-render"
                            )
                            
                            # Generate a unique job ID
                            new_job_id = str(uuid.uuid4())[:12]
                            now_iso = utcnow().isoformat() + "Z"
                            
                            # Construct initial state
                            job_data = {
                                "job_id":       new_job_id,
                                "status":       "queued",
                                "video_url":    "",
                                "thumbnail_url": "",
                                "error":        "",
                                "progress":     0,
                                "current_step": "Initializing",
                                "render_mode":  director_output.render_mode or "auto",
                                "with_avatar":  True,
                                "avatar_type":  "tony_cartoon",
                                "avatar_id":    None,
                                "video_type":   None,
                                "use_elevenlabs": True,
                                "image_path":   None,
                                "webhook_url":  None,
                                "created_at":   now_iso,
                                "updated_at":   now_iso,
                                "topic":        arg,
                                "raw_html":     parsed["html_content"],
                                "storyboard":   [s.model_dump() if hasattr(s, "model_dump") else s for s in director_output.scenes],
                                "overrides":    None,
                                "logs":         [{"node": "SYSTEM", "msg": "🚀 Job initialized via Telegram Bot", "type": "info"}]
                            }
                            
                            with _jobs_lock:
                                jobs[new_job_id] = job_data
                            
                            # DB Persistence
                            try:
                                from db.repository import create_job
                                create_job(
                                    job_id=new_job_id,
                                    topic=arg,
                                    source_type="html",
                                    render_mode_requested=director_output.render_mode or "auto",
                                    with_avatar=True,
                                    avatar_type="tony_cartoon",
                                    callback_url=None
                                )
                            except Exception:
                                pass
                                
                            _save_jobs()
                            
                            # Start thread
                            t = threading.Thread(
                                target=_run_pipeline,
                                args=(new_job_id, arg, parsed["html_content"], "html", None),
                                name=f"compile_{new_job_id}"
                            )
                            t.daemon = True
                            t.start()
                            
                            reply_text = (
                                f"🚀 <b>HD Compile Dispatched successfully!</b>\n\n"
                                f"<b>Job ID:</b> <code>{new_job_id}</code>\n"
                                f"<b>Topic:</b> {arg}\n"
                                f"Use <code>/status</code> to check progress!"
                            )
                        except Exception as e:
                            reply_text = f"❌ <b>Compilation launch failed:</b> {e}"
                else:
                    reply_text = "❌ <b>Unknown command.</b> Use <code>/help</code> to see all options."
                    
                if reply_text:
                    try:
                        send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                        requests.post(send_url, json={
                            "chat_id": chat_id,
                            "text": reply_text,
                            "parse_mode": "HTML"
                        }, timeout=10)
                    except Exception as e:
                        print(f"⚠️ Failed to send Telegram reply: {e}")
                        
        except Exception as e:
            print(f"⚠️ Telegram Bot loop error: {e}")
            time.sleep(5)


def start_industrial_services():
    """Starts the background janitor and sanitizes stalled jobs."""
    _sanitize_stalled_jobs()

# Only run if explicitly called or if main
if __name__ == "__main__":
    start_industrial_services()


@app.on_event("startup")
def on_startup():
    """FastAPI startup hook to initialize industrial services and Telegram interactive bot."""
    print("🚀 FastAPI App Startup Initializing...")
    try:
        _sanitize_stalled_jobs()
    except Exception as e:
        print(f"⚠️ Failed to sanitize stalled jobs: {e}")
        
    # Start interactive Telegram Bot loop in background thread
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id_target = os.environ.get("TELEGRAM_CHAT_ID")
    if bot_token and chat_id_target:
        import threading
        bot_thread = threading.Thread(target=_start_telegram_bot_loop, name="telegram_bot")
        bot_thread.daemon = True
        bot_thread.start()
        print("🤖 Interactive Telegram Bot thread dispatched successfully.")




def _send_telegram_notification(job_id: str, status_data: dict):
    """Sends a premium, highly formatted real-time status alert to Telegram when a video job completes or fails."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        return
        
    status = status_data.get("status", "unknown").upper()
    topic = status_data.get("topic", "N/A")
    video_url = status_data.get("video_url", "")
    cost = status_data.get("usd_cost", 0.0)
    error = status_data.get("error", "")
    
    emoji = "✅" if status == "COMPLETED" else "❌"
    
    msg = f"<b>{emoji} EaseToLearn Video Factory Job Update</b>\n\n"
    msg += f"<b>Job ID:</b> <code>{job_id}</code>\n"
    msg += f"<b>Topic:</b> {topic}\n"
    msg += f"<b>Status:</b> <code>{status}</code>\n"
    msg += f"<b>Incurred Cost:</b> ${cost:.4f}\n"
    
    if status == "COMPLETED" and video_url:
        msg += f"\n🎬 <b>Watch Video:</b> {video_url}\n"
    elif error:
        msg += f"\n⚠️ <b>Error Details:</b> <code>{error}</code>\n"
        
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": msg,
            "parse_mode": "HTML"
        }
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code < 300:
            print(f"✈️  Telegram notification sent successfully for job {job_id}")
        else:
            print(f"⚠️  Telegram API returned status {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"⚠️  Failed to send Telegram notification: {e}")


def _notify_webhook_with_retry(job_id: str, status_data: dict):
    """Industrial Sentinel: Robust notification with exponential backoff and full payload parity."""
    # Send Telegram notification if configured
    _send_telegram_notification(job_id, status_data)
    
    # Priority: 1. Request-specific URL | 2. Registry value | 3. Global Env
    webhook_url = status_data.get("webhook_url") or os.environ.get("WEBHOOK_URL")
    
    if not webhook_url:
        return

    import time
    max_retries = 5

    last_status_code = None
    last_error = ""
    for attempt in range(max_retries):
        try:
            # Use a longer timeout for the webhook itself
            headers = {}
            webhook_secret = os.environ.get("FACTORY_WEBHOOK_SECRET")
            if webhook_secret:
                headers["X-Webhook-Secret"] = webhook_secret
            resp = requests.post(webhook_url, json=status_data, headers=headers, timeout=60)
            last_status_code = resp.status_code

            if resp.status_code < 300:
                print(f"🔔 Webhook Success (Job {job_id}) on attempt {attempt + 1}")
                return
            else:
                last_error = f"HTTP {resp.status_code}"
                print(f"⚠️  Webhook Status {resp.status_code} on attempt {attempt + 1}")
        except requests.RequestException as e:
            last_error = str(e)
            print(f"⚠️  Webhook Retry {attempt + 1} for job {job_id}: {e}")
        
        if attempt < max_retries - 1:
            # Jittered exponential backoff: 2, 4, 8, 16 seconds
            wait_time = (2 ** attempt) + (attempt * 2)
            time.sleep(wait_time)

    print(f"❌ Webhook FAILED (Job {job_id}) after {max_retries} attempts. Persisting to DLQ.")
    _dlq_persist(job_id, status_data, webhook_url=webhook_url, last_status_code=last_status_code, last_error=last_error)



# ── Pipeline runner ───────────────────────────────────────────────────────────
class RenderOverrides(BaseModel):
    render_mode: Optional[str] = Field(None, description="Force a specific render path: manim | presentation | explainer | heygen")
    has_formula: Optional[bool] = Field(None, description="Force/Hint math detection")
    has_static_image: Optional[bool] = Field(None, description="Force/Hint image grounding")
    enable_ambient: Optional[bool] = None
    animation_enabled: Optional[bool] = Field(None, description="Force/Hint cinematic animations")
    with_avatar: Optional[bool] = Field(None, description="Force/Hint avatar generation")
    use_elevenlabs: Optional[bool] = Field(None, description="Force ElevenLabs high-fidelity TTS")
    language: Optional[str] = Field(None, description="Force language: en | hi")

class RenderRequest(BaseModel):
    topic:       str
    html:        Optional[Any] = None  # Legacy/Composite HTML field
    solution_v2: Optional[Any] = None  # Spring Boot solutionV2 format
    json_data:   Optional[Any] = None  # Structured JSON facts or derivation steps
    markdown:    Optional[str] = None  # Markdown content with LaTeX support
    render_mode: Optional[Literal["manim", "presentation", "explainer", "heygen", "notes", "user_generated_video", "user_generated"]] = None
    with_avatar: bool = False
    avatar_type: Optional[Literal["logo", "human", "pro", "user", "heygen", "tony_cartoon"]] = None
    avatar_id:   Optional[str] = None
    video_type:  Optional[Literal["marketing", "educational"]] = None
    image_path:  Optional[str] = None
    webhook_url: Optional[str] = None
    use_elevenlabs: bool = False # Direct per-request switch (Industrial Cost Control)
    storyboard: Optional[list[dict]] = Field(None, description="Custom storyboard scene blueprints from Editor Studio")
    overrides: Optional[RenderOverrides] = Field(None, description="Manual control toggles to override autonomous logic")

    class Config:
        json_schema_extra = {
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
    knowledge_base: dict[str, Any]  # {total_fact_sheets, storage_usage_kb}
    finance: dict[str, Any]         # {total_est_cost_usd, avg_cost_per_video}
    health: dict[str, str]          # {gemma_status, searxng_status}

    class Config:
        json_schema_extra = {
            "example": {
                "total_jobs": 100,
                "completed": 85,
                "failed": 15,
                "success_rate": "85.0%",
                "avg_render_time_sec": 45.2,
                "render_modes_breakdown": {"manim": 50, "presentation": 35},
                "knowledge_base": {"total_fact_sheets": 42, "storage_usage_kb": 125.5},
                "finance": {"total_est_cost_usd": 12.45, "avg_cost_per_video": 0.14},
                "health": {"gemma_status": "online", "searxng_status": "online"}
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
    actual_cost_usd: float # Real measured cost from API responses
    estimated_cost_usd: float # Fallback estimate for legacy jobs or redundant field for new ones
    cost_source: str # "measured" | "estimated"


class CostsResponse(BaseModel):
    total_cost_usd: float
    completed_jobs: int
    avg_cost_per_video_usd: float
    breakdown: list[CostItem]
    note: str
    total_estimated_cost_usd: float # Legacy alias for backward compatibility

    class Config:
        json_schema_extra = {
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
        json_schema_extra = {
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
        json_schema_extra = {
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

class DubResponse(BaseModel):
    job_id: str
    language: str
    dubbed_video_url: str
    status: str = "completed"

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "3193cfab",
                "language": "hindi",
                "dubbed_video_url": "http://localhost:8000/stream/3193cfab/video_hindi.mp4",
                "status": "completed"
            }
        }



# ── Pipeline runner ───────────────────────────────────────────────────────────

def _run_pipeline(job_id: str, topic: str, html: str, source_type: str = "html", overrides: dict = None):
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
            now_iso = utcnow().isoformat() + "Z"
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
        if injected_image:
            if injected_image.startswith(("http://", "https://")):
                import requests, shutil
                try:
                    # Industrial Sentinel: Robust URL Encoding for special characters/spaces
                    import urllib.parse
                    parsed_url = urllib.parse.urlparse(injected_image)
                    encoded_path = urllib.parse.quote(parsed_url.path)
                    safe_url = urllib.parse.urlunparse(parsed_url._replace(path=encoded_path))
                    
                    # Wikipedia/CDN protection: Send a browser User-Agent
                    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}
                    resp = requests.get(safe_url, headers=headers, timeout=30)
                    resp.raise_for_status()
                    
                    dest = os.path.join(job_dir, "tony_diagram.png")
                    with open(dest, 'wb') as f:
                        f.write(resp.content)
                    print(f"📸 Downloaded injected image: {dest} ({len(resp.content)} bytes) | Original: {injected_image}")
                except Exception as e:
                    print(f"⚠️ Failed to download image: {e}")
            elif os.path.exists(injected_image):
                import shutil
                dest = os.path.join(job_dir, "tony_diagram.png")
                shutil.copy2(injected_image, dest)
                print(f"📸 Using injected local image: {dest}")

        try:
            from autonomous_graph import app as graph

            final_state = graph.invoke({
                "job_id":            job_id,
                "raw_input":         html,
                "topic":             topic,
                "attempt_count":     0,
                "parsed_facts":      None,
                "source_type":       source_type,
                "render_mode":       job.get("render_mode"),
                "with_avatar":       job.get("with_avatar", False),
                "overrides":         overrides,
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
                "use_elevenlabs":     job.get("use_elevenlabs", False),
                "avatar_type":        job.get("avatar_type"),
                "avatar_id":          job.get("avatar_id"),
                "storyboard":         job.get("storyboard"),
            })
        except ImportError as e:
            error_category = "DEPENDENCY"
            error_detail = f"Missing module: {e.name if hasattr(e, 'name') else e}"
        except (KeyError, ValueError, TypeError) as e:
            error_category = "DATA"
            error_detail = f"{type(e).__name__}: {e}"
        except Exception as e:
            error_category = type(e).__name__
            error_detail = str(e)
            
            # Industrial Sentinel: Calculate sunk costs even on failure
            from cost_tracker import LedgerManager
            sunk_cost = LedgerManager.get_job_total_cost(job_id)
            print(f"❌ [{error_category}] Pipeline Error for job {job_id}: {error_detail} (Sunk Cost: ${sunk_cost})")
        else:
            error_category = None
            error_detail = None

        if error_category:
            print(f"❌ [{error_category}] Pipeline Error for job {job_id}: {error_detail}")
            with _jobs_lock:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["error"]  = f"[{error_category}] {error_detail}"

            duration = time.time() - start_pipeline_t
            with _jobs_lock:
                if "metrics" not in jobs[job_id]:
                    jobs[job_id]["metrics"] = {}
                jobs[job_id]["metrics"]["total_duration_sec"] = round(duration, 2)
                jobs[job_id]["updated_at"] = utcnow().isoformat() + "Z"
            
            _safe_save_jobs(f"pipeline failed ({job_id})")
            
            # DB Persistence: Hook 4 - Job Failed
            try:
                from db.repository import update_job_status
                from cost_tracker import LedgerManager
                sunk_cost = LedgerManager.get_job_total_cost(job_id)
                update_job_status(
                    job_id=job_id,
                    status="failed",
                    error_node=error_category,
                    error_message=error_detail,
                    total_cost_usd=sunk_cost,
                    duration_seconds=time.time() - start_pipeline_t
                )
            except Exception as e:
                pass
            
            import threading
            threading.Thread(
                target=_notify_webhook_with_retry,
                args=(job_id, {
                    "job_id": job_id,
                    "status": "failed",
                    "error": f"[{error_category}] {error_detail}",
                    "video_url": "",
                    "progress": 0,
                    "usd_cost": sunk_cost,
                    "webhook_url": jobs[job_id].get("webhook_url"),
                    "updated_at": utcnow().isoformat() + "Z"
                }),
                daemon=True,
                name=f"webhook_fail_{job_id}"
            ).start()
            return

        # ── Post-Render Phase (Network I/O) ──
        # Semaphore is held during state persistence to avoid race conditions.
        video_url = final_state.get("video_url") or ""
        error_msg = final_state.get("rendering_errors", "")

        with _jobs_lock:
            # Transfer Ledger for Financial Analytics (Grounded Usage Tracking)
            if "ledger" in final_state:
                jobs[job_id]["ledger"] = final_state["ledger"]

            if video_url:
                jobs[job_id]["status"]        = "completed"
                jobs[job_id]["video_url"]     = video_url
                jobs[job_id]["thumbnail_url"] = final_state.get("thumbnail_url") or ""
                jobs[job_id]["logs"].append({"node": "DEPLOY", "msg": "Video production finalized and uploaded.", "type": "success"})
                print(f"✅ Job {job_id} completed: {video_url}")
            else:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["error"]  = error_msg or "No output produced"
                print(f"❌ Job {job_id} failed: {error_msg}")
                jobs[job_id]["logs"].append({"node": "SYSTEM", "msg": f"Failure: {jobs[job_id]['error']}", "type": "warning"})
                print(f"❌ Job {job_id} failed: {jobs[job_id]['error']}")

            final_status = jobs[job_id]["status"]
            final_error  = jobs[job_id]["error"]

        _safe_save_jobs(f"pipeline finalize ({job_id})")

        # DB Persistence: Hook 4 - Job Completed/Failed (Final)
        try:
            from db.repository import update_job_status, upsert_video_cache
            from cost_tracker import LedgerManager
            sunk_cost = LedgerManager.get_job_total_cost(job_id)
            total_duration = time.time() - start_pipeline_t
            
            with _jobs_lock:
                status = jobs[job_id]["status"]
                error = jobs[job_id]["error"]
                v_url = jobs[job_id]["video_url"]
                t_url = jobs[job_id]["thumbnail_url"]
            
            update_job_status(
                job_id=job_id,
                status=status,
                video_url=v_url,
                thumbnail_url=t_url,
                error_message=error,
                total_cost_usd=sunk_cost,
                duration_seconds=total_duration
            )
            
            if v_url:
                upsert_video_cache(
                    job_id=job_id,
                    video_url=v_url,
                    thumbnail_url=t_url,
                    render_mode=jobs[job_id].get("render_mode", "auto"),
                    topic=topic,
                    total_cost_usd=sunk_cost,
                    duration_seconds=int(total_duration),
                    status="ready"
                )
        except Exception as e:
            pass

    # Final Webhook Handover with 3-attempt exponential backoff
    with _jobs_lock:
        final_payload = dict(jobs[job_id])
    
    import threading
    threading.Thread(
        target=_notify_webhook_with_retry,
        args=(job_id, final_payload),
        daemon=True,
        name=f"webhook_{job_id}"
    ).start()


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

@app.post("/storyboard/draft", dependencies=[SecurityDep], tags=["Core"], summary="Draft storyboard blueprint", description="Drafts a storyboard outline (render_mode, reasoning, scenes) using the Director Agent without compiling a video. The result can be reviewed and edited in the Storyboard Studio.")
def draft_storyboard(request: RenderRequest):
    combined_inputs = []
    source_labels = []
    
    if request.json_data:
        combined_inputs.append(request.json_data)
        source_labels.append("json")
    if request.html:
        combined_inputs.append(request.html)
        source_labels.append("html")
    if request.markdown:
        combined_inputs.append(request.markdown)
        source_labels.append("markdown")
    if request.solution_v2:
        combined_inputs.append(request.solution_v2)
        source_labels.append("solution_v2")

    if not combined_inputs:
        raise HTTPException(status_code=400, detail="At least one content source (html, json_data, or markdown) is required")

    if len(combined_inputs) == 1:
        raw_content = combined_inputs[0]
    else:
        raw_content = combined_inputs

    from html_parser import parse_tony_html
    parsed = parse_tony_html(raw_content, topic_hint=request.topic)

    # Inject solution_v2 as knowledge if available
    knowledge_base = None
    if isinstance(raw_content, list) and all(isinstance(item, dict) and "title" in item for item in raw_content):
        from knowledge_manager import inject_solution_v2_as_knowledge
        knowledge_base = inject_solution_v2_as_knowledge(request.topic, raw_content)

    from director_agent import run_director
    director_output, usage = run_director(
        parsed,
        knowledge_base=knowledge_base,
        avatar_type=request.avatar_type,
        with_avatar=request.with_avatar
    )

    scenes = [
        (s.model_dump() if hasattr(s, "model_dump") else s.dict()) 
        for s in director_output.scenes
    ]

    return {
        "render_mode": request.render_mode or director_output.render_mode,
        "decision_reasoning": director_output.decision_reasoning,
        "scenes": scenes
    }

@app.post("/render", response_model=JobStatus, dependencies=[SecurityDep], tags=["Core"], summary="Submit single job", description="Accepts lesson HTML, JSON, or Markdown to queue a single video production job. Returns a job_id immediately while rendering proceeds in a background thread.")
def start_render(
    request: RenderRequest = Body(
        ...,
        openapi_examples={
            "HTML Input": {
                "summary": "Legacy HTML support",
                "description": "The original format using the 'html' field.",
                "value": {
                    "topic": "Newton's Laws of Motion",
                    "html": "<html><body><h1>Lesson 1</h1><p>Force equals mass times acceleration.</p></body></html>",
                    "render_mode": "manim"
                }
            },
            "JSON Input": {
                "summary": "Structured JSON facts",
                "description": "Send a list of dictionaries for precise fact control.",
                "value": {
                    "topic": "Chemistry Basics",
                    "json_data": [
                        {"title": "The Atom", "description": "Basic unit of matter."},
                        {"title": "Molecules", "description": "Groups of atoms bonded together."}
                    ],
                    "render_mode": "presentation"
                }
            },
            "Markdown Input": {
                "summary": "Raw Markdown",
                "description": "Write your lesson in plain markdown.",
                "value": {
                    "topic": "History of AI",
                    "markdown": "# Early AI\n\n- **1950**: Turing Test\n- **1956**: Dartmouth Workshop",
                    "render_mode": "explainer"
                }
            }
        }
    ),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    # ── 0. Idempotency Guard ──
    # Industrial Hardening: Use payload-based hash if header is missing
    effective_key = idempotency_key or generate_idempotency_key(
        request.model_dump(exclude={"overrides"}), 
        request.render_mode, 
        request.overrides.model_dump() if request.overrides else None
    )
    
    existing_job_id = _idempotency_lookup(effective_key)
    if existing_job_id:
        _load_jobs()
        with _jobs_lock:
            if existing_job_id in jobs:
                print(f"🔁 Idempotency hit: key={effective_key} → job={existing_job_id}")
                res = copy.deepcopy(jobs[existing_job_id])
                res["from_cache"] = True
                return res

    # ── 1. [NEW] Polymorphic Appender (Priority & Concatenation) ──
    # Industrial Requirement: Support mixed input schemas (JSON + HTML + Markdown) appended in order.
    combined_inputs = []
    source_labels = []
    
    if request.json_data:
        combined_inputs.append(request.json_data)
        source_labels.append("json")
    if request.html:
        combined_inputs.append(request.html)
        source_labels.append("html")
    if request.markdown:
        combined_inputs.append(request.markdown)
        source_labels.append("markdown")
    if request.solution_v2:
        combined_inputs.append(request.solution_v2)
        source_labels.append("solution_v2")

    if not combined_inputs:
        raise HTTPException(status_code=400, detail="topic and at least one content source (html, json_data, or markdown) are required")

    # If only one input, keep original behavior for logging, otherwise use 'composite'
    if len(combined_inputs) == 1:
        raw_content = combined_inputs[0]
        source_type = source_labels[0]
    else:
        raw_content = combined_inputs
        source_type = "composite (" + "+".join(source_labels) + ")"

    if not request.topic or not raw_content:
        raise HTTPException(status_code=400, detail="topic and at least one content source (html, json_data, or markdown) are required")

    # 🛡️ MEDIA HARDENING: Validate image assets before enqueuing
    if request.image_path:
        _validate_image_asset(request.image_path)

    # INDUSTRIAL SENTINEL: Refresh memory state before collision check
    _load_jobs()
    
    # Industrial Sentinel: UUID Collision Guard for Infinite Scale
    while True:
        job_id = str(uuid.uuid4())[:12]
        with _jobs_lock:
            if job_id not in jobs:
                break
    
    # Register the job ID with the idempotency key before starting
    _idempotency_register(effective_key, job_id)


    now_iso = utcnow().isoformat() + "Z"

    with _jobs_lock:
        init_msg = f"🚀 Job initialized for topic: {request.topic} | Source: {source_type.upper()} | Mode: {request.render_mode or 'auto'} | Avatar: {request.with_avatar}"
        jobs[job_id] = {
            "job_id":       job_id,
            "status":       "queued",
            "video_url":    "",
            "thumbnail_url": "",
            "error":        "",
            "progress":     0,
            "current_step": "Initializing",
            "render_mode":  request.render_mode or "auto",
            "with_avatar":  request.with_avatar,
            "avatar_type":  request.avatar_type,
            "avatar_id":    request.avatar_id,
            "video_type":   request.video_type,
            "use_elevenlabs": request.use_elevenlabs,
            "image_path":   request.image_path,
            "webhook_url":  request.webhook_url,
            "created_at":   now_iso,
            "updated_at":   now_iso,
            "topic":        request.topic,
            "raw_html":     raw_content,
            "storyboard":    request.storyboard,
            "overrides":    request.overrides.model_dump() if request.overrides else None,
            "logs":         [{"node": "SYSTEM", "msg": init_msg, "type": "info"}]
        }

    # DB Persistence: Hook 1 - Job Submitted
    try:
        from db.repository import create_job
        create_job(
            job_id=job_id,
            topic=request.topic,
            source_type=source_type,
            render_mode_requested=request.render_mode or "auto",
            with_avatar=request.with_avatar,
            avatar_type=request.avatar_type,
            callback_url=request.webhook_url
        )
    except Exception as e:
        pass


    thread = threading.Thread(
        target=_run_pipeline,
        args=(job_id, request.topic, raw_content, source_type, request.overrides.model_dump() if request.overrides else None),
        daemon=True,
    )
    thread.start()

    # Snapshot BEFORE save (save may reload+merge and temporarily displace new job)
    with _jobs_lock:
        job_snapshot = copy.deepcopy(jobs[job_id])

    _safe_save_jobs(f"start_render enqueue ({job_id})", fatal=False)  # non-fatal

    _idempotency_register(idempotency_key, job_id)
    print(f"🚀 Job {job_id} queued for: {request.topic}")
    return job_snapshot


@app.post("/bulk_render", response_model=BulkRenderResponse, dependencies=[SecurityDep], tags=["Core"], summary="Submit batch jobs", description="Accepts a JSON array of lessons. Jobs are processed sequentially in a single background worker to prevent resource exhaustion.")
async def bulk_render(
    file: UploadFile = File(...),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    """Accept a JSON file and queue all lessons as separate jobs."""
    # ── Idempotency Guard ──
    existing_job_id = _idempotency_lookup(idempotency_key)
    if existing_job_id:
        # For bulk, we stored a comma-separated list of job_ids as the "job_id"
        cached_ids = existing_job_id.split(",")
        print(f"🔁 Bulk idempotency hit: key={idempotency_key} → {len(cached_ids)} jobs")
        return {"job_ids": cached_ids, "total": len(cached_ids), "status": "queued"}

    content = await file.read()
    
    try:
        lessons = json.loads(content)
    except Exception as e:
        print(f"⚠️ [bulk_render] Invalid JSON upload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    
    if not isinstance(lessons, list):
        raise HTTPException(status_code=400, detail="JSON must be an array of lessons")
    
    print(f"DEBUG: Loaded {len(lessons)} lessons from bulk upload")
    
    job_ids = []
    from datetime import datetime
    
    def _run_bulk_sequential(job_queue):
        for job_id, topic, raw_content, source_type in job_queue:
            _run_pipeline(job_id, topic, raw_content, source_type)
            print(f"✅ Bulk: Job {job_id} done, moving to next...")

    job_queue = []
    for lesson in lessons:
        topic = lesson.get("topic", "Untitled")
        
        # ── Polymorphic Content Resolution (Industrial Standard) ──
        source_type = "html"
        raw_content = lesson.get("html")
        if lesson.get("json_data"):
            raw_content = lesson.get("json_data")
            source_type = "json"
        elif lesson.get("markdown"):
            raw_content = markdown.markdown(lesson.get("markdown"), extensions=['extra', 'tables', 'fenced_code'])
            source_type = "markdown"

        if not raw_content:
            print(f"⚠️ Skipping bulk lesson '{topic}': No valid content (html, json_data, or markdown) found.")
            continue
            
        img_path = lesson.get("image_path")
        # 🛡️ MEDIA HARDENING: Bulk Validation
        if img_path:
            try:
                _validate_image_asset(img_path)
            except HTTPException as e:
                print(f"⚠️ Skipping bulk lesson '{topic}' due to invalid media: {e.detail}")
                continue
            
        while True:
            job_id = str(uuid.uuid4())[:12]
            with _jobs_lock:
                if job_id not in jobs:
                    break
        
        now_iso = utcnow().isoformat() + "Z"
        
        with _jobs_lock:
            init_msg = f"🚀 Bulk job initialized for topic: {topic} | Source: {source_type.upper()} | Mode: {lesson.get('render_mode', 'auto')}"
            jobs[job_id] = {
                "job_id":       job_id,
                "topic":        topic,
                "status":       "queued",
                "video_url":    "",
                "thumbnail_url": "",
                "error":        "",
                "progress":     0,
                "current_step": "Initializing",
                "render_mode":  lesson.get("render_mode"),
                "with_avatar":  lesson.get("with_avatar", False),
                "video_type":   lesson.get("video_type", "educational"),
                "image_path":   None,
                "created_at":   now_iso,
                "updated_at":   now_iso,
                "raw_html":     raw_content,
                "logs":         [{"node": "SYSTEM", "msg": init_msg, "type": "info"}],
                "metrics":      {}
            }
        
        # DB Persistence: Hook 1 - Job Submitted (Bulk)
        try:
            from db.repository import create_job
            create_job(
                job_id=job_id,
                topic=topic,
                source_type=source_type,
                render_mode_requested=lesson.get("render_mode") or "auto",
                with_avatar=lesson.get("with_avatar", False),
                avatar_type=lesson.get("avatar_type")
            )
        except Exception as e:
            pass

        job_ids.append(job_id)
        job_queue.append((job_id, topic, raw_content, source_type))

    # Single thread runs all jobs one after another
    thread = threading.Thread(
        target=_run_bulk_sequential,
        args=(job_queue,),
        daemon=True,
    )
    thread.start()
    
    _safe_save_jobs("bulk_render enqueue")
    _idempotency_register(idempotency_key, ",".join(job_ids))
    print(f"🚀 Bulk ingest: {len(job_ids)} jobs queued")
    
    return {"job_ids": job_ids, "total": len(job_ids), "status": "queued"}


@app.get("/jobs", response_model=dict[str, JobStatus], dependencies=[SecurityDep], tags=["Core"], summary="List all jobs", description="Retrieves the full registry of all current and historical jobs from the persistence layer.")
def get_all_jobs():
    """Returns all jobs for the Factory Portal dashboard."""
    _load_jobs()
    with _jobs_lock:
        # INDUSTRIAL SENTINEL: Return a snapshot copy to prevent mutation pollution
        return copy.deepcopy(dict(jobs))



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
        # Snapshot copy for thread-safe state isolation
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
    total_cost = 0.0
    
    # Cost constants (sync with estimate_costs)
    COST_PER_GROQ_CALL = 0.002
    COST_PER_ELEVENLABS_CHAR = 0.00003
    COST_PER_HEYGEN_SEC = 0.0333
    COST_PER_HIGGSFIELD_CALL = 0.10

    for j in completed:
        mode = j.get("render_mode") or "auto"
        render_modes[mode] = render_modes.get(mode, 0) + 1
        
        # ── Financial Aggregation ──
        ledger = j.get("ledger", {})
        if ledger:
            prompt_tokens = ledger.get("prompt_tokens", 0)
            completion_tokens = ledger.get("completion_tokens", 0)
            elevenlabs_chars = ledger.get("elevenlabs_chars", 0)
            heygen_seconds = ledger.get("heygen_seconds", 0)
            higgsfield_calls = ledger.get("higgsfield_calls", 0)

            llm_cost = (prompt_tokens + completion_tokens) / 1_000_000 * 0.50
            voice_cost = elevenlabs_chars * COST_PER_ELEVENLABS_CHAR
            avatar_cost = heygen_seconds * COST_PER_HEYGEN_SEC
            explainer_cost = higgsfield_calls * COST_PER_HIGGSFIELD_CALL
            
            total_cost += llm_cost + voice_cost + avatar_cost + explainer_cost
        else:
            # Fallback for Legacy/Migrated Jobs without ledgers
            has_avatar = j.get("with_avatar", False)
            est = COST_PER_GROQ_CALL * 3 
            est += COST_PER_ELEVENLABS_CHAR * 2000
            if mode == "explainer": est += COST_PER_HIGGSFIELD_CALL * 3
            if has_avatar: est += COST_PER_HEYGEN_SEC * 60  # ~60s average avatar video
            total_cost += est
        
    durations = [j.get("metrics", {}).get("total_duration_sec", 0) for j in completed]
    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0
    
    # KB Stats
    kb_stats = _get_kb_stats()
    
    # System Health (Probes)
    health_status = _get_system_health()
    
    return {
        "total_jobs": len(all_jobs),
        "completed": len(completed),
        "failed": len(failed),
        "success_rate": f"{round(len(completed)/len(all_jobs)*100, 1)}%" if all_jobs else "0%",
        "avg_render_time_sec": avg_duration,
        "render_modes_breakdown": render_modes,
        "knowledge_base": kb_stats,
        "finance": {
            "total_est_cost_usd": round(total_cost, 2),
            "avg_cost_per_video": round(total_cost / len(completed), 4) if completed else 0
        },
        "health": health_status
    }

@app.get("/analytics/kb", tags=["Analytics"], summary="Knowledge Base retrieval stats", description="Detailed audit of KB retrieval performance, usage rates, and semantic confidence scores.")
def get_kb_analytics():
    """Deep-dive audit into KB retrieval performance and ground-truth utilization."""
    from pathlib import Path
    import json
    kb_log_path = Path("output/kb_retrievals.jsonl")
    if not kb_log_path.exists():
        return {"message": "No KB retrievals logged yet."}
    
    try:
        with open(kb_log_path, "r") as f:
            entries = [json.loads(line) for line in f if line.strip()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read KB logs: {e}")
    
    if not entries:
        return {"message": "KB log file is empty."}
        
    total = len(entries)
    used = sum(1 for e in entries if e.get("used"))
    
    by_node = {}
    by_mode = {}
    
    for e in entries:
        node = e.get("node", "unknown")
        mode = e.get("render_mode", "unknown")
        score = e.get("top_confidence", 0.0)
        
        by_node.setdefault(node, []).append(score)
        by_mode.setdefault(mode, []).append(score)
    
    return {
        "total_retrievals": total,
        "used_rate": round(used / total, 3) if total else 0,
        "mean_top_confidence": round(sum(e.get("top_confidence", 0.0) for e in entries) / total, 3) if total else 0,
        "by_node": {
            node: {
                "count": len(scores),
                "mean_confidence": round(sum(scores) / len(scores), 3),
            }
            for node, scores in by_node.items()
        },
        "by_render_mode": {
            mode: {
                "count": len(scores),
                "mean_confidence": round(sum(scores) / len(scores), 3),
            }
            for mode, scores in by_mode.items()
        },
    }

def _get_kb_stats() -> dict:
    """Helper to audit the Knowledge Base persistence layer."""
    from knowledge_manager import KNOWLEDGE_DIR
    import os
    if not os.path.exists(KNOWLEDGE_DIR):
        return {"total_fact_sheets": 0, "storage_usage_kb": 0.0}
    
    files = [f for f in os.listdir(KNOWLEDGE_DIR) if f.endswith(".json")]
    total_size = sum(os.path.getsize(os.path.join(KNOWLEDGE_DIR, f)) for f in files)
    
    return {
        "total_fact_sheets": len(files),
        "storage_usage_kb": round(total_size / 1024, 2)
    }

def _get_system_health() -> dict:
    """Lightweight connectivity probes for critical factory dependencies."""
    import requests
    import config
    
    health = {"gemma_status": "unknown", "searxng_status": "unknown"}
    
    # Probe Gemma 4 (Local LLM)
    try:
        # We check the /v1/models endpoint as it's a standard probe
        resp = requests.get(config.LOCAL_LLM_URL.replace("/v1", "/v1/models"), timeout=2)
        health["gemma_status"] = "online" if resp.status_code == 200 else "error"
    except Exception as e:
        print(f"⚠️ [health_probes] Gemma probe failed: {e}")
        health["gemma_status"] = "offline"
        
    # Probe SearXNG (Metasearch)
    try:
        resp = requests.get(config.SEARXNG_URL, timeout=2)
        health["searxng_status"] = "online" if resp.status_code == 200 else "error"
    except Exception as e:
        print(f"⚠️ [health_probes] SearXNG probe failed: {e}")
        health["searxng_status"] = "offline"
        
    return health

def _validate_image_asset(path: str):
    """
    Industrial Sentinel: Defensive guard against dangerous or invalid media.
    Prevents pipeline crashes by checking assets before compute allocation.
    """
    import os
    
    # 1. Extension Validation
    ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp'}
    ext = os.path.splitext(path)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported media type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # 2. Existence & Size Validation (if local path)
    # Note: For S3 or Remote URLs, we would pre-sign or check headers here.
    if not path.startswith(("http://", "https://")):
        if not os.path.exists(path):
            raise HTTPException(status_code=400, detail=f"Media asset not found: {path}")
            
        # Limit to 10MB to protect memory in Manim/HeyGen
        max_size_mb = 10 
        file_size_mb = os.path.getsize(path) / (1024 * 1024)
        if file_size_mb > max_size_mb:
            raise HTTPException(
                status_code=400, 
                detail=f"Media asset too large ({file_size_mb:.1f}MB). Max limit is {max_size_mb}MB."
            )
    
    return True


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
    now_iso = utcnow().isoformat() + "Z"
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

from enum import Enum

class TargetLanguage(str, Enum):
    HINDI = "hindi"
    HINGLISH = "hinglish"
    TAMIL = "tamil"
    TELUGU = "telugu"
    BENGALI = "bengali"
    MARATHI = "marathi"
    KANNADA = "kannada"
    MALAYALAM = "malayalam"


@app.post("/dub/{job_id}", response_model=DubResponse, dependencies=[SecurityDep], tags=["Operational"], summary="Dub completed job", description="Translates and re-dubs an existing completed job into a target language (hindi, tamil, etc.) using Pipeline 6.")
def dub_job(job_id: str, language: TargetLanguage = TargetLanguage.HINDI):
    """Dub a completed job into a target language."""
    try:
        # Run the dubbing pipeline (Groq + ElevenLabs + FFmpeg)
        result = run_dub_pipeline(job_id, language.value)
        
        # Convert local file path to accessible streaming URL
        video_filename = os.path.basename(result["dubbed_video_path"])
        result["dubbed_video_url"] = f"/stream/{job_id}/{video_filename}"
        
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Industrial Sentinel: Log the full error to stdout for debugging
        print(f"❌ Dubbing Pipeline Error for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))



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
    except Exception as e:
        print(f"⚠️ [health_detailed] Groq check failed: {e}")
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
        except Exception as e:
            print(f"⚠️ [timeline] Failed to parse timestamp for job: {e}")
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
        jobs[job_id]["updated_at"] = utcnow().isoformat() + "Z"
        jobs[job_id]["logs"].append({"node": "SYSTEM", "msg": "Job cancelled by operator.", "type": "warning"})
    
    _safe_save_jobs(f"cancel job ({job_id})")
    return {"job_id": job_id, "status": "cancelled"}


@app.get("/version", response_model=VersionResponse, tags=["Enterprise"], summary="Service version info", description="Retrieves the current API version, server uptime, git commit hash, and environment details.")
def get_version():
    """API version, uptime, and build info — enterprise compliance."""
    uptime_seconds = (utcnow() - _APP_START_TIME).total_seconds()
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
    except Exception as e:
        print(f"⚠️ [version] Failed to get git commit: {e}")
    
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

@app.get("/costs", response_model=CostsResponse, tags=["Analytics"], summary="API cost tracking", description="Calculates real API costs from the ledger for measured jobs, and uses average estimates for legacy jobs.")
def get_costs():
    """Aggregate API costs from the ledger and fallback estimates."""
    from cost_tracker import LedgerManager
    
    # 1. Constants for legacy estimation (averages)
    COST_PER_GROQ_CALL = 0.002
    COST_PER_ELEVENLABS_CHAR = 0.00003
    COST_PER_HEYGEN_SEC = 0.0333
    COST_PER_HIGGSFIELD_CALL = 0.10

    with _jobs_lock:
        all_jobs = list(jobs.values())
    
    completed = [j for j in all_jobs if j["status"] == "completed"]
    
    # 2. Read all job totals from the ledger file
    job_ledger_totals = {}
    path = LedgerManager.get_ledger_path()
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                for line in f:
                    entry = json.loads(line)
                    jid = entry.get("job_id")
                    if jid:
                        job_ledger_totals[jid] = job_ledger_totals.get(jid, 0.0) + entry.get("cost_usd", 0.0)
        except Exception as e:
            print(f"⚠️ Error reading cost ledger: {e}")

    job_costs = []
    total_measured = 0.0
    total_estimated = 0.0
    
    # 3. Process each completed job
    for j in completed:
        jid = j.get("job_id")
        mode = j.get("render_mode") or "auto"
        has_avatar = j.get("with_avatar", False)
        topic = j.get("topic", "Unknown")
        
        if jid in job_ledger_totals:
            # Measured job (New)
            actual = round(job_ledger_totals[jid], 6)
            total_measured += actual
            job_costs.append({
                "job_id": jid,
                "topic": topic,
                "render_mode": mode,
                "actual_cost_usd": actual,
                "estimated_cost_usd": actual,
                "cost_source": "measured"
            })
        else:
            # Legacy job (Fallback to average estimate)
            est = COST_PER_GROQ_CALL * 3
            est += COST_PER_ELEVENLABS_CHAR * 2000
            if mode == "explainer": est += COST_PER_HIGGSFIELD_CALL * 3
            if has_avatar: est += COST_PER_HEYGEN_SEC * 60  # ~60s average avatar video
            
            est = round(est, 4)
            total_estimated += est
            job_costs.append({
                "job_id": jid,
                "topic": topic,
                "render_mode": mode,
                "actual_cost_usd": 0.0,
                "estimated_cost_usd": est,
                "cost_source": "estimated"
            })
    
    # Sort by ID descending (newest first)
    job_costs.sort(key=lambda x: x["job_id"], reverse=True)
    
    total_all = total_measured + total_estimated
    count = len(completed)
    
    return {
        "total_cost_usd": round(total_all, 4),
        "total_estimated_cost_usd": round(total_all, 4), # Alias
        "completed_jobs": count,
        "avg_cost_per_video_usd": round(total_all / count, 6) if count else 0,
        "breakdown": job_costs,
        "note": f"Report contains {len(job_ledger_totals)} measured jobs and {count - len(job_ledger_totals)} legacy estimated jobs."
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
        "timestamp": utcnow().isoformat() + "Z",
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
