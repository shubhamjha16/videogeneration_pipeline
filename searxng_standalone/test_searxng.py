import requests
import sys

def test_searxng(host="http://localhost:8080"):
    print(f"📡 Testing SearXNG Standalone at {host}...")
    
    url = f"{host.rstrip('/')}/search"
    params = {
        "q": "Manim Python Animation",
        "format": "json"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("results", [])
        
        if results:
            print(f"✅ Success! Found {len(results)} results.")
            print(f"🔝 Top result: {results[0].get('title')} ({results[0].get('url')})")
        else:
            print("⚠️ No results found. Check upstream engine connectivity.")
            
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        print("\n💡 Troubleshooting:")
        print("1. Ensure Docker is running.")
        print("2. Ensure JSON format is enabled in settings.yml.")
        print(f"3. Verify you can access {url} in your browser.")

if __name__ == "__main__":
    host_arg = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
    test_searxng(host_arg)
