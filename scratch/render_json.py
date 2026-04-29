import requests
import json

def trigger_render_json():
    url = "http://localhost:8000/render"
    
    payload = {
        "topic": "The Solar System (JSON)",
        "json_data": [
            {"title": "The Planets", "description": "There are eight planets in our solar system that orbit the Sun."},
            {"title": "The Sun", "description": "The Sun is at the center of our solar system and provides light and heat."},
            {"title": "Question", "description": "Which planet has the most extensive and visible ring system in our solar system?\nA. Mercury\nB. Earth\nC. Saturn\nD. Neptune\n\nThe correct answer is C. Saturn."}
        ],
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
    trigger_render_json()
