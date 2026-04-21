"""
SearXNG Tool — Metasearch Wrapper
Connects to a SearXNG instance to gather information/assets.
Used by Director for fact-finding and Healer for error fixes.
"""

import requests
import json
from typing import List, Dict, Any
import config

def search_searxng(query: str, categories: str = "general", limit: int = None) -> List[Dict[str, Any]]:
    """
    Perform a search query against the configured SearXNG instance.
    
    Args:
        query: The search term
        categories: comma-separated list of categories (e.g. "general,science,it")
        limit: Max number of results to return (defaults to config.SEARXNG_RESULTS_LIMIT)
        
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
        # Ensure the URL ends with /search
        base_url = config.SEARXNG_URL.rstrip("/")
        if not base_url.endswith("/search"):
            base_url += "/search"
            
        print(f"🔍 Searching SearXNG [{categories}]: '{query}'...")
        response = requests.get(base_url, params=params, timeout=10)
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
        
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        # Industrial Hardening: Silence technical failures to prevent pipeline crashes.
        # The Orchestrator will fallback to 'Internal Knowledge' if this returns [].
        print(f"⚠️ SearXNG Research Offline ({e}). Falling back to Internal Knowledge.")
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
