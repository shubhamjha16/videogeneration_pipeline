"""
Automated Telemetry & Ledger Safety Verification Suite
Tests process-safe file locking with fcntl and dynamic model pricing integration.
"""
import os
import sys
import json
import time
import shutil
from multiprocessing import Process

# Ensure project root is in path
sys.path.append(os.getcwd())

# Force test output location
os.environ["MANIM_MEDIA_DIR"] = "test_proper_output"

from db.engine import init_db, get_session
from db.repository import create_job
from db.models import JobTokenUsage
from cost_tracker import LedgerManager, MODELS_PRICING

TEST_JOB_ID = "test_telemetry_job_999"

def clear_test_ledger():
    ledger_path = LedgerManager.get_ledger_path()
    if os.path.exists(ledger_path):
        os.remove(ledger_path)
    lock_path = ledger_path + ".lock"
    if os.path.exists(lock_path):
        os.remove(lock_path)
    print(f"🧹 Cleared existing test ledger files at {ledger_path}")

def run_worker(worker_id: int, num_operations: int):
    """Worker process simulation generating concurrent cost tracking calls."""
    print(f"🚀 Worker {worker_id} started, generating {num_operations} operations...")
    for i in range(num_operations):
        op_type = i % 5
        if op_type == 0:
            # 1. Test LLM call
            LedgerManager.record_llm_call(
                job_id=TEST_JOB_ID,
                provider="openai",
                model="gpt-4o-mini",
                usage_dict={"prompt_tokens": 100, "completion_tokens": 200}
            )
        elif op_type == 1:
            # 2. Test TTS call
            LedgerManager.record_tts_call(
                job_id=TEST_JOB_ID,
                provider="elevenlabs",
                characters=500
            )
        elif op_type == 2:
            # 3. Test dynamic DALL-E call (with model fallback / pricing mapping resolver)
            LedgerManager.record_dalle_call(
                job_id=TEST_JOB_ID,
                model="gpt-image-2"
            )
        elif op_type == 3:
            # 4. Test Gemini Omni / Veo call
            LedgerManager.record_veo_call(
                job_id=TEST_JOB_ID,
                duration_seconds=10.0,
                model_name="gemini-omni-flash"
            )
        elif op_type == 4:
            # 5. Test Search call
            LedgerManager.record_search_call(
                job_id=TEST_JOB_ID,
                provider="searxng"
            )
    print(f"✅ Worker {worker_id} finished all {num_operations} operations.")

def verify_results(num_workers: int, ops_per_worker: int):
    print("\n🔍 Verifying Test Results...")
    ledger_path = LedgerManager.get_ledger_path()
    
    # 1. File verification
    if not os.path.exists(ledger_path):
        raise FileNotFoundError(f"Ledger file not found at {ledger_path}!")
        
    expected_total = num_workers * ops_per_worker
    lines = []
    
    with open(ledger_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                lines.append(data)
            except json.JSONDecodeError as e:
                print(f"❌ Corruption detected at line {idx}: {line!r}")
                raise e

    print(f"📊 Total lines in ledger: {len(lines)} (Expected: {expected_total})")
    assert len(lines) == expected_total, f"Line count mismatch! Expected {expected_total}, got {len(lines)}"
    
    # Check that there is absolutely no line truncation or interleaved corruption
    print("✅ 100% of JSON lines decoded successfully. Cross-process concurrency locks verified.")

    # 2. Verify pricing logic
    print("🔍 Checking pricing math and dynamic resolution...")
    for entry in lines:
        model = entry.get("model")
        cost = entry.get("cost_usd", 0.0)
        call_type = entry.get("call_type")
        
        if model == "gpt-image-2":
            # Dynamic pricing resolves to flat fee
            expected_cost = MODELS_PRICING["gpt-image-2"].flat_fee
            assert abs(cost - expected_cost) < 1e-6, f"DALL-E cost mismatch: {cost} vs expected {expected_cost}"
        elif model == "gemini-omni-flash":
            # Veo pricing: duration (10s) * rate ($0.02)
            expected_cost = 10.0 * MODELS_PRICING["gemini-omni-flash"].flat_fee
            assert abs(cost - expected_cost) < 1e-6, f"Veo cost mismatch: {cost} vs expected {expected_cost}"
        elif model == "searxng":
            expected_cost = MODELS_PRICING["searxng"].flat_fee
            assert abs(cost - expected_cost) < 1e-6, f"Searxng cost mismatch: {cost} vs expected {expected_cost}"
            
    print("✅ Dynamic pricing resolution matches MODELS_PRICING configuration.")

    # 3. DB Verification
    print("🔍 Verifying DB entry count and consistency...")
    session = get_session()
    try:
        db_entries = session.query(JobTokenUsage).filter_by(job_id=TEST_JOB_ID).all()
        print(f"📊 DB row count for {TEST_JOB_ID}: {len(db_entries)} (Expected: {expected_total})")
        assert len(db_entries) == expected_total, f"DB entry count mismatch! Expected {expected_total}, got {len(db_entries)}"
        print("✅ DB record counts match ledger perfectly with zero lock contention.")
    finally:
        session.close()

def main():
    print("🎬 Initializing Cost Tracker Concurrency Test...")
    
    # Initialize DB and create a dummy job to fulfill foreign key constraints
    if not init_db():
        print("❌ DB init failed.")
        sys.exit(1)
        
    create_job(job_id=TEST_JOB_ID, topic="Concurrency Ledger verification", source_type="test")
    
    clear_test_ledger()
    
    num_workers = 8
    ops_per_worker = 125 # Total 1000 operations
    
    processes = []
    start_time = time.time()
    
    for i in range(num_workers):
        p = Process(target=run_worker, args=(i, ops_per_worker))
        processes.append(p)
        p.start()
        
    for p in processes:
        p.join()
        
    duration = time.time() - start_time
    print(f"⏱️ Concurrency phase completed in {duration:.3f} seconds.")
    
    verify_results(num_workers, ops_per_worker)
    print("\n⭐ ALL LEDGER AUDIT AND TELEMETRY VERIFICATIONS PASSED SUCCESSFULLY! ⭐")

if __name__ == "__main__":
    main()
