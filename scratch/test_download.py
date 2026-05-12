import requests
import os

url = "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9c/Erythema_multiforme.jpg/440px-Erythema_multiforme.jpg"
headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}

print(f"Testing download from: {url}")
try:
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    print(f"Success! Status: {resp.status_code}, Length: {len(resp.content)}")
    with open("test_wiki_image.jpg", "wb") as f:
        f.write(resp.content)
    print(f"Saved to test_wiki_image.jpg")
except Exception as e:
    print(f"Failed: {e}")
