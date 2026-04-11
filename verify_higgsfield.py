import os
import requests
import time

API_ID = "c05c45fe-b14d-4355-b1fe-d0dbb34e86d4"
API_KEY = "ffcbb017c4ccf2ad8f5b0606cd2792b71591571f16933e921e648b304b3b1888"

def test_muapi():
    url = "https://api.muapi.ai/api/v1/generate_video"
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": "Cinematic shot of a golden pocket watch ticking slowly",
        "aspect_ratio": "16:9",
        "resolution": "720p",
        "duration": 5
    }
    # Just checking the submission first
    print("Testing Muapi Submission...")
    # response = requests.post(url, headers=headers, json=payload)
    # print(f"Response: {response.status_code} - {response.text}")

if __name__ == "__main__":
    test_muapi()
