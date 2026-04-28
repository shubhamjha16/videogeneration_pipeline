import pytest
from unittest.mock import MagicMock, patch
def test_ledger_sync_stateful():
    import autonomous_graph
    # Test that ledger is synchronized correctly without duplication
    state = {
        "job_id": "test_job_123",
        "ledger": {"tokens": 100, "chars": 500}
    }
    
    mock_job = {"metrics": {}, "logs": [], "progress": 0}
    mock_api = MagicMock()
    mock_api.jobs = {"test_job_123": mock_job}
    mock_api._jobs_lock = MagicMock()
    mock_api._jobs_lock.__enter__ = MagicMock()
    mock_api._jobs_lock.__exit__ = MagicMock()
    
    with patch("autonomous_graph._api_bridge_refs", mock_api):
        # First log
        autonomous_graph._log_progress(state, "DIRECTOR", "Start")
        assert mock_job["ledger"]["tokens"] == 100
        assert mock_job["metrics"]["tokens"] == 100
        
        # Second log with updated ledger
        state["ledger"]["tokens"] += 50
        autonomous_graph._log_progress(state, "VISION", "Next")
        
        # Ensure it's not 100 + 150 = 250 (which was the bug)
        # It should be exactly the current state: 150
        assert mock_job["ledger"]["tokens"] == 150
        assert mock_job["metrics"]["tokens"] == 150

def test_progress_mapping():
    import autonomous_graph
    state = {"job_id": "job1"}
    mock_job = {"metrics": {}, "logs": []}
    mock_api = MagicMock()
    mock_api.jobs = {"job1": mock_job}
    
    with patch("autonomous_graph._api_bridge_refs", mock_api):
        autonomous_graph._log_progress(state, "DIRECTOR", "test")
        assert mock_job["progress"] == 15
        
        autonomous_graph._log_progress(state, "DEPLOY", "test")
        assert mock_job["progress"] == 95
