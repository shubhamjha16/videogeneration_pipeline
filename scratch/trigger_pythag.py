import requests
import json
import time

API_BASE = "http://localhost:8000"
API_KEY = "etl_factory_prod_8291_secret"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

payload = {
    "topic": "Pythagorean Theorem",
    "markdown": """# Pythagorean Theorem

## The Foundation of Geometry
In any right-angled triangle, the area of the square whose side is the hypotenuse (the side opposite the right angle) is equal to the sum of the areas of the squares on the other two sides.
Mathematically, we write this as:
$$a^2 + b^2 = c^2$$

## Solving for the Unknowns
If we know any two sides of a right triangle, we can solve for the third side using simple algebra:
- **Hypotenuse**: $c = \\sqrt{a^2 + b^2}$
- **Base/Altitude**: $a = \\sqrt{c^2 - b^2}$ or $b = \\sqrt{c^2 - a^2}$

## The Classic 3-4-5 Triangle
Let us look at the most famous Pythagorean triple: sides of length 3, 4, and 5.
$$3^2 + 4^2 = 9 + 16 = 25 = 5^2$$
Therefore, a triangle with sides 3 and 4 must have a hypotenuse of 5.

## Modern Real-World Usage
This ancient theorem is critical in modern science and tech:
- **Computer Graphics**: Calculating distances between 2D or 3D coordinate points.
- **GPS Navigation**: Triangulation algorithms to find physical coordinates.
- **Architecture**: Construction workers use 3-4-5 rules to build perfectly square walls.
""",
    "render_mode": "presentation",
    "with_avatar": False,
    "use_elevenlabs": False
}

print(f"Sending POST request to {API_BASE}/render with topic '{payload['topic']}'...")
response = requests.post(f"{API_BASE}/render", json=payload, headers=headers)

if response.status_code == 200:
    job = response.json()
    print("🎉 Job spawned successfully!")
    print(json.dumps(job, indent=2))
    job_id = job["job_id"]
    
    print("\nStarting live status polling...\n")
    while True:
        status_resp = requests.get(f"{API_BASE}/status/{job_id}", headers=headers)
        if status_resp.status_code == 200:
            status_data = status_resp.json()
            progress = status_data.get("progress", 0)
            current_step = status_data.get("current_step", "unknown")
            status = status_data.get("status", "processing")
            print(f"[{time.strftime('%H:%M:%S')}] Status: {status} | Step: {current_step} | Progress: {progress}%")
            
            if status in ["completed", "failed"]:
                print(f"\n🏁 Render finalized with status: {status}")
                if status == "completed":
                    print(f"🎥 Video URL: {API_BASE}{status_data.get('video_url')}")
                    print(f"🖼️ Thumbnail URL: {API_BASE}{status_data.get('thumbnail_url')}")
                else:
                    print(f"❌ Error: {status_data.get('error')}")
                break
        else:
            print(f"⚠️ Error polling status: {status_resp.status_code}")
        time.sleep(5)
else:
    print(f"❌ Failed to trigger render: {response.status_code}")
    print(response.text)
