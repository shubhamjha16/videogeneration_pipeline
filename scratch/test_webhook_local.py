import sys
import os
# Add root workspace directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from fastapi.testclient import TestClient


# Mock the environment to point webhook target back to the local test receiver
os.environ["WEBHOOK_URL"] = "http://testserver/test/webhook/receiver"
os.environ["FACTORY_API_KEY"] = "etl_factory_prod_8291_secret"

from api_bridge import app

client = TestClient(app)

print("\n" + "="*80)
print("🤖 RUNNING OFFLINE END-TO-END WEBHOOK INTEGRATION TEST")
print("="*80)

# Simulate firing the connectivity test endpoint
print("\n📤 Triggering POST /webhook/test via FastAPI TestClient...")
headers = {
    "X-Api-Key": "etl_factory_prod_8291_secret",
    "Content-Type": "application/json"
}

# The test client will execute /webhook/test, which will POST to http://testserver/test/webhook/receiver.
# FastAPI's TestClient will automatically intercept and route this request back to the same app!
response = client.post("/webhook/test", headers=headers)

print(f"\n📥 Response Status Code: {response.status_code}")
print("📥 Response Body:")
print(json.dumps(response.json(), indent=2))

print("\n" + "="*80)
print("✅ END-TO-END WEBHOOK TEST COMPLETED")
print("="*80 + "\n")
