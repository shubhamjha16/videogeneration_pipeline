"""
Data Access Layer (Repository Pattern) for the Video Factory.

Provides clean, high-level functions for PostgreSQL persistence.
All functions include try/except blocks to ensure that database 
failures never crash the primary video generation pipeline.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from db.engine import get_session
from db.models import RenderJob, JobCondition, JobTokenUsage, VideoCache

logger = logging.getLogger("video_factory.db")

def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def create_job(
    job_id: str,
    topic: str,
    source_type: str = "html",
    render_mode_requested: Optional[str] = None,
    priority: int = 100,
    callback_url: Optional[str] = None,
    with_avatar: bool = False,
    avatar_type: Optional[str] = None,
    question_id: Optional[int] = None
) -> bool:
    """Hook 1: Record new job submission."""
    session = get_session()
    if not session:
        return False
    
    try:
        job = RenderJob(
            job_id=job_id,
            topic=topic,
            source_type=source_type,
            render_mode_requested=render_mode_requested,
            priority=priority,
            callback_url=callback_url,
            with_avatar=1 if with_avatar else 0,
            avatar_type=avatar_type,
            question_id=question_id,
            status="queued",
            queued_at=utcnow()
        )
        session.add(job)
        session.commit()
        return True
    except Exception as e:
        logger.warning(f"DB Error (create_job): {e}")
        session.rollback()
        return False
    finally:
        session.close()

def insert_conditions(
    job_id: str,
    selected_render_mode: str,
    routing_reason: Optional[str] = None,
    content_type: Optional[str] = None,
    subject: Optional[str] = None,
    scene_count: Optional[int] = None,
    overrides: Optional[Dict[str, Any]] = None,
    question_id: Optional[int] = None,
    has_diagram: bool = False
) -> bool:
    """Hook 2: Record Director's routing decision and detected signals."""
    session = get_session()
    if not session:
        return False
    
    try:
        overrides = overrides or {}
        condition = JobCondition(
            job_id=job_id,
            question_id=question_id,
            has_image_in_body=1 if overrides.get("has_static_image") else 0,
            has_math_formula=1 if overrides.get("has_formula") else 0,
            has_equation=1 if overrides.get("has_equation") else 0,
            needs_animation=1 if overrides.get("animation_enabled") is not False else 0,
            has_diagram=1 if has_diagram else 0,
            has_mcq=1 if content_type == "mcq" else 0,
            has_derivation=1 if "derivation" in (routing_reason or "").lower() else 0,
            content_type=content_type,
            subject=subject,
            scene_count=scene_count,
            selected_render_mode=selected_render_mode,
            routing_reason=routing_reason,
            created_at=utcnow()
        )
        session.add(condition)
        
        # Also update the actual render mode in the main job table
        job = session.query(RenderJob).filter(RenderJob.job_id == job_id).first()
        if job:
            job.render_mode_actual = selected_render_mode
            job.started_at = utcnow()
            job.status = "processing"
            
        session.commit()
        return True
    except Exception as e:
        logger.warning(f"DB Error (insert_conditions): {e}")
        session.rollback()
        return False
    finally:
        session.close()

def insert_token_usage(
    job_id: str,
    provider: str,
    service: str,
    call_type: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_usd: float = 0.0,
    from_cache: bool = False,
    tts_characters: int = 0,
    image_count: int = 0
) -> bool:
    """Hook 3: Record per-API-call cost and token usage."""
    session = get_session()
    if not session:
        return False
    
    try:
        usage = JobTokenUsage(
            job_id=job_id,
            provider=provider,
            service=service,
            call_type=call_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=Decimal(str(cost_usd)),
            cost_inr=Decimal(str(cost_usd)) * Decimal("83.5"),
            from_cache=1 if from_cache else 0,
            tts_characters=tts_characters,
            image_count=image_count,
            created_at=utcnow()
        )
        session.add(usage)
        session.commit()
        return True
    except Exception as e:
        logger.warning(f"DB Error (insert_token_usage): {e}")
        session.rollback()
        return False
    finally:
        session.close()

def update_job_status(
    job_id: str,
    status: str,
    video_url: Optional[str] = None,
    thumbnail_url: Optional[str] = None,
    error_node: Optional[str] = None,
    error_message: Optional[str] = None,
    total_cost_usd: float = 0.0,
    duration_seconds: float = 0.0
) -> bool:
    """Hook 4: Update final job status and metrics."""
    session = get_session()
    if not session:
        return False
    
    try:
        job = session.query(RenderJob).filter(RenderJob.job_id == job_id).first()
        if job:
            job.status = status
            job.final_video_url = video_url
            job.thumbnail_url = thumbnail_url
            job.error_node = error_node
            job.error_message = error_message
            job.total_cost_usd = Decimal(str(total_cost_usd))
            job.duration_seconds = Decimal(str(duration_seconds))
            job.completed_at = utcnow()
            
            session.commit()
            return True
        return False
    except Exception as e:
        logger.warning(f"DB Error (update_job_status): {e}")
        session.rollback()
        return False
    finally:
        session.close()

def upsert_video_cache(
    job_id: str,
    video_url: str,
    render_mode: str,
    topic: str,
    thumbnail_url: Optional[str] = None,
    duration_seconds: int = 0,
    total_cost_usd: float = 0.0,
    status: str = "ready",
    purpose: str = "question_explanation"
) -> bool:
    """Hook 4 (Secondary): Ensure video is in cache for Spring Boot lookup."""
    session = get_session()
    if not session:
        return False
    
    try:
        cache_entry = session.query(VideoCache).filter(VideoCache.job_id == job_id).first()
        if not cache_entry:
            cache_entry = VideoCache(job_id=job_id, purpose=purpose)
            session.add(cache_entry)
        
        cache_entry.video_url = video_url
        cache_entry.thumbnail_url = thumbnail_url
        cache_entry.render_mode = render_mode
        cache_entry.title = topic
        cache_entry.duration_seconds = int(duration_seconds)
        cache_entry.total_cost_usd = Decimal(str(total_cost_usd))
        cache_entry.total_cost_inr = Decimal(str(total_cost_usd)) * Decimal("83.5")
        cache_entry.status = status
        cache_entry.updated_at = utcnow()
        
        session.commit()
        return True
    except Exception as e:
        logger.warning(f"DB Error (upsert_video_cache): {e}")
        session.rollback()
        return False
    finally:
        session.close()


def get_active_job_by_topic(topic: str) -> Optional[str]:
    """Helper to find any currently active enqueued or processing job for this topic context."""
    session = get_session()
    if not session:
        return None
    try:
        job = session.query(RenderJob).filter(
            RenderJob.topic == topic,
            RenderJob.status.in_(["queued", "processing"])
        ).first()
        return job.job_id if job else None
    except Exception as e:
        logger.warning(f"DB Error (get_active_job_by_topic): {e}")
        return None
    finally:
        session.close()


def get_job_by_id(job_id: str) -> Optional[dict]:
    """Helper to fetch render job state details directly from Postgres."""
    session = get_session()
    if not session:
        return None
    try:
        job = session.query(RenderJob).filter(RenderJob.job_id == job_id).first()
        if job:
            return {
                "job_id": job.job_id,
                "topic": job.topic,
                "status": job.status,
                "video_url": job.final_video_url,
                "thumbnail_url": job.thumbnail_url,
                "error_node": job.error_node,
                "error_message": job.error_message,
                "duration_seconds": float(job.duration_seconds) if job.duration_seconds else 0.0,
                "total_cost_usd": float(job.total_cost_usd) if job.total_cost_usd else 0.0,
            }
        return None
    except Exception as e:
        logger.warning(f"DB Error (get_job_by_id): {e}")
        return None
    finally:
        session.close()


import threading
_sqlite_fallback_lock = threading.Lock()

def acquire_active_job_slot_pg(
    topic: str,
    job_id: str,
    source_type: str = "html",
    render_mode: Optional[str] = None,
    with_avatar: bool = False,
    avatar_type: Optional[str] = None,
    callback_url: Optional[str] = None
) -> tuple[bool, Optional[str]]:
    """
    Atomically check if an active job for the topic exists, and if not, create one.
    Uses PostgreSQL session-level advisory locking (or normal transaction checks for SQLite fallback).
    Returns (acquired, active_job_id).
    """
    import zlib
    from sqlalchemy import text
    
    # Calculate a unique 32-bit signed integer hash for the topic
    lock_id = zlib.crc32(f"active_job_slot:{topic}".encode('utf-8')) & 0x7fffffff
    
    session = get_session()
    if not session:
        return False, None
        
    try:
        # SQLite dialect check
        if session.bind.dialect.name == "sqlite":
            with _sqlite_fallback_lock:
                active_job = session.query(RenderJob).filter(
                    RenderJob.topic == topic,
                    RenderJob.status.in_(["queued", "processing"])
                ).first()
                if active_job:
                    return False, active_job.job_id
                    
                job = RenderJob(
                    job_id=job_id,
                    topic=topic,
                    source_type=source_type,
                    render_mode_requested=render_mode or "auto",
                    with_avatar=1 if with_avatar else 0,
                    avatar_type=avatar_type,
                    callback_url=callback_url,
                    status="queued",
                    queued_at=utcnow()
                )
                session.add(job)
                session.commit()
                return True, job_id
            
        # PostgreSQL Advisory Lock path
        locked = session.execute(text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": lock_id}).scalar()
        if not locked:
            # Another concurrent request is currently enqueuing for this topic
            return False, None
            
        try:
            active_job = session.query(RenderJob).filter(
                RenderJob.topic == topic,
                RenderJob.status.in_(["queued", "processing"])
            ).first()
            if active_job:
                return False, active_job.job_id
                
            job = RenderJob(
                job_id=job_id,
                topic=topic,
                source_type=source_type,
                render_mode_requested=render_mode or "auto",
                with_avatar=1 if with_avatar else 0,
                avatar_type=avatar_type,
                callback_url=callback_url,
                status="queued",
                queued_at=utcnow()
            )
            session.add(job)
            session.commit()
            return True, job_id
        finally:
            session.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": lock_id})
            session.commit()
            
    except Exception as e:
        logger.warning(f"DB Error (acquire_active_job_slot_pg): {e}")
        session.rollback()
        return False, None
    finally:
        session.close()


