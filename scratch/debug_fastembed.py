import os
import sys
from fastembed import TextEmbedding

# Add current dir to path to import config
sys.path.append(os.getcwd())
import config

VECTOR_DB_PATH = os.path.join(config.BASE_DIR, "factory_vector_db")
model_cache = os.path.join(VECTOR_DB_PATH, "models")

print(f"Testing FastEmbed with cache_dir: {model_cache}")

try:
    model = TextEmbedding(
        model_name="BAAI/bge-small-en-v1.5",
        cache_dir=model_cache
    )
    print("✅ Model loaded successfully")
    
    embeddings = list(model.embed(["test query"]))
    print(f"✅ Embedding generated: {len(embeddings[0])} dimensions")
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()
