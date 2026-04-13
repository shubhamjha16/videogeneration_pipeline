import os
import json
import time
import sys

# Add current dir to sys.path
sys.path.append(os.getcwd())

from api_bridge import _load_jobs, JOBS_FILE

def verify_persistence_fallback():
    print("🛠️  Testing Persistence Fallback...")
    
    # 1. Create a corrupted jobs.json (invalid JSON)
    with open(JOBS_FILE, "w", encoding='utf-8') as f:
        f.write("{ invalid_json: ,,, }")
    
    print(f"   - Created corrupted {JOBS_FILE}")
    
    # 2. Call _load_jobs()
    result = _load_jobs()
    
    # 3. Verify fresh dict returned
    if result == {}:
        print("   ✅ Step 1: Returned empty dict on corruption.")
    else:
        print(f"   ❌ Step 1 FAILED: Returned {result} instead of {{}}")
        sys.exit(1)
        
    # 4. Verify corrupted file was renamed (search for .corrupt_ in root)
    import glob
    corrupt_files = glob.glob(f"{JOBS_FILE}.corrupt_*")
    if len(corrupt_files) > 0:
        print(f"   ✅ Step 2: Corrupted file was archived to {corrupt_files[0]}")
    else:
        print("   ❌ Step 2 FAILED: No corrupted archive found.")
        sys.exit(1)
    
    print("🎉 PERSISTENCE VERIFICATION SUCCESSFUL.")

if __name__ == "__main__":
    verify_persistence_fallback()
