"""
Knowledge Vector Store — Standalone Factory Brain
Handles semantic indexing and retrieval of SearXNG research using FastEmbed.
100% Standalone: No API key or remote embedding service required.
"""

import os
import lancedb
import json
import pandas as pd
from typing import List, Dict, Any, Optional
import config

# Industrial Storage Path
VECTOR_DB_PATH = os.path.join(config.BASE_DIR, "factory_vector_db")

class VectorStore:
    _instance = None
    _db = None
    _table = None
    _model = None

    def __init__(self):
        if not os.path.exists(VECTOR_DB_PATH):
            os.makedirs(VECTOR_DB_PATH, exist_ok=True)
            
        self.db = lancedb.connect(VECTOR_DB_PATH)
        self.table_name = "knowledge_nodes"
        
        # Initialize or Load table
        try:
            self.table = self.db.open_table(self.table_name)
        except:
            self.table = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_model(self):
        """Lazy load the FastEmbed model (saves memory/disk until needed)."""
        if self._model is None:
            try:
                from fastembed import TextEmbedding
                # BGE-small is industry standard for low-resource environments (~100MB)
                # Industrial Hardening: Use a persistent cache directory in the workspace
                # to prevent ONNXRuntimeErrors when OS temp folders are cleared.
                model_cache = os.path.join(VECTOR_DB_PATH, "models")
                os.makedirs(model_cache, exist_ok=True)
                
                print(f"🧠 Vector Store: Loading local models from {model_cache}...")
                self._model = TextEmbedding(
                    model_name="BAAI/bge-small-en-v1.5",
                    cache_dir=model_cache
                )
            except ImportError:
                print("⚠️ Vector Store: fastembed library missing. pip install fastembed")
                return None
            except Exception as e:
                print(f"❌ Vector Store: Model initialization failed: {e}")
                return None
        return self._model

    def _get_embedding(self, text: str) -> List[float]:
        """Generate high-fidelity embeddings locally without an API key."""
        model = self._get_model()
        if not model:
            return [0.0] * 384 # Fallback
            
        try:
            # FastEmbed returns a generator of embeddings
            embeddings = list(model.embed([text]))
            return embeddings[0].tolist()
        except Exception as e:
            print(f"⚠️ Vector Store: Local embedding failed: {e}")
            return [0.0] * 384

    def add_fact_sheet(self, topic: str, fact_sheet: Dict[str, Any]):
        """Index a distilled fact sheet into the local vector space."""
        summary = fact_sheet.get("summary", "")
        if not summary:
            return

        embedding = self._get_embedding(summary)
        
        data = [{
            "vector": embedding,
            "topic": topic,
            "summary": summary,
            "key_facts": json.dumps(fact_sheet.get("key_facts", [])),
            "metadata": json.dumps({
                "visual_metaphors": fact_sheet.get("visual_metaphors", []),
                "source": "searxng_distillation",
                "engine": "fastembed_local"
            })
        }]
        
        if self.table is None:
            self.table = self.db.create_table(self.table_name, data=data)
        else:
            # Avoid duplicate topics
            existing = self.table.search().where(f"topic = '{topic}'").to_list()
            if not existing:
                self.table.add(data)
            else:
                print(f"ℹ️ Vector Store: Topic '{topic}' already in semantic memory.")

    def search_knowledge(self, query: str, limit: int = 3, min_score: float = 0.7) -> List[Dict[str, Any]]:
        """Perform 100% offline semantic search."""
        if self.table is None:
            return []

        query_embedding = self._get_embedding(query)
        
        results = (
            self.table.search(query_embedding)
            .limit(limit)
            .to_list()
        )
        
        hits = []
        for r in results:
            dist = r.get("_distance", 1.0)
            similarity = 1.0 - (dist / 2.0)
            
            if similarity >= min_score:
                hits.append({
                    "topic": r["topic"],
                    "summary": r["summary"],
                    "key_facts": json.loads(r["key_facts"]),
                    "metadata": json.loads(r["metadata"]),
                    "similarity": round(similarity, 3)
                })
        
        return hits

# Global Helper Integration
def index_research(topic: str, fact_sheet: Dict[str, Any]):
    try:
        vs = VectorStore.get_instance()
        vs.add_fact_sheet(topic, fact_sheet)
    except Exception as e:
        print(f"⚠️ Vector Store: Failed to index research: {e}")

def retrieve_related_research(query: str) -> List[Dict[str, Any]]:
    try:
        vs = VectorStore.get_instance()
        return vs.search_knowledge(query)
    except Exception as e:
        print(f"⚠️ Vector Store: Retrieval error: {e}")
        return []
