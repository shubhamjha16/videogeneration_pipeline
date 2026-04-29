import requests
import json

def trigger_render():
    url = "http://localhost:8000/render"
    
    payload = {
        "topic": "The Solar System",
        "markdown": """
# The Solar System

The Solar System consists of the Sun and everything bound to it by gravity.

## Key Facts
- The Sun contains 99.86% of the system's mass.
- There are eight recognized planets.
- The asteroid belt lies between Mars and Jupiter.

## Question
Which planet is known for its prominent ring system?
A. Mercury
B. Earth
C. Saturn
D. Neptune

The correct answer is C. Saturn.
        """,
        "render_mode": "manim",
        "with_avatar": False
    }
    
    headers = {
        "X-API-Key": "etl_factory_prod_8291_secret"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Status: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    trigger_render()
