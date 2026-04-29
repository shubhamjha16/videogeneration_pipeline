import requests
import json

def trigger_render_html():
    url = "http://localhost:8000/render"
    
    html_content = """
    <html>
    <body>
        <h1>The Solar System: Planets and Moons</h1>
        <p>The Solar System consists of our star, the Sun, and everything bound to it by gravity — the planets Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, and Neptune; dwarf planets such as Pluto; dozens of moons; and millions of asteroids, comets, and meteoroids.</p>
        
        <h2>Key Questions</h2>
        <p>Which planet is famously known as the 'Red Planet' due to its iron oxide surface?</p>
        <ul>
            <li>A. Venus</li>
            <li>B. Mars</li>
            <li>C. Jupiter</li>
            <li>D. Saturn</li>
        </ul>
        
        <h3>Answer Key</h3>
        <p>The correct answer is B. Mars. Its reddish appearance comes from iron oxide (rust) on its surface.</p>
    </body>
    </html>
    """
    
    payload = {
        "topic": "Mars: The Red Planet (HTML)",
        "html": html_content,
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
    trigger_render_html()
