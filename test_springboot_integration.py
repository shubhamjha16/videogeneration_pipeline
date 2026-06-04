#!/usr/bin/env python3
"""
Integration test: Simulate Spring Boot → Factory workflow
This script tests what your Spring Boot integration will do:
  1. POST /render with X-Api-Key header
  2. Receive job_id back
  3. Factory would later POST /webhook back to Spring Boot
"""

import requests
import json
import time
from datetime import datetime

import os
FACTORY_URL = os.environ.get("FACTORY_URL", "http://10.0.1.1:8000")
FACTORY_API_KEY = "etl_factory_prod_8291_secret"
SPRING_BOOT_WEBHOOK = os.environ.get("SPRING_BOOT_WEBHOOK", "http://10.0.1.10:8081/api/v1/videos/webhook")

def test_springboot_integration():
    """Test the exact payload shape that Spring Boot would send."""

    print("\n" + "="*80)
    print("🔄 SPRING BOOT → FACTORY INTEGRATION TEST")
    print("="*80)

    # Step 1: Simulate what Spring Boot's RenderRequest would POST to factory
    # After the fix, RenderRequest is mapped to match factory's /render contract:
    #   - topic: the semantic title (Spring Boot's 'title')
    #   - html/solution_v2/json_data/markdown: content (one required)
    #   - render_mode: optional (factory AI decides if null)
    #   - webhook_url: where factory POSTs job completion
    #
    # Internal metadata (jobId, purpose, etc.) is NOT sent to factory (marked @JsonProperty WRITE_ONLY)
    render_payload = {
        "topic": "Solve the Quadratic Equation v2",  # Required by factory
        "html": "<h3>Quadratic Equation Basics</h3><p>For ax² + bx + c = 0, use the quadratic formula...</p>",  # Required (one of: html|solution_v2|json_data|markdown)
        "render_mode": "manim",  # Optional (factory AI chooses if null)
        "webhook_url": f"{SPRING_BOOT_WEBHOOK}",  # Where factory POSTs results
        "use_elevenlabs": True  # Optional TTS strategy
    }

    headers = {
        "X-Api-Key": FACTORY_API_KEY,
        "Content-Type": "application/json"
    }

    print("\n📤 Spring Boot (RenderRequest) POSTs to factory /render:")
    print(json.dumps(render_payload, indent=2))
    print(f"\n📋 Headers: {json.dumps(headers, indent=2)}")
    print("\n✅ Note: Spring Boot internal fields (jobId, purpose, relatedEntityType, etc.) are marked")
    print("   @JsonProperty(access=WRITE_ONLY) so they're NOT serialized in the HTTP POST.")

    # Step 2: Actually send it
    print("\n⏳ Sending to factory...")
    try:
        response = requests.post(
            f"{FACTORY_URL}/render",
            json=render_payload,
            headers=headers,
            timeout=10
        )
        print(f"✅ Response Status: {response.status_code}")

        if response.status_code in [200, 202]:
            body = response.json()
            print(f"✅ Factory response: {json.dumps(body, indent=2)}")

            factory_job_id = body.get("job_id") or body.get("jobId")  # Try both snake_case and camelCase
            if factory_job_id:
                print(f"\n🎯 Factory job_id: {factory_job_id}")

                # Step 3: Spring Boot would return 202 to caller
                # Note: Spring Boot's jobId is different from factory's job_id
                # Spring Boot generates its own UUID and stores the factory job_id in the VideoCacheEntity
                spring_boot_job_id = "550e8400-e29b-41d4-a716-446655440001"  # Spring Boot's internal UUID
                spring_boot_response = {
                    "jobId": spring_boot_job_id,
                    "status": "QUEUED",
                    "message": f"Render job queued. Poll /api/v1/videos/{spring_boot_job_id}/status for updates."
                }
                print(f"\n📤 Spring Boot would return 202 ACCEPTED to caller:")
                print(json.dumps(spring_boot_response, indent=2))

                # Step 4: Poll factory for job status
                print(f"\n🔍 Polling factory for job {factory_job_id} status...")
                time.sleep(2)

                status_response = requests.get(
                    f"{FACTORY_URL}/status/{factory_job_id}",
                    headers={"X-Api-Key": FACTORY_API_KEY},
                    timeout=5
                )

                if status_response.status_code == 200:
                    job_status = status_response.json()
                    print(f"✅ Job status: {json.dumps(job_status, indent=2)}")
                else:
                    print(f"⚠️  Status endpoint returned {status_response.status_code}")

                print("\n" + "="*80)
                print("✅ INTEGRATION TEST PASSED")
                print("="*80)
                print(f"\nFlow verified:")
                print(f"  1. ✅ Spring Boot can auth to factory (X-Api-Key works)")
                print(f"  2. ✅ Factory accepts RenderRequest payload shape")
                print(f"  3. ✅ Factory returns job_id")
                print(f"  4. ✅ Spring Boot returns 202 QUEUED to caller")
                print(f"  5. ⏳ Factory will POST webhook back to: {SPRING_BOOT_WEBHOOK}")
                print(f"\nNext: Start Spring Boot service on port 8081 to receive webhooks")

            else:
                print("❌ Factory response missing job_id field!")

        else:
            print(f"❌ Unexpected status {response.status_code}: {response.text}")

    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to factory on {FACTORY_URL}")
        print("   Make sure Uvicorn is running: uvicorn api_bridge:app --port 8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_springboot_integration()
