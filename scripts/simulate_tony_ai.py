import requests
import json
import time
import threading
import sys
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

# Force absolute paths for imports if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
FACTORY_URL = "http://localhost:8000"
API_KEY = os.environ.get("FACTORY_API_KEY", "industrial_secret_123")
WEBHOOK_PORT = 9090
WEBHOOK_PATH = "/tony-ai/callback"
WEBHOOK_URL = f"http://localhost:{WEBHOOK_PORT}{WEBHOOK_PATH}"

class MockTonyAIBackend(BaseHTTPRequestHandler):
    """Mock Spring Boot server to receive webhooks."""
    def do_POST(self):
        if self.path == WEBHOOK_PATH:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            payload = json.loads(post_data.decode('utf-8'))
            
            print(f"\n🔔 [WEBHOOK RECEIVED BY TONY AI]")
            print(f"   Job ID: {payload.get('job_id')}")
            print(f"   Status: {payload.get('status')}")
            print(f"   Video URL: {payload.get('video_url')}")
            print(f"   Error: {payload.get('error') or 'None'}")
            
            self.send_response(200)
            self.end_headers()
            
            # SIGNAL: Job is done
            if payload.get('status') in ['completed', 'failed']:
                self.server.job_done = True

def run_mock_server(server):
    print(f"🚀 Mock Tony AI Server listening on port {WEBHOOK_PORT}...")
    server.serve_forever()

def simulate_handshake():
    print("🤝 Starting Industrial Handshake Simulation...")
    
    # 1. Start Mock Server in background
    mock_server = HTTPServer(('localhost', WEBHOOK_PORT), MockTonyAIBackend)
    mock_server.job_done = False
    server_thread = threading.Thread(target=run_mock_server, args=(mock_server,), daemon=True)
    server_thread.start()
    
    # 2. Prepare Render Request
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    payload = {
        "topic": "The Physics of Integration Handshakes",
        "html": "<html><body><h1>Simulation Test</h1><p>Testing the 2nd layer research loop.</p></body></html>",
        "render_mode": "presentation",
        "video_type": "educational",
        "webhook_url": WEBHOOK_URL
    }
    
    # 3. Submit Job
    print(f"📤 Submitting Render Request to {FACTORY_URL}/render...")
    try:
        response = requests.post(f"{FACTORY_URL}/render", json=payload, headers=headers)
        response.raise_for_status()
        job_info = response.json()
        job_id = job_info['job_id']
        print(f"✅ Job Created: {job_id}")
    except Exception as e:
        print(f"❌ Failed to submit job: {e}")
        mock_server.shutdown()
        return

    # 4. Wait for Webhook
    print("⏳ Waiting for industrial pipeline to complete (and webhook to fire)...")
    timeout = 600 # 10 minutes
    start_time = time.time()
    
    try:
        while not mock_server.job_done:
            if time.time() - start_time > timeout:
                print("❌ TIMEOUT: Webhook not received within 10 minutes.")
                break
            
            # Poll status for progress reporting
            status_resp = requests.get(f"{FACTORY_URL}/status/{job_id}", headers=headers)
            if status_resp.status_code == 200:
                s = status_resp.json()
                print(f"   [POLL] Status: {s['status']} | Progress: {s['progress']}% | Current: {s['current_step']}", end='\r')
            
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n🛑 Simulation interrupted by user.")
    
    print("\n🏁 Simulation Finished.")
    mock_server.shutdown()

if __name__ == "__main__":
    simulate_handshake()
