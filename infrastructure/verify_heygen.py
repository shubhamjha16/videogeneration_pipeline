import os
import sys
import requests
from dotenv import load_dotenv

# Add current dir to path to import config if needed
sys.path.append(os.getcwd())

def verify_heygen_api():
    """Sentinel script to verify HeyGen API connectivity and authorization."""
    load_dotenv()
    
    api_key = os.environ.get("HEYGEN_API_KEY")
    if not api_key:
        print("❌ HEYGEN_API_KEY not found in environment!")
        return False
    
    print(f"📡 Testing HeyGen API Connectivity (Key: {api_key[:4]}...{api_key[-4:]})")
    
    # We test the v1 video_status endpoint with a dummy ID to check auth
    url = "https://api.heygen.com/v1/video_status.get?video_id=dummy_id"
    headers = {
        "x-api-key": api_key,
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        # We expect a 400 or a specific error message if the key is valid but ID is wrong
        # If the key is invalid, we'll likely get a 401/403
        if response.status_code == 401 or response.status_code == 403:
            print(f"❌ AUTHENTICATION FAILED (Status {response.status_code})")
            print(f"Response: {response.text}")
            return False
            
        print(f"✅ API Reachable (Status {response.status_code})")
        data = response.json()
        if "error" in data and "invalid_api_key" in str(data["error"]).lower():
            print("❌ Invalid API Key detected in response body.")
            return False
            
        print("🚀 HeyGen API Sentinel: Success. Credentials accepted.")
        return True
        
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False

if __name__ == "__main__":
    success = verify_heygen_api()
    sys.exit(0 if success else 1)
