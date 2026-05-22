"""
Database persistence layer for the EaseToLearn Video Factory.

Provides SQLAlchemy ORM models and a clean repository pattern
for writing job lifecycle data to MySQL (etl_video_generation).

Usage:
    from db.engine import init_db
    from db.repository import create_job, update_job_status

Architecture:
    - Sync SQLAlchemy 2.0 + PyMySQL (matches existing threading.Thread model)
    - Dual-write: JSONL ledger stays, DB is additive
    - Fail-safe: DB errors log warnings but never crash the pipeline
"""

from db.engine import get_session, init_db
