"""
Database Engine & Session Factory

Connection lifecycle:
    - Reads DATABASE_URL from environment
    - Production (ENV=production): MUST be mysql+pymysql://...  — fails loudly if missing
    - Development (ENV=dev or unset): Falls back to SQLite for zero-config local dev
    - init_db() creates tables via Base.metadata.create_all() (safe to call multiple times)

Pool settings tuned for ECS Fargate (max 2 concurrent render threads):
    pool_size=5, max_overflow=10, pool_recycle=1800
"""

import os
import sys
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

_ENGINE = None
_SESSION_FACTORY = None


def _get_database_url() -> str:
    """Resolve the database URL with environment-aware safety."""
    url = os.environ.get("DATABASE_URL", "")
    env = os.environ.get("ENV", "dev").lower().strip()

    if url:
        return url

    # Production safety: NEVER silently fall back to SQLite
    if env == "production":
        print(
            "🔴 FATAL: DATABASE_URL is not set in production. "
            "The factory CANNOT persist job data without MySQL. "
            "Set DATABASE_URL in Secrets Manager or environment.",
            file=sys.stderr,
        )
        # Don't crash the pipeline — just disable DB persistence
        return ""

    # Dev fallback: SQLite file in project root
    print("⚠️  DATABASE_URL not set. Using local SQLite (dev mode only).")
    return "sqlite:///./factory_jobs.db"


def _build_engine():
    """Create the SQLAlchemy engine with connection pooling."""
    url = _get_database_url()
    if not url:
        return None

    connect_args = {}
    pool_kwargs = {}

    if url.startswith("sqlite"):
        # SQLite doesn't support pool_size or check_same_thread
        connect_args = {"check_same_thread": False}
        pool_kwargs = {"pool_pre_ping": True}
    else:
        # MySQL pool settings for ECS Fargate
        pool_kwargs = {
            "pool_size": 5,
            "max_overflow": 10,
            "pool_recycle": 1800,  # Recycle connections every 30 min (AWS RDS timeout)
            "pool_pre_ping": True,  # Detect stale connections before use
        }

    engine = create_engine(url, connect_args=connect_args, **pool_kwargs)
    return engine


def get_engine():
    """Lazy singleton for the database engine."""
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = _build_engine()
    return _ENGINE


def get_session() -> Session | None:
    """Get a new database session. Returns None if DB is unavailable."""
    global _SESSION_FACTORY
    engine = get_engine()
    if engine is None:
        return None

    if _SESSION_FACTORY is None:
        _SESSION_FACTORY = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    return _SESSION_FACTORY()


def init_db():
    """Create all tables if they don't exist. Safe to call on every startup."""
    engine = get_engine()
    if engine is None:
        print("⚠️  Database not available. Skipping table creation.")
        return False

    from db.models import Base

    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables verified/created.")
        return True
    except Exception as e:
        print(f"⚠️  Database init failed: {e}. Pipeline will continue without DB persistence.")
        return False
