import os
import shutil
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add root to sys.path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

def setup_test_folder():
    """Create dummy folders for hygiene testing."""
    media_root = "test_output"
    os.makedirs(media_root, exist_ok=True)
    
    # 1. Stale Job (30 hours old)
    stale_id = "test_stale"
    stale_path = os.path.join(media_root, f"job_{stale_id}")
    os.makedirs(stale_path, exist_ok=True)
    with open(os.path.join(stale_path, "raw.mp4"), "w") as f: f.write("dummy data")
    
    # 2. Recent Job (1 hour old)
    recent_id = "test_recent"
    recent_path = os.path.join(media_root, f"job_{recent_id}")
    os.makedirs(recent_path, exist_ok=True)
    with open(os.path.join(recent_path, "raw.mp4"), "w") as f: f.write("dummy data")
    
    # 3. Orphan Job (not in jobs.json)
    orphan_id = "test_orphan"
    orphan_path = os.path.join(media_root, f"job_{orphan_id}")
    os.makedirs(orphan_path, exist_ok=True)
    
    # Create mock jobs.json
    now = datetime.utcnow()
    stale_time = (now - timedelta(hours=30)).isoformat() + "Z"
    recent_time = (now - timedelta(hours=1)).isoformat() + "Z"
    
    mock_jobs = {
        stale_id: {"job_id": stale_id, "created_at": stale_time},
        recent_id: {"job_id": recent_id, "created_at": recent_time}
    }
    
    return media_root, mock_jobs

def run_hygiene_test(media_root, all_jobs):
    """Simplified version of the api_bridge hygiene logic for testing."""
    print(f"🧼 [Test] Starting hygiene pass on {media_root}...")
    now = datetime.utcnow()
    retention_hours = 24
    purged = []
    
    for item in os.listdir(media_root):
        item_path = os.path.join(media_root, item)
        if not os.path.isdir(item_path) or not item.startswith("job_"):
            continue
            
        job_id = item.replace("job_", "")
        should_purge = False
        
        if job_id not in all_jobs:
            should_purge = True
            print(f"   [Purge] Orphan: {item}")
        else:
            created_at_str = all_jobs[job_id]["created_at"].replace("Z", "")
            created_at = datetime.fromisoformat(created_at_str)
            age = now - created_at
            if (age.total_seconds() / 3600) > retention_hours:
                should_purge = True
                print(f"   [Purge] Stale ({round(age.total_seconds()/3600, 1)}h): {item}")
        
        if should_purge:
            shutil.rmtree(item_path)
            purged.append(item)
    return purged

if __name__ == "__main__":
    media_root, mock_jobs = setup_test_folder()
    print(f"📁 Created test folders in {media_root}")
    
    purged = run_hygiene_test(media_root, mock_jobs)
    
    # Verify
    print("\n📊 Results:")
    remnants = os.listdir(media_root)
    print(f"   Remaining: {remnants}")
    
    assert "job_test_recent" in remnants
    assert "job_test_stale" not in remnants
    assert "job_test_orphan" not in remnants
    
    print("\n✅ Hygiene Logic Verified: Stale and Orphan folders were purged. Recent folder was kept.")
    
    # Cleanup
    shutil.rmtree(media_root)
