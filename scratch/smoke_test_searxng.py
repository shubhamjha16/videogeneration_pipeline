import sys
import os
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from searxng_tool import search_searxng
import config

def test_searxng():
    load_dotenv()
    
    print(f"Testing SearXNG integration...")
    print(f"URL: {config.SEARXNG_URL}")
    
    # We use a broad term to test connectivity
    query = "Manim Python library"
    results = search_searxng(query, limit=3)
    
    if results:
        print(f"✅ Success! Found {len(results)} results.")
        for res in results:
            print(f"- {res['title']} ({res['url']})")
    else:
        print(f"❌ Failed to get results. Check if SearXNG is running at {config.SEARXNG_URL}")
        print("Note: If you are in a restricted environment, this test might fail even if the code is correct.")

if __name__ == "__main__":
    test_searxng()
