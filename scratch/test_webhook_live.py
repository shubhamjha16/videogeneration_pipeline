import subprocess
import time
import requests
import json
import os

print("\n" + "="*80)
print("⚙️ STARTING LIVE LOCAL END-TO-END WEBHOOK INTEGRATION TEST")
print("="*80)

# Set environment variables for the subprocess
env = os.environ.copy()
env["WEBHOOK_URL"] = "http://localhost:8000/test/webhook/receiver"
env["FACTORY_API_KEY"] = "etl_factory_prod_8291_secret"
env["PORT"] = "8000"

print("\n🚀 Starting api_bridge Uvicorn server on port 8000 in the background...")
# Run Uvicorn in the background
server_process = subprocess.Popen(
    ["venv/bin/python3", "-m", "uvicorn", "api_bridge:app", "--host", "127.0.0.1", "--port", "8000"],
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

# Wait for server to boot
print("⏳ Waiting for server to initialize (4 seconds)...")
time.sleep(4)

print("\n📤 Sending POST /webhook/test to trigger the webhook loop...")
headers = {
    "X-Api-Key": "etl_factory_prod_8291_secret",
    "Content-Type": "application/json"
}

try:
    resp = requests.post("http://localhost:8000/webhook/test", headers=headers, timeout=10)
    print(f"📥 Received Response Status: {resp.status_code}")
    print("📥 Response Body:")
    print(json.dumps(resp.json(), indent=2))
    
    # Wait another 2 seconds to let the server print the webhook receiver callback stdout
    time.sleep(2)
    
except Exception as e:
    print(f"❌ HTTP request failed: {e}")

finally:
    print("\n🛑 Shutting down background Uvicorn server...")
    server_process.terminate()
    try:
        server_process.wait(timeout=5)
        print("✅ Server process terminated cleanly.")
    except subprocess.TimeoutExpired:
        server_process.kill()
        print("⚠️ Server process force killed.")
        
    # Read server logs to check if the webhook receiver printed the payload
    print("\n📋 Capturing Uvicorn server stdout logs:")
    logs, _ = server_process.communicate()
    
    # Filter and highlight the webhook receiver print logs
    has_webhook_log = False
    for line in logs.splitlines():
        if "MOCK WEBHOOK" in line or "RECEIVED" in line or "test-ping" in line:
            print(f"  🔥 [SERVER LOG] {line}")
            has_webhook_log = True
        elif has_webhook_log and len(line.strip()) > 0 and not "INFO" in line:
            print(f"  🔥 [SERVER LOG] {line}")
            
    print("\n" + "="*80)
    print("✅ LIVE WEBHOOK TEST COMPLETED")
    print("="*80 + "\n")
