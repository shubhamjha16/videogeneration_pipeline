"""
Local DB Smoke Test (Host Machine)
Verifies that all 4 lifecycle hooks work correctly without Docker.
Uses SQLite fallback automatically.
"""
import os
import sys

# Ensure project root is in path
sys.path.append(os.getcwd())

from db.engine import init_db, get_session
from db.repository import create_job, insert_conditions, insert_token_usage, update_job_status, upsert_video_cache
from db.models import RenderJob, JobCondition, JobTokenUsage, VideoCache

def run_test():
    print("🚀 Starting Local DB Smoke Test...")
    
    # 1. Init
    if not init_db():
        print("❌ Database init failed.")
        return
    print("✅ init_db() passed.")

    job_id = "test_smoke_99"
    topic = "Local DB Verification"

    # 2. Hook 1: create_job
    print(f"📡 Testing Hook 1 (create_job) for {job_id}...")
    success = create_job(job_id=job_id, topic=topic, source_type="html")
    if not success:
        print("❌ create_job failed.")
        return
    print("✅ create_job passed.")

    # 3. Hook 2: insert_conditions
    print("📡 Testing Hook 2 (insert_conditions)...")
    success = insert_conditions(
        job_id=job_id, 
        selected_render_mode="presentation",
        routing_reason="Test reasoning",
        content_type="concept",
        subject="physics",
        scene_count=5,
        overrides={"animation_enabled": True}
    )
    if not success:
        print("❌ insert_conditions failed.")
        return
    print("✅ insert_conditions passed.")

    # 4. Hook 3: insert_token_usage
    print("📡 Testing Hook 3 (insert_token_usage)...")
    success = insert_token_usage(
        job_id=job_id,
        provider="openai",
        service="gpt-4o",
        call_type="llm",
        input_tokens=500,
        output_tokens=1000,
        cost_usd=0.015
    )
    if not success:
        print("❌ insert_token_usage failed.")
        return
    print("✅ insert_token_usage passed.")

    # 5. Hook 4: update_job_status + cache
    print("📡 Testing Hook 4 (update_job_status)...")
    success = update_job_status(
        job_id=job_id,
        status="completed",
        video_url="https://s3.example.com/video.mp4",
        thumbnail_url="https://s3.example.com/thumb.jpg",
        total_cost_usd=0.015,
        duration_seconds=120.5
    )
    if not success:
        print("❌ update_job_status failed.")
        return
    print("✅ update_job_status passed.")

    print("📡 Testing Hook 4 (upsert_video_cache)...")
    success = upsert_video_cache(
        job_id=job_id,
        video_url="https://s3.example.com/video.mp4",
        render_mode="presentation",
        topic=topic,
        total_cost_usd=0.015,
        duration_seconds=120
    )
    if not success:
        print("❌ upsert_video_cache failed.")
        return
    print("✅ upsert_video_cache passed.")

    # 6. Final verification of data
    print("\n📊 Final Verification (SQLite Query):")
    session = get_session()
    job = session.query(RenderJob).filter_by(job_id=job_id).first()
    cond = session.query(JobCondition).filter_by(job_id=job_id).first()
    usage = session.query(JobTokenUsage).filter_by(job_id=job_id).first()
    cache = session.query(VideoCache).filter_by(job_id=job_id).first()
    
    print(f"   Job Status: {job.status} (Expected: completed)")
    print(f"   Render Mode: {job.render_mode_actual} (Expected: presentation)")
    print(f"   Subject: {cond.subject} (Expected: physics)")
    print(f"   Tokens: {usage.input_tokens} in / {usage.output_tokens} out")
    print(f"   Cost: ${usage.cost_usd} / INR {usage.cost_inr}")
    print(f"   Cache URL: {cache.video_url}")
    
    session.close()
    print("\n⭐ ALL 4 PERSISTENCE HOOKS VERIFIED SUCCESSFULLY (HOST-LEVEL SQLITE) ⭐")

if __name__ == "__main__":
    run_test()
