"""
Knowledge Vector Store — Organizational Knowledge Layer (Qdrant)

Handles semantic indexing and retrieval of research, lesson scripts,
curriculum documents, teacher notes, and SearXNG research results.

Backend: Qdrant (centralized vector database)
Embeddings: FastEmbed local BGE-small-en-v1.5 (100% offline, no API key)

Graceful degradation:
    - If Qdrant is unreachable, operations log warnings and return empty results
    - The main pipeline continues unaffected (knowledge retrieval is additive)
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional

import config

logger = logging.getLogger("video_factory.knowledge")

# ── Qdrant connection settings ─────────────────────────────────────────────
QDRANT_HOST    = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT    = int(os.environ.get("QDRANT_PORT", "6333"))
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", None)  # None = no auth (local)
QDRANT_HTTPS   = os.environ.get("QDRANT_HTTPS", "false").lower() == "true"

# ── Collection settings ────────────────────────────────────────────────────
COLLECTION_NAME = "knowledge_nodes"
VECTOR_DIM      = 384  # BGE-small-en-v1.5 output dimension

# ── Local embedding model cache ────────────────────────────────────────────
VECTOR_DB_PATH = os.path.join(config.BASE_DIR, "factory_vector_db")


class VectorStore:
    _instance = None

    def __init__(self):
        import threading
        self._load_lock = threading.Lock()
        self._model = None
        self._client = None
        os.makedirs(VECTOR_DB_PATH, exist_ok=True)
        self._init_client()
        self._ensure_collection()

    # ── Singleton ──────────────────────────────────────────────────────────

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Qdrant client ──────────────────────────────────────────────────────

    def _init_client(self):
        """Connect to the Qdrant instance (local or cloud)."""
        try:
            from qdrant_client import QdrantClient
            self._client = QdrantClient(
                host=QDRANT_HOST,
                port=QDRANT_PORT,
                api_key=QDRANT_API_KEY,
                https=QDRANT_HTTPS,
                timeout=10,
            )
            logger.info("✅ Qdrant: Connected to %s:%d", QDRANT_HOST, QDRANT_PORT)
        except ImportError:
            logger.warning("⚠️  Qdrant: 'qdrant-client' not installed. pip install qdrant-client>=1.9.0")
            self._client = None
        except Exception as e:
            logger.warning("⚠️  Qdrant: Connection failed (%s). Knowledge retrieval disabled.", e)
            self._client = None

    def _ensure_collection(self):
        """Idempotently create the knowledge_nodes collection if it doesn't exist."""
        if not self._client:
            return
        try:
            from qdrant_client.models import Distance, VectorParams
            existing = [c.name for c in self._client.get_collections().collections]
            if COLLECTION_NAME not in existing:
                self._client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
                )
                logger.info("✅ Qdrant: Created collection '%s' (dim=%d)", COLLECTION_NAME, VECTOR_DIM)
            else:
                logger.info("✅ Qdrant: Collection '%s' already exists.", COLLECTION_NAME)
        except Exception as e:
            logger.warning("⚠️  Qdrant: Failed to ensure collection: %s", e)

    # ── Embedding model ────────────────────────────────────────────────────

    def _get_model(self):
        """Lazy-load the FastEmbed local embedding model."""
        with self._load_lock:
            if self._model is None:
                try:
                    from fastembed import TextEmbedding
                    model_cache = os.path.abspath(os.path.join(VECTOR_DB_PATH, "models"))
                    os.makedirs(model_cache, exist_ok=True)
                    self._heal_model_symlinks(model_cache)
                    self._model = TextEmbedding(
                        model_name="BAAI/bge-small-en-v1.5",
                        cache_dir=model_cache,
                        providers=["CPUExecutionProvider"],
                    )
                    logger.info("🧠 FastEmbed: BGE-small-en-v1.5 loaded.")
                except ImportError:
                    logger.warning("⚠️  FastEmbed not installed. pip install fastembed>=0.2.0")
                except Exception as e:
                    logger.warning("⚠️  FastEmbed model init failed: %s", e)
        return self._model

    def _heal_model_symlinks(self, cache_dir: str):
        """Fix broken ONNX symlinks created by huggingface_hub on Mac/Linux."""
        import shutil
        for root, dirs, files in os.walk(cache_dir):
            for f in files:
                if f.endswith(".onnx"):
                    f_path = os.path.join(root, f)
                    if os.path.islink(f_path):
                        target = os.path.realpath(f_path)
                        if os.path.exists(target):
                            os.remove(f_path)
                            shutil.copy2(target, f_path)

    def _get_embedding(self, text: str) -> List[float]:
        """Generate a local embedding vector using FastEmbed BGE-small."""
        model = self._get_model()
        if not model:
            return [0.0] * VECTOR_DIM
        try:
            embeddings = list(model.embed([text]))
            return embeddings[0].tolist()
        except Exception as e:
            logger.warning("⚠️  Embedding failed: %s", e)
            return [0.0] * VECTOR_DIM

    # ── Write ──────────────────────────────────────────────────────────────

    def add_fact_sheet(self, topic: str, fact_sheet: Dict[str, Any]):
        """Index a distilled SearXNG fact sheet into the Qdrant knowledge base."""
        if not self._client:
            return

        summary = fact_sheet.get("summary", "")
        if not summary:
            return

        embedding = self._get_embedding(summary)

        try:
            from qdrant_client.models import PointStruct
            import uuid as _uuid

            # Use deterministic UUID from topic to prevent duplicate entries
            point_id = str(_uuid.uuid5(_uuid.NAMESPACE_URL, f"etl:knowledge:{topic}"))

            payload = {
                "topic": topic,
                "summary": summary,
                "key_facts": fact_sheet.get("key_facts", []),
                "visual_metaphors": fact_sheet.get("visual_metaphors", []),
                "source": "searxng_distillation",
                "engine": "fastembed_bge_small",
            }

            self._client.upsert(
                collection_name=COLLECTION_NAME,
                points=[PointStruct(id=point_id, vector=embedding, payload=payload)],
            )
            logger.info("📚 Qdrant: Indexed topic '%s' (id=%s)", topic, point_id)

        except Exception as e:
            logger.warning("⚠️  Qdrant: Failed to index '%s': %s", topic, e)

    # ── Read ───────────────────────────────────────────────────────────────

    def search_knowledge(
        self,
        query: str,
        limit: int = 3,
        min_score: float = 0.7,
        node: str = "unknown",
        job_id: str = "unknown",
        render_mode: str = "unknown",
    ) -> List[Dict[str, Any]]:
        """Semantic search against the organizational knowledge base."""
        if not self._client:
            return []

        query_embedding = self._get_embedding(query)

        try:
            results = self._client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=min_score,
            )
        except Exception as e:
            logger.warning("⚠️  Qdrant: Search failed: %s", e)
            return []

        hits = []
        for r in results:
            p = r.payload or {}
            hits.append({
                "topic": p.get("topic", ""),
                "summary": p.get("summary", ""),
                "key_facts": p.get("key_facts", []),
                "metadata": {
                    "visual_metaphors": p.get("visual_metaphors", []),
                    "source": p.get("source", ""),
                    "engine": p.get("engine", ""),
                },
                "similarity": round(r.score, 3),
            })

        # ── KB Telemetry audit log ─────────────────────────────────────────
        from datetime import datetime, timezone
        from pathlib import Path

        KB_LOG_PATH = Path("output/kb_retrievals.jsonl")
        os.makedirs("output", exist_ok=True)

        top_conf  = hits[0]["similarity"] if hits else 0.0
        mean_conf = sum(h["similarity"] for h in hits) / len(hits) if hits else 0.0

        log_entry = {
            "timestamp":      datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
            "job_id":         job_id,
            "node":           node,
            "render_mode":    render_mode,
            "query":          query[:200],
            "num_results":    len(hits),
            "top_confidence": top_conf,
            "mean_confidence": mean_conf,
            "used":           len(hits) > 0,
        }
        try:
            with open(KB_LOG_PATH, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception:
            pass

        return hits


# ── Module-level helper functions (public API — unchanged signature) ────────

def index_research(topic: str, fact_sheet: Dict[str, Any]):
    """Index a new SearXNG fact sheet into the organizational knowledge base."""
    try:
        VectorStore.get_instance().add_fact_sheet(topic, fact_sheet)
    except Exception as e:
        logger.warning("⚠️  Vector Store: Failed to index research: %s", e)


def retrieve_related_research(
    query: str,
    node: str = "unknown",
    job_id: str = "unknown",
    render_mode: str = "unknown",
) -> List[Dict[str, Any]]:
    """Retrieve semantically related knowledge from the Qdrant knowledge base."""
    try:
        return VectorStore.get_instance().search_knowledge(
            query, node=node, job_id=job_id, render_mode=render_mode
        )
    except Exception as e:
        logger.warning("⚠️  Vector Store: Retrieval error: %s", e)
        return []
