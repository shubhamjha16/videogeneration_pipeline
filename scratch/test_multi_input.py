import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_html_input():
    print("\n--- Testing HTML Input ---")
    payload = {
        "topic": "HTML Test",
        "html": "<html><body><h1>Lesson 1</h1><p>This is a test of HTML input.</p></body></html>",
        "render_mode": "presentation"
    }
    response = requests.post(f"{BASE_URL}/render", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.json().get("job_id")

def test_json_input():
    print("\n--- Testing JSON Input ---")
    payload = {
        "topic": "JSON Test",
        "json_data": [
            {"title": "Fact 1", "description": "This is the first fact from JSON."},
            {"title": "Fact 2", "description": "This is the second fact from JSON."}
        ],
        "render_mode": "presentation"
    }
    response = requests.post(f"{BASE_URL}/render", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.json().get("job_id")

def test_markdown_input():
    print("\n--- Testing Markdown Input ---")
    payload = {
        "topic": "Markdown Test",
        "markdown": "# Lesson 1\n\nThis is a test of **Markdown** input.\n\n- Point A\n- Point B",
        "render_mode": "presentation"
    }
    response = requests.post(f"{BASE_URL}/render", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.json().get("job_id")

if __name__ == "__main__":
    try:
        html_id = test_html_input()
        json_id = test_json_input()
        md_id = test_markdown_input()
        
        print("\n--- Verification Summary ---")
        print(f"HTML Job ID: {html_id}")
        print(f"JSON Job ID: {json_id}")
        print(f"Markdown Job ID: {md_id}")
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the API. Make sure it's running at http://localhost:8000")
