import os
import sys
import json
from dotenv import load_dotenv

# Add root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from llm_factory import LLMFactory, clean_llm_json

def test_llm_integration():
    """
    Diagnostic script to test LLM connectivity across all providers.
    """
    load_dotenv()
    
    current_provider = config.LLM_PROVIDER
    print(f"🚀 Testing LLM Integration (Current Provider: {current_provider})")
    
    test_messages = [{"role": "user", "content": "Say 'EaseToLearn Industrial LLM Test Success' and return a JSON object like {'status': 'success'}."}]
    
    # 1. Test Current Provider
    print(f"\n--- Testing Provider: {current_provider} ---")
    try:
        content = LLMFactory.get_completion(
            messages=test_messages,
            json_mode=True
        )
        data = clean_llm_json(content)
        print(f"✅ Success! Response: {data}")
    except Exception as e:
        print(f"❌ Failed: {e}")

    # 2. Test Local (if configured)
    if current_provider != "local":
        print(f"\n--- Testing Provider: local (URL: {config.LOCAL_LLM_URL}, Model: {config.LOCAL_LLM_MODEL}) ---")
        try:
            content = LLMFactory.get_completion(
                messages=test_messages,
                provider_override="local",
                json_mode=True
            )
            data = clean_llm_json(content)
            print(f"✅ Success! Local Response: {data}")
        except Exception as e:
            print(f"ℹ️ Local test skipped or failed (common if tunnel/WireGuard is not active): {e}")

if __name__ == "__main__":
    test_llm_integration()
