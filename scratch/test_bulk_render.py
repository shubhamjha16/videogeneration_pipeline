import requests
import json

BASE_URL = "http://localhost:8000"

def test_bulk_render():
    print("\n--- Testing Bulk Render (Multi-Format) ---")
    files = {'file': ('test_bulk_multi.json', open('scratch/test_bulk_multi.json', 'rb'), 'application/json')}
    response = requests.post(f"{BASE_URL}/bulk_render", files=files)
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Batch ID: {data.get('batch_id')}")
        print(f"Job IDs: {data.get('job_ids')}")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    try:
        test_bulk_render()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the API. Make sure it's running at http://localhost:8000")
