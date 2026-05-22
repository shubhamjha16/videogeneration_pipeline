"""
SQLAlchemy ORM Models — etl_video_generation database

These models match the corrected CREATE TABLE statements exactly.
Column names, types, and constraints are 1:1 with the MySQL schema.

Tables:
    render_jobs      — Primary job lifecycle tracker
    job_conditions   — Director routing decision + detected signals
    job_token_usage  — Per-API-call cost tracking (mirrors LedgerEntry)
    video_cache      — Completed videos for Spring Boot lookups
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Enum,
    DateTime,
    Numeric,
    SmallInteger,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class RenderJob(Base):
    """Primary job lifecycle tracker — maps to `render_jobs` table."""

    __tablename__ = "render_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), nullable=False, unique=True, index=True)
    question_id = Column(Integer, nullable=True)
    topic = Column(String(500), nullable=True)
    source_type = Column(String(50), nullable=True)  # html|json|markdown|composite
    render_mode_requested = Column(String(50), nullable=True)
    render_mode_actual = Column(
        Enum("manim", "presentation", "explainer", "heygen", "notes", "user_generated_video",
             name="render_mode_enum"),
        nullable=True,
    )
    with_avatar = Column(SmallInteger, nullable=False, default=0)
    avatar_type = Column(String(30), nullable=True)
    priority = Column(Integer, nullable=False, default=100)
    callback_url = Column(String(500), nullable=True)
    status = Column(
        Enum("queued", "processing", "completed", "failed", "cancelled",
             name="job_status_enum"),
        nullable=False,
        default="queued",
    )
    current_node = Column(String(50), nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    final_video_url = Column(String(500), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    error_node = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    total_cost_usd = Column(Numeric(10, 4), nullable=True)
    duration_seconds = Column(Numeric(10, 2), nullable=True)
    queued_at = Column(DateTime, nullable=True, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<RenderJob job_id={self.job_id} status={self.status}>"


class JobCondition(Base):
    """Director routing decision + detected signals — maps to `job_conditions` table."""

    __tablename__ = "job_conditions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), nullable=False, unique=True, index=True)
    question_id = Column(Integer, nullable=True)

    # Spring Boot hint flags (sent via RenderOverrides)
    has_image_in_body = Column(SmallInteger, nullable=False, default=0)
    has_math_formula = Column(SmallInteger, nullable=False, default=0)
    has_equation = Column(SmallInteger, nullable=False, default=0)
    needs_animation = Column(SmallInteger, nullable=False, default=0)
    has_diagram = Column(SmallInteger, nullable=False, default=0)

    # Factory-detected signals (from html_parser + director_agent)
    has_mcq = Column(SmallInteger, nullable=False, default=0)
    has_derivation = Column(SmallInteger, nullable=False, default=0)
    content_type = Column(String(30), nullable=True)  # mcq|numerical|concept|case_study
    subject = Column(String(50), nullable=True)  # medical|physics|maths|...
    scene_count = Column(Integer, nullable=True)

    # Routing outcome
    selected_render_mode = Column(
        Enum("manim", "presentation", "explainer", "heygen", "notes", "user_generated_video",
             name="condition_render_mode_enum"),
        nullable=False,
    )
    routing_reason = Column(Text, nullable=True)
    uses_existing_image = Column(SmallInteger, nullable=False, default=0)
    source_image_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=True, default=datetime.utcnow)

    def __repr__(self):
        return f"<JobCondition job_id={self.job_id} mode={self.selected_render_mode}>"


class JobTokenUsage(Base):
    """Per-API-call cost tracking — maps to `job_token_usage` table."""

    __tablename__ = "job_token_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), nullable=False, index=True)
    provider = Column(String(50), nullable=False)  # anthropic|google|groq|openai|...
    service = Column(String(100), nullable=False)  # Model name: claude-4-7-opus, dall-e-3, tts
    call_type = Column(String(20), nullable=True)  # llm|audio|video|image|search|vision
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    tts_characters = Column(Integer, nullable=True)
    image_count = Column(Integer, nullable=True)
    api_calls = Column(Integer, nullable=True, default=1)
    from_cache = Column(SmallInteger, nullable=False, default=0)
    cost_usd = Column(Numeric(10, 4), nullable=True)
    cost_inr = Column(Numeric(10, 4), nullable=True)
    created_at = Column(DateTime, nullable=True, default=datetime.utcnow)

    def __repr__(self):
        return f"<JobTokenUsage job_id={self.job_id} provider={self.provider} cost=${self.cost_usd}>"


class VideoCache(Base):
    """Completed videos for Spring Boot lookups — maps to `video_cache` table."""

    __tablename__ = "video_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), nullable=False, unique=True, index=True)
    purpose = Column(
        Enum("question_explanation", "marketing", "course_intro", "announcement",
             "affiliate", "tutorial", "other",
             name="video_purpose_enum"),
        nullable=False,
        default="question_explanation",
    )
    related_entity_type = Column(String(50), nullable=True)
    related_entity_id = Column(Integer, nullable=True)
    render_mode = Column(String(50), nullable=False)
    title = Column(String(255), nullable=True)
    status = Column(
        Enum("pending", "rendering", "ready", "failed",
             name="video_cache_status_enum"),
        nullable=False,
        default="pending",
    )
    video_url = Column(String(500), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    total_cost_usd = Column(Numeric(10, 4), nullable=True)
    total_cost_inr = Column(Numeric(10, 4), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<VideoCache job_id={self.job_id} status={self.status}>"
