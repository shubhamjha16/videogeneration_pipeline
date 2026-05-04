"""
SearXNG Tool — Metasearch Wrapper
Connects to a SearXNG instance to gather information/assets.
Used by Director for fact-finding and Healer for error fixes.
"""

import requests
import json
from typing import List, Dict, Any
import config

def search_searxng(query: str, categories: str = "general", limit: int = None, job_id: str = None) -> List[Dict[str, Any]]:
    """
    Perform a search query against the configured SearXNG instance.
    
    Args:
        query: The search term
        categories: comma-separated list of categories (e.g. "general,science,it")
        limit: Max number of results to return (defaults to config.SEARXNG_RESULTS_LIMIT)
        job_id: Optional job attribution for cost tracking
        
    Returns:
        List of result dictionaries: [{"title", "content", "url", "engine"}]
    """
    if not config.SEARXNG_URL:
        print("⚠️ SEARXNG_URL not configured. Search disabled.")
        return []

    limit = limit or config.SEARXNG_RESULTS_LIMIT
    
    params = {
        "q": query,
        "format": "json",
        "categories": categories,
        "language": "en"
    }
    
    try:
        # Record cost if job_id is provided
        try:
            from cost_tracker import LedgerManager
            LedgerManager.record_search_call(job_id)
        except Exception as e:
            print(f"⚠️ Failed to log search cost: {e}")

        # Ensure the URL ends with /search
        base_url = config.SEARXNG_URL.rstrip("/")
        if not base_url.endswith("/search"):
            base_url += "/search"
            
        print(f"🔍 Searching SearXNG [{categories}]: '{query}'...")
        
        # Industrial Retry Strategy: Exponential Backoff
        import time
        max_retries = config.SEARXNG_RETRIES
        timeout = config.SEARXNG_TIMEOUT
        
        last_error = None
        for attempt in range(max_retries):
            try:
                response = requests.get(base_url, params=params, timeout=timeout)
                response.raise_for_status()
                
                data = response.json()
                raw_results = data.get("results", [])
                
                # Format and truncate
                formatted = []
                for res in raw_results[:limit]:
                    formatted.append({
                        "title": res.get("title", ""),
                        "content": res.get("content", ""), # This is the snippet/summary
                        "url": res.get("url", ""),
                        "engine": res.get("engine", "unknown")
                    })
                    
                return formatted
            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) # 1s, 2s, 4s...
                    print(f"   ⚠️ Search Attempt {attempt+1} failed. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                continue

        # If we reach here, all retries failed
        print(f"⚠️ SearXNG Research Offline after {max_retries} attempts ({last_error}). Falling back to Internal Knowledge.")
        return []
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON from SearXNG: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected Search Error: {e}")
        return []

if __name__ == "__main__":
    # Quick Test
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    # Override for local test if needed
    # config.SEARXNG_URL = "http://localhost:8080"
    
    test_query = "Manim Render Error: 'VMobject' object has no attribute 'set_text'"
    results = search_searxng(test_query)
    
    print(f"\n--- Results for '{test_query}' ---")
    if not results:
        print("No results found or instance unreachable.")
    for i, r in enumerate(results, 1):
        print(f"{i}. {r['title']}\n   {r['url']}\n   Snippet: {r['content'][:100]}...\n")
