import os
import sys
import json
import time
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Add project root to path to read config values
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config

# Configuration
API_BASE = "http://localhost:8000"
API_KEY  = os.environ.get("FACTORY_API_KEY", "etl_factory_prod_8291_secret")
CALLBACK_PORT = 9090
CALLBACK_URL = f"http://localhost:{CALLBACK_PORT}/api/v1/factory/callback"

# Global state to capture the webhook callback
received_payload = {}
callback_event = threading.Event()

class MockSpringBootHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        global received_payload
        if self.path == "/api/v1/factory/callback":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            # Respond with 200 OK to the factory api
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "received"}')
            
            # Parse callback payload
            try:
                received_payload = json.loads(post_data.decode('utf-8'))
                print("\n🔔 [SPRING BOOT EMULATOR] Webhook callback received successfully!")
                print(json.dumps(received_payload, indent=2))
            except Exception as e:
                print(f"❌ Failed to parse callback JSON: {e}")
            finally:
                callback_event.set()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Mute standard HTTP logging to keep output clean
        return

def start_mock_server():
    server = HTTPServer(('localhost', CALLBACK_PORT), MockSpringBootHandler)
    print(f"🖥️  Started Mock Spring Boot Backend on {CALLBACK_URL}")
    server.serve_forever()

def run_handshake():
    # 1. Start the Spring Boot emulator in a daemon thread
    t = threading.Thread(target=start_mock_server, daemon=True)
    t.start()
    time.sleep(1) # Allow port binding

    # 2. Trigger render job
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "topic": "Handshake Integration Validation",
        "html": "<html><body><h2>Lesson 1: Handshake</h2><p>Checking endpoints.</p></body></html>",
        "render_mode": "notes", # Quickest rendering mode for verification
        "video_type": "educational",
        "webhook_url": CALLBACK_URL
    }

    print("\n🚀 [1] Submitting render request to Factory API...")
    try:
        resp = requests.post(f"{API_BASE}/render", json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        job_id = data.get("job_id")
        print(f"    ✅ Job Queued successfully! ID: {job_id}")
    except Exception as e:
        print(f"    ❌ Connection failed to Factory API: {e}")
        print("    👉 Ensure the Uvicorn server is running locally: python3 -m uvicorn api_bridge:app --reload")
        return

    # 3. Poll for progress or wait for webhook
    print("\n⏳ [2] Waiting for Webhook callback from the Factory (2 minutes max)...")
    wait_success = callback_event.wait(timeout=120)

    if not wait_success:
        print("⏰ [TIMEOUT] Webhook did not trigger within 120 seconds.")
        # Attempt to pull status manually as fallback diagnostic
        try:
            r = requests.get(f"{API_BASE}/status/{job_id}", headers=headers, timeout=5)
            print("📊 Status endpoint diagnostics:")
            print(json.dumps(r.json(), indent=2))
        except Exception:
            pass
        return

    # 4. Assert callback integrity
    print("\n📊 [3] Validating Webhook Payload schema...")
    status = received_payload.get("status")
    if status == "completed":
        print("✅ INTEGRATION SUCCESSFUL!")
        print(f"    - Job ID: {received_payload.get('job_id')}")
        print(f"    - Status: {received_payload.get('status')}")
        print(f"    - Video URL: {received_payload.get('video_url')}")
        print(f"    - Progress: {received_payload.get('progress')}%")
    else:
        print("❌ INTEGRATION TERMINATED WITH FAILURE:")
        print(f"    - Status: {received_payload.get('status')}")
        print(f"    - Error Logged: {received_payload.get('error')}")

if __name__ == "__main__":
    print("🧪 TONY AI FACTORY - END-TO-END HANDSHAKE VERIFICATION")
    print("=====================================================")
    run_handshake()
