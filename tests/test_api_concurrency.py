import os
os.environ["FACTORY_API_KEY"] = "your_factory_key"

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import threading
import time
import uuid
from typing import List

from api_bridge import app, jobs
from caching.redis_client import get_cache
from db.engine import get_session
from db.models import RenderJob

client = TestClient(app)

# Helper function to fire a request in a separate thread
def fire_render_request(results: List[dict], idempotency_key: str, topic: str):
    headers = {
        "X-API-Key": "your_factory_key",
        "Idempotency-Key": idempotency_key,
        "Content-Type": "application/json"
    }
    payload = {
        "topic": topic,
        "html": "<p>Geometry concept explanation.</p>",
        "render_mode": "explainer",
        "video_type": "educational"
    }
    try:
        response = client.post("/render", json=payload, headers=headers)
        results.append({
            "status_code": response.status_code,
            "data": response.json() if response.status_code == 200 else {}
        })
    except Exception as e:
        results.append({"error": str(e)})


def test_concurrent_idempotency_redis_active():
    """
    Test enqueuing requests with matching idempotency keys concurrently.
    Verifies that the atomic SET NX logic prevents double-rendering when Redis is online.
    """
    # 1. Clear jobs memory
    with jobs._lock:
        jobs.clear()

    # 2. Mock active Redis Cache with a thread-safe set_nx simulator
    mock_redis = {}
    redis_lock = threading.Lock()
    
    def mock_set_nx(key, val, ttl_seconds):
        with redis_lock:
            if key in mock_redis:
                return False
            mock_redis[key] = val
            return True

    def mock_get(key):
        with redis_lock:
            return mock_redis.get(key)

    mock_cache = MagicMock()
    mock_cache.available = True
    mock_cache.set_nx = mock_set_nx
    mock_cache.get = mock_get

    idempotency_key = f"test-idemp-redis-{uuid.uuid4()}"
    topic = f"Concurrency Topic Redis {uuid.uuid4()}"

    threads = []
    results = []

    # Mock the singleton cache connection
    with patch("api_bridge.get_cache", return_value=mock_cache), \
         patch("caching.redis_client.get_cache", return_value=mock_cache), \
         patch("api_bridge._load_jobs", return_value=jobs), \
         patch("api_bridge._save_jobs", return_value=True), \
         patch.object(jobs, "_redis_active", False), \
         patch.object(jobs, "_local_jobs", {}):
         
        # Fire 10 concurrent threads trigger requests at once
        for _ in range(10):
            t = threading.Thread(target=fire_render_request, args=(results, idempotency_key, topic))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Assert that all 10 requests completed successfully (returning 200)
        for res in results:
            assert "error" not in res
            assert res["status_code"] == 200

        # Ensure only ONE job_id is mapped in our mock redis cache
        lock_key = f"idempotency:idempotency:render:"
        val = [v for k, v in mock_redis.items() if k.startswith("idempotency:")]
        assert len(val) == 1
        winner_job_id = val[0]

        # Ensure exactly one job is present in the jobs store
        assert len(jobs) == 1
        assert winner_job_id in jobs


def test_concurrent_idempotency_redis_inactive_postgres_fallback():
    """
    Test enqueuing requests concurrently when Redis is offline.
    Verifies that the PostgreSQL advisory lock/slot enqueuing logic prevents duplicate triggers.
    """
    # 1. Clear jobs memory
    with jobs._lock:
        jobs.clear()

    # 2. Mock offline Redis Cache
    mock_cache = MagicMock()
    mock_cache.available = False

    idempotency_key = f"test-idemp-pg-{uuid.uuid4()}"
    topic = f"Concurrency Topic Postgres {uuid.uuid4()}"

    threads = []
    results = []

    # Mock the singleton cache connection to simulate Redis outage
    with patch("api_bridge.get_cache", return_value=mock_cache), \
         patch("caching.redis_client.get_cache", return_value=mock_cache), \
         patch("api_bridge._load_jobs", return_value=jobs), \
         patch("api_bridge._save_jobs", return_value=True), \
         patch.object(jobs, "_redis_active", False), \
         patch.object(jobs, "_local_jobs", {}):
         
        # Fire 5 concurrent requests at once
        for _ in range(5):
            t = threading.Thread(target=fire_render_request, args=(results, idempotency_key, topic))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Assert that all requests completed successfully
        for res in results:
            assert "error" not in res
            assert res["status_code"] == 200

        # Query the local SQLite database directly to verify enqueued jobs for this topic
        session = get_session()
        db_jobs = session.query(RenderJob).filter(RenderJob.topic == topic).all()
        session.close()

        # Ensure exactly ONE job record was created in the database for this topic context
        assert len(db_jobs) == 1
        assert db_jobs[0].status == "queued"

        # Ensure exactly one job is tracked in the memory jobs store
        assert len(jobs) == 1
        assert db_jobs[0].job_id in jobs
