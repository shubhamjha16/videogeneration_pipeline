import os
import sys
import json
from dotenv import load_dotenv

# Add root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

def test_connection():
    provider = os.environ.get("LLM_PROVIDER", "groq")
    print(f"Testing connection for provider: {provider}")
    
    # This is a placeholder for the actual test logic we'll implement
    # once llm_factory is created.
    print("Pre-flight check: Environment variables loaded.")
    print(f"GROQ_API_KEY set: {bool(config.GROQ_API_KEY)}")
    print(f"GEMINI_API_KEY set: {bool(config.GEMINI_API_KEY)}")
    
if __name__ == "__main__":
    load_dotenv()
    test_connection()
