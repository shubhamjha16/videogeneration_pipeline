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
    Supports Local (Gemma 4 / WireGuard), Groq (Llama 3), and Google (Gemini).
    """
    
    @staticmethod
    def get_completion(
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        model_override: Optional[str] = None,
        provider_override: Optional[str] = None,
        include_usage: bool = False # NEW: Enable usage tracking
    ) -> Any:
        provider = provider_override or config.LLM_PROVIDER
        
        # Merge system prompt if provided separately
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages
            
        if provider == "groq":
            content, usage = LLMFactory._call_groq(messages, json_mode, model_override)
        elif provider == "local":
            content, usage = LLMFactory._call_local(messages, json_mode, model_override)
        elif provider == "google":
            content, usage = LLMFactory._call_google(messages, json_mode, model_override)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
            
        return (content, usage) if include_usage else content

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
        
        # Industrial Usage Capture
        usage = {
            "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0),
            "completion_tokens": getattr(response.usage, 'completion_tokens', 0),
            "total_tokens": getattr(response.usage, 'total_tokens', 0)
        }
        return response.choices[0].message.content, usage

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
        
        if json_mode:
            try:
                kwargs["response_format"] = {"type": "json_object"}
                response = client.chat.completions.create(**kwargs)
                usage = {
                    "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0),
                    "completion_tokens": getattr(response.usage, 'completion_tokens', 0),
                    "total_tokens": getattr(response.usage, 'total_tokens', 0)
                }
                return response.choices[0].message.content, usage
            except Exception as e:
                # Fallback if local provider doesn't support JSON mode
                if "response_format" in str(e) or "400" in str(e):
                    kwargs.pop("response_format")
                else:
                    raise
                    
        response = client.chat.completions.create(**kwargs)
        usage = {
            "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0),
            "completion_tokens": getattr(response.usage, 'completion_tokens', 0),
            "total_tokens": getattr(response.usage, 'total_tokens', 0)
        }
        return response.choices[0].message.content, usage

    @staticmethod
    def _call_google(messages, json_mode, model_override):
        # We wrap the existing google logic here or implement it for usage capture
        # For now, we provide dummy usage for implementing the interface
        # Actual implementation usually happens in autonomous_graph.py for Gemini
        return "Not implemented in LLMFactory yet", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

# Helper for JSON cleaning
def clean_llm_json(content: str) -> dict:
    import re
    import json
    
    try:
        return json.loads(content.strip())
    except: pass
    
    match = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except: pass
        
    try:
        start_idx = content.find('{')
        end_idx = content.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            potential_json = content[start_idx:end_idx+1]
            return json.loads(potential_json.strip())
    except: pass
    
    cleaned = content.strip().lstrip("JSON response:").lstrip("Here is the JSON:").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"❌ LLM-FACTORY: Critical JSON Decode Failure.")
        raise ValueError(f"Failed to extract valid JSON from LLM response: {e}")
