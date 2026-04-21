import os
import sys
import json
import time
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import autonomous_graph
from autonomous_graph import research_node, TonyState
import config

def test_research_resilience():
    print("🧪 Starting Research Resilience Test...")
    
    # Mock state with a research request
    state: TonyState = {
        "job_id": "test_resilience_123",
        "topic": "Resilience Engineering",
        "search_queries": ["What is circuit breaking in AI?"],
        "search_results": []
    }
    
    # Force a failure URL in config
    original_url = config.SEARXNG_URL
    config.SEARXNG_URL = "http://unreachable.local:9999"
    
    print(f"📡 Mocking SEARCH outage with URL: {config.SEARXNG_URL}")
    
    try:
        # Run the node
        start_t = time.time()
        new_state = research_node(state)
        duration = time.time() - start_t
        
        print(f"⏱️ Node Execution Time: {duration:.2f}s")
        
        # VERIFICATIONS
        # 1. Topic should still be there
        assert new_state["topic"] == "Resilience Engineering"
        
        # 2. Search queries should be cleared (to prevent loops)
        assert len(new_state["search_queries"]) == 0
        
        # 3. Search results should be empty but NOT crash the system
        assert isinstance(new_state["search_results"], list)
        
        print("✅ SUCCESS: Research Node completed gracefully despite technical failure.")
        print("📋 Verify the terminal output above for the '⚠️ SearXNG Connection Failed' log.")
        
    except Exception as e:
        print(f"❌ FAILURE: Research Node crashed! {e}")
        sys.exit(1)
    finally:
        config.SEARXNG_URL = original_url

if __name__ == "__main__":
    test_research_resilience()
