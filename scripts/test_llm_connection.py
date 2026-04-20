import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from llm_factory import LLMFactory

def test_local_completion():
    print(f"📡 Testing Local LLM Integration...")
    print(f"   Provider: {config.LLM_PROVIDER}")
    print(f"   URL:      {config.LOCAL_LLM_URL}")
    print(f"   Model:    {config.LOCAL_LLM_MODEL}")
    
    messages = [
        {"role": "user", "content": "You are the Director of an AI Video Factory. Say 'System online and ready for production' if you can hear me."}
    ]
    
    try:
        response = LLMFactory.get_completion(messages)
        print("\n✅ CONNECTION SUCCESS!")
        print(f"🤖 Local Gemma Response: \"{response.strip()}\"")
    except Exception as e:
        print(f"\n❌ CONNECTION FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_local_completion()
