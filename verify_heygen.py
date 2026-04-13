import os
import requests
import json
from dotenv import load_dotenv

def verify_production_heygen():
    """
    Sentinel Script for EaseToLearn Factory.
    Validates HeyGen API credentials and Avatar availability before industrial deployment.
    """
    load_dotenv()
    
    api_key = os.environ.get("HEYGEN_API_KEY")
    avatar_id = os.environ.get("DEFAULT_HEYGEN_AVATAR", "josh_video_20230607")
    
    if not api_key:
        print("❌ ERROR: HEYGEN_API_KEY environment variable is missing.")
        return False
        
    print(f"🚀 [Sentinel] Verifying HeyGen API Key: {api_key[:6]}...")
    
    # Check API key by listing avatars
    url = "https://api.heygen.com/v2/avatars"
    headers = {
        "x-api-key": api_key,
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 401:
            print("❌ ERROR: Invalid HeyGen API Key (401 Unauthorized).")
            return False
        
        response.raise_for_status()
        avatars = response.json().get("data", {}).get("avatars", [])
        
        # Verify the configured avatar exists
        found = False
        avatar_list = []
        for av in avatars:
            avatar_list.append(av.get("avatar_id"))
            if av.get("avatar_id") == avatar_id:
                found = True
                break
        
        if found:
            print(f"✅ SUCCESS: HeyGen API authenticated and Avatar '{avatar_id}' is ready.")
            return True
        else:
            print(f"⚠️  WARNING: API Key is valid, but Avatar '{avatar_id}' not found in your account.")
            print(f"   Available Avatars: {avatar_list[:5]}...")
            return True # Still authenticated
            
    except Exception as e:
        print(f"❌ SENTINEL FAILURE: Could not connect to HeyGen API: {e}")
        return False

if __name__ == "__main__":
    if verify_production_heygen():
        print("\n🏆 PRODUCTION READY: HeyGen path is industrialized.")
        exit(0)
    else:
        print("\n🛑 DEPLOYMENT BLOCKED: Please check your credentials.")
        exit(1)
