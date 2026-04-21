import requests
import os
import sys
import subprocess

# Configuration
API_URL = "http://localhost:8000/render"
API_KEY = os.environ.get("FACTORY_API_KEY", "industrial_secret_123")

def setup_test_files():
    print("📂 Setting up test media files...")
    # 1. Valid file
    with open("scratch/valid.png", "wb") as f:
        f.write(b"fake image content")
    
    # 2. Invalid extension
    with open("scratch/danger.exe", "wb") as f:
        f.write(b"fake malware content")
        
    # 3. Massive file (15MB)
    try:
        subprocess.run(["dd", "if=/dev/zero", "of=scratch/massive.jpg", "bs=1m", "count=15"], check=True)
    except Exception as e:
        print(f"⚠️ Could not create massive file via dd: {e}")

def cleanup_test_files():
    print("🧹 Cleaning up test files...")
    for f in ["scratch/valid.png", "scratch/danger.exe", "scratch/massive.jpg"]:
        if os.path.exists(f):
            os.remove(f)

def run_test_case(name, image_path, expected_status):
    print(f"\n🧪 Test Case: {name}")
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    payload = {
        "topic": f"Testing {name}",
        "html": "<html><body>test</body></html>",
        "image_path": image_path
    }
    
    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        if response.status_code == expected_status:
            print(f"   ✅ SUCCESS: Received expected status {expected_status}")
            if expected_status == 400:
                print(f"   📋 Error Detail: {response.json().get('detail')}")
        else:
            print(f"   ❌ FAILURE: Expected {expected_status}, got {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")

if __name__ == "__main__":
    try:
        setup_test_files()
        
        # Scenario 1: Non-existent file
        run_test_case("Missing File", "scratch/does_not_exist.png", 400)
        
        # Scenario 2: Invalid extension
        run_test_case("Invalid Extension", "scratch/danger.exe", 400)
        
        # Scenario 3: Massive file
        run_test_case("Massive File", "scratch/massive.jpg", 400)
        
        # Scenario 4: Valid file
        run_test_case("Valid File", "scratch/valid.png", 200)
        
    finally:
        cleanup_test_files()
