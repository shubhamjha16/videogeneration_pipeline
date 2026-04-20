import os
import json
import time
from typing import Optional, Any, List, Dict
import config

# Fallback to standard libraries if specific ones aren't installed
try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

class LLMFactory:
    """
    Industrial Hub for LLM operations.
    Supports Groq (Llama 3), Google (Gemini), and Local (Gemma/WireGuard).
    """
    
    @staticmethod
    def get_completion(
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        model_override: Optional[str] = None,
        provider_override: Optional[str] = None
    ) -> str:
        provider = provider_override or config.LLM_PROVIDER
        
        # Merge system prompt if provided separately
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages
            
        if provider == "groq":
            return LLMFactory._call_groq(messages, json_mode, model_override)
        elif provider == "local":
            return LLMFactory._call_local(messages, json_mode, model_override)
        elif provider == "google":
            return LLMFactory._call_google(messages, json_mode, model_override)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    @staticmethod
    def _call_groq(messages, json_mode, model_override):
        if not Groq:
            raise ImportError("groq library not installed. pip install groq")
        
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY missing")
            
        client = Groq(api_key=api_key)
        model = model_override or "llama-3.3-70b-versatile"
        
        kwargs = {
            "model": model,
            "messages": messages,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
            
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    @staticmethod
    def _call_local(messages, json_mode, model_override):
        """Connects to Mac Mini via WireGuard/Tunneling using OpenAI-compatible API."""
        if not OpenAI:
            raise ImportError("openai library not installed. pip install openai")
            
        base_url = config.LOCAL_LLM_URL
        model = model_override or config.LOCAL_LLM_MODEL
        
        client = OpenAI(base_url=base_url, api_key="local-dev")
        
        kwargs = {
            "model": model,
            "messages": messages,
        }
        
        # INDUSTRIAL HARDENING: Some local runners (older Ollama/vLLM) crash with response_format.
        # We try with it first, then fallback if it fails.
        if json_mode:
            try:
                kwargs["response_format"] = {"type": "json_object"}
                response = client.chat.completions.create(**kwargs)
                return response.choices[0].message.content
            except Exception as e:
                # If it's a 400 Bad Request regarding response_format, retry without it
                if "response_format" in str(e) or "400" in str(e):
                    print(f"⚠️ Local LLM does not support JSON Mode. Retrying with raw format...")
                    kwargs.pop("response_format")
                else:
                    raise
                    
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    @staticmethod
    def _call_google(messages, json_mode, model_override):
        raise NotImplementedError("Direct chat completion for Google provider through factory not yet implemented.")

# Helper for JSON cleaning (LLMs often wrap JSON in markdown or conversational chatter)
def clean_llm_json(content: str) -> dict:
    import re
    import json
    
    # 1. Try direct parse first (cleanest case)
    try:
        return json.loads(content.strip())
    except: pass
    
    # 2. Look for markdown code blocks: ```json ... ``` or ``` ... ```
    match = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except: pass
        
    # 3. Look for the first '{' and last '}' — aggressive extraction
    try:
        start_idx = content.find('{')
        end_idx = content.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            potential_json = content[start_idx:end_idx+1]
            return json.loads(potential_json.strip())
    except: pass
    
    # 4. Final attempt: strip common prefixes/suffixes
    cleaned = content.strip().lstrip("JSON response:").lstrip("Here is the JSON:").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"❌ LLM-FACTORY: Critical JSON Decode Failure.")
        print(f"   Raw Content (First 500 chars): {content[:500]}")
        raise ValueError(f"Failed to extract valid JSON from LLM response: {e}")
