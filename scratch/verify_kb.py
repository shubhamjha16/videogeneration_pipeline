import sys
import os
import json
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from knowledge_manager import distill_search_results, save_knowledge, get_knowledge
import config

def verify_kb_logic():
    load_dotenv()
    
    topic = "Internal Iliac Artery"
    mock_results = [
        {
            "title": "Internal iliac artery - Wikipedia",
            "url": "https://en.wikipedia.org/wiki/Internal_iliac_artery",
            "content": "The internal iliac artery is the smaller of the two terminal branches of the common iliac artery. It supplies the walls and viscera of the pelvis."
        },
        {
            "title": "Branches of Internal Iliac Artery",
            "url": "https://teachmeanatomy.info",
            "content": "The internal iliac artery divides into an anterior and a posterior division. The anterior division gives off many branches like the obturator and umbilical."
        }
    ]
    
    print(f"--- 1. Testing Distillation ---")
    distilled = distill_search_results(topic, mock_results)
    print(json.dumps(distilled, indent=2))
    
    print(f"\n--- 2. Testing Storage ---")
    path = save_knowledge(topic, distilled)
    if path and os.path.exists(path):
        print(f"✅ KB file created: {path}")
    else:
        print(f"❌ KB file creation failed.")
        
    print(f"\n--- 3. Testing Retrieval ---")
    loaded = get_knowledge(topic)
    if loaded and loaded.get("summary"):
        print(f"✅ Knowledge retrieved correctly.")
    else:
        print(f"❌ Knowledge retrieval failed.")

if __name__ == "__main__":
    verify_kb_logic()
