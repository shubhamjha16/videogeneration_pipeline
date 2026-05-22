import os
import sys

# Ensure project root is in PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set a mock operations webhook for testing purposes (logs to standard output if not set)
os.environ["OPERATIONS_SLACK_WEBHOOK"] = os.environ.get("OPERATIONS_SLACK_WEBHOOK", "")
os.environ["MONTHLY_BUDGET_LIMIT_USD"] = "50.00"

from utils.telemetry_alerts import (
    alert_pipeline_failure,
    check_monthly_budget,
    alert_low_thirdparty_credits,
    calculate_cumulative_spend
)

def run_telemetry_smoke_test():
    print("=" * 60)
    print("🔔 RUNNING TELEMETRY ALERTS & TELEMETRY SMOKE TEST")
    print("=" * 60)
    
    # 1. Simulate Pipeline Failure Alert
    print("\n1. Simulating a render pipeline failure...")
    alert_pipeline_failure(
        job_id="test-job-9999",
        topic="Introductory Quantum Computing Lesson",
        error_msg="ElevenLabsError: API key depletion (Code 401)",
        sunk_cost=0.4520
    )
    
    # 2. Simulate Low API Key Credits Alert
    print("\n2. Simulating a low third-party credit alert...")
    alert_low_thirdparty_credits(
        provider="ElevenLabs",
        current_balance=2450,
        threshold=5000
    )
    
    # 3. Simulate Budget Limit Evaluation
    # We will temporarily fake some cost records in a mock file
    print("\n3. Evaluating mock budget limits...")
    mock_ledger = "output/cost_records_mock.jsonl"
    os.environ["COST_LEDGER_PATH"] = mock_ledger
    
    # Write mock costs exceeding 80% threshold ($42 out of $50)
    import json
    with open(mock_ledger, "w", encoding="utf-8") as f:
        # 8 entries of $5.50
        for i in range(8):
            f.write(json.dumps({"job_id": f"job-{i}", "cost_usd": 5.50}) + "\n")
            
    print("   [Ledger Created] Spend is currently $44.00 (88% of $50.00 budget)")
    check_monthly_budget()
    
    # Exceed limit ($55 out of $50)
    with open(mock_ledger, "a", encoding="utf-8") as f:
        f.write(json.dumps({"job_id": "job-exceed", "cost_usd": 11.00}) + "\n")
        
    print("   [Ledger Updated] Spend is currently $55.00 (110% of $50.00 budget)")
    check_monthly_budget()
    
    # Clean up mock file
    if os.path.exists(mock_ledger):
        os.remove(mock_ledger)
        
    print("\n✅ Smoke test finished successfully!")

if __name__ == "__main__":
    run_telemetry_smoke_test()
