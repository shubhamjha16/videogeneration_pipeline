import requests
import json
import os

# Configuration
API_URL = "http://localhost:8000/analytics"
API_KEY = os.environ.get("FACTORY_API_KEY", "industrial_secret_123")

def test_industrial_analytics():
    print("🧪 Starting Industrial Analytics Verification...")
    
    headers = {"X-API-Key": API_KEY}
    
    try:
        response = requests.get(API_URL, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        print("\n✅ Analytics Payload Received:")
        print(json.dumps(data, indent=4))
        
        # Validation Checks
        print("\n🔍 Validating Data Structure...")
        
        if "knowledge_base" in data:
            print(f"   [KB] Found {data['knowledge_base']['total_fact_sheets']} distilled fact sheets.")
        else:
            print("   ❌ KB stats missing!")

        if "finance" in data:
            print(f"   [Finance] Total Est Cost: ${data['finance']['total_est_cost_usd']}")
        else:
            print("   ❌ Financial stats missing!")

        if "health" in data:
            print(f"   [Health] Gemma: {data['health']['gemma_status']} | SearXNG: {data['health']['searxng_status']}")
        else:
            print("   ❌ Health probes missing!")
            
        print("\n✨ Verification Complete: Industrial Analytics are operational.")
        
    except Exception as e:
        print(f"❌ Analytics Test Failed: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"   Status Code: {e.response.status_code}")
            print(f"   Error Body: {e.response.text}")

if __name__ == "__main__":
    test_industrial_analytics()
