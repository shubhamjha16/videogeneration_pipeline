import sys
import os
import time
from caching.redis_client import get_cache

print("🔍 Phase 1: Redis Client Validation")

# Test 1: Set/Get/Delete
print("\n[Test 1] Basic Operations...")
cache = get_cache()
if cache.available:
    success = cache.set("test_key", {"val": 123}, ttl_seconds=60)
    print(f"   Set successful: {success}")
    
    val = cache.get("test_key")
    print(f"   Get result: {val}")
    
    deleted = cache.delete("test_key")
    print(f"   Delete successful: {deleted}")
    
    val_after = cache.get("test_key")
    print(f"   Get after delete: {val_after} (Expected: None)")
else:
    print("   ⚠️ Redis not running locally. Skipping functional tests.")

# Test 2: Graceful Degradation
print("\n[Test 2] Graceful Degradation...")
# We simulate a failure by pointing to a non-existent port
os.environ["REDIS_URL"] = "redis://localhost:9999/0"
from caching.redis_client import Cache
bad_cache = Cache("redis://localhost:9999/0")

print(f"   Bad cache available: {bad_cache.available} (Expected: False)")
print(f"   Bad cache get('foo'): {bad_cache.get('foo')} (Expected: None)")
print(f"   Bad cache set('foo', 'bar'): {bad_cache.set('foo', 'bar', 10)} (Expected: False)")

print("\n✅ Phase 1 Validation Complete.")
