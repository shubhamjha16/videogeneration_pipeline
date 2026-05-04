import os
import json
import logging
import hashlib
from typing import Optional, Any
try:
    import redis
except ImportError:
    redis = None

import config

# Industrial Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FactoryCache")

class Cache:
    """
    Industrial Abstraction for Persistent Caching.
    Supports graceful degradation: If Redis library or server is unavailable, 
    all operations fail silently so the pipeline continues.
    """
    def __init__(self, url: str):
        if not redis:
            logger.warning("⚠️ Cache: 'redis' library not installed. Operating in pass-through mode.")
            self.available = False
            return

        try:
            self.client = redis.from_url(

                url,
                socket_connect_timeout=2,
                socket_timeout=2,
                decode_responses=True,
                retry_on_timeout=False,
            )
            # Connectivity Probe
            self.client.ping()
            self.available = True
            logger.info(f"🚀 Cache: Connected to Redis at {url}")
        except redis.RedisError as e:
            logger.warning(f"⚠️ Cache: Redis unavailable ({e}). Operating in pass-through mode.")
            self.available = False

    def get(self, key: str) -> Optional[Any]:
        if not self.available:
            return None
        try:
            raw = self.client.get(key)
            return json.loads(raw) if raw else None
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.warning(f"⚠️ Cache Get failed for {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl_seconds: int) -> bool:
        if not self.available:
            return False
        try:
            self.client.setex(key, ttl_seconds, json.dumps(value))
            return True
        except (redis.RedisError, TypeError) as e:
            logger.warning(f"⚠️ Cache Set failed for {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        if not self.available:
            return False
        try:
            return bool(self.client.delete(key))
        except redis.RedisError as e:
            logger.warning(f"⚠️ Cache Delete failed: {e}")
            return False

# ── Singleton Initialization ──────────────────────────────────────────

_cache_instance: Optional[Cache] = None

def get_cache() -> Cache:
    """Lazy initializer for the global Cache singleton."""
    global _cache_instance
    if _cache_instance is None:
        # Default to localhost for dev, but allow override via env
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _cache_instance = Cache(redis_url)
    return _cache_instance

# ── Key Generators ───────────────────────────────────────────────────

def generate_idempotency_key(payload: dict, render_mode: str, overrides: dict = None) -> str:
    """Create a unique key for a job request. Includes overrides to prevent cache collisions."""
    # Ensure stable sorting of keys for consistent hashing
    data = {"p": payload, "m": render_mode}
    if overrides:
        data["o"] = overrides
        
    canonical = json.dumps(data, sort_keys=True)
    h = hashlib.sha256(canonical.encode()).hexdigest()
    return f"idempotency:render:{h}"

def generate_llm_cache_key(model: str, system: str, user: str, temperature: float) -> str:
    """Create a unique key for an LLM completion."""
    parts = {
        "m": model,
        "s": system,
        "u": user,
        "t": round(temperature, 2)
    }
    canonical = json.dumps(parts, sort_keys=True)
    h = hashlib.sha256(canonical.encode()).hexdigest()
    return f"llm:v1:{h}"
