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
        include_usage: bool = False,
        cacheable: bool = True,
        job_id: Optional[str] = None,
        temperature: float = 0.0
    ) -> Any:
        from caching.redis_client import get_cache, generate_llm_cache_key
        
        provider = provider_override or config.LLM_PROVIDER
        
        # Determine the effective model name for cache keying
        model = model_override
        if not model:
            if provider == "groq": model = "llama-3.1-8b-instant"
            elif provider == "openai": model = "gpt-4o"
            elif provider == "local": model = config.LOCAL_LLM_MODEL
            else: model = "unknown"

        # Merge system prompt if provided separately
        full_messages = messages
        if system_prompt:
            full_messages = [{"role": "system", "content": system_prompt}] + messages

        effective_cacheable = cacheable and (temperature == 0.0)

        # ── LLM CACHE LOOKUP ──────────────────────────────────────────────────
        cache = get_cache()
        cache_key = None
        if cache.available and effective_cacheable:
            # We use a default temperature of 0.0 for deterministic educational content
            cache_key = generate_llm_cache_key(model, str(system_prompt or ""), str(messages), temperature)
            cached_res = cache.get(cache_key)
            if cached_res:
                print(f"💎 LLM Cache Hit: {model} (Key: {cache_key[:8]}...)")
                content = cached_res["content"]
                usage = cached_res["usage"]
                usage["from_cache"] = True
                
                try:
                    from cost_tracker import LedgerManager
                    LedgerManager.record_llm_call(job_id, provider, model, usage, from_cache=True)
                except Exception as e:
                    print(f"⚠️ Failed to record LLM cost: {e}")
                    
                return (content, usage) if include_usage else content

        # ── CACHE MISS: Execute Completion with Resilient Retry ──
        import time
        for attempt in range(5):
            try:
                if provider == "groq":
                    content, usage = LLMFactory._call_groq(full_messages, json_mode, model_override, temperature)
                elif provider == "openai":
                    content, usage = LLMFactory._call_openai(full_messages, json_mode, model_override, temperature)
                elif provider == "local":
                    content, usage = LLMFactory._call_local(full_messages, json_mode, model_override, temperature)
                elif provider == "google":
                    content, usage = LLMFactory._call_google(full_messages, json_mode, model_override)
                else:
                    raise ValueError(f"Unknown LLM provider: {provider}")
                break
            except Exception as e:
                if attempt == 4:
                    print(f"❌ LLM Provider '{provider}' failed completely after 5 attempts. Last error: {e}")
                    raise
                
                # Dynamic backoff sleep duration
                sleep_sec = 3.0 * (2 ** attempt)
                # Parse retry-after from error message if possible
                import re
                retry_match = re.search(r"try again in ([\d\.]+)s", str(e), re.IGNORECASE)
                if retry_match:
                    try:
                        sleep_sec = float(retry_match.group(1)) + 0.5
                    except Exception as e:
                        print(f"⚠️ [LLMFactory] Failed to parse retry-after duration: {e}")
                
                print(f"⚠️  LLM Provider '{provider}' error: {e}. Retrying ({attempt + 1}/5) in {sleep_sec:.2f}s...")
                time.sleep(sleep_sec)

        # ── PERSIST TO CACHE ──────────────────────────────────────────────────
        if cache.available and effective_cacheable and cache_key:
            cache.set(cache_key, {"content": content, "usage": usage}, ttl_seconds=86400 * 7) # 7 Day TTL

        usage["from_cache"] = False
        
        try:
            from cost_tracker import LedgerManager
            LedgerManager.record_llm_call(job_id, provider, model, usage, from_cache=False)
        except Exception as e:
            print(f"⚠️ Failed to record LLM cost: {e}")
            
        return (content, usage) if include_usage else content


    @staticmethod
    def _call_openai(messages, json_mode, model_override, temperature: float = 0.0):
        if not OpenAI:
            raise ImportError("openai library not installed. pip install openai")
        
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY missing")
            
        client = OpenAI(api_key=api_key, timeout=300.0)
        model = model_override or "gpt-4o"
        
        kwargs = {
            "model": model,
            "messages": messages,
            "timeout": 300.0,
            "temperature": temperature
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
            
        response = client.chat.completions.create(**kwargs)
        
        usage = {
            "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0),
            "completion_tokens": getattr(response.usage, 'completion_tokens', 0),
            "total_tokens": getattr(response.usage, 'total_tokens', 0)
        }
        return response.choices[0].message.content, usage

    @staticmethod
    def _call_groq(messages, json_mode, model_override, temperature: float = 0.0):
        if not Groq:
            raise ImportError("groq library not installed. pip install groq")
        
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY missing")
            
        # Industrial Sentinel: Set a generous 300s timeout for complex director planning
        client = Groq(api_key=api_key, timeout=300.0)
        model = model_override or "llama-3.1-8b-instant"
        
        kwargs = {
            "model": model,
            "messages": messages,
            "timeout": 300.0,
            "temperature": temperature
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
    def _call_local(messages, json_mode, model_override, temperature: float = 0.0):
        """Connects to Mac Mini via WireGuard/Tunneling using OpenAI-compatible API."""
        if not OpenAI:
            raise ImportError("openai library not installed. pip install openai")
            
        base_url = config.LOCAL_LLM_URL
        model = model_override or config.LOCAL_LLM_MODEL
        
        client = OpenAI(base_url=base_url, api_key="local-dev", timeout=300.0)
        
        kwargs = {
            "model": model,
            "messages": messages,
            "timeout": 300.0,
            "temperature": temperature
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
                    # Clear timeout from kwargs if we re-try? No, keep it.
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
    
    data = None
    
    # 1. Try direct parse
    try:
        data = json.loads(content.strip())
    except Exception as e:
        print(f"⚠️ [clean_llm_json] Direct JSON parse failed: {e}")
    
    # 2. Try markdown extraction
    if data is None:
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1).strip())
            except Exception as e:
                print(f"⚠️ [clean_llm_json] Markdown-extracted JSON parse failed: {e}")
    
    # 3. Try fuzzy extraction (first { to last })
    if data is None:
        try:
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                potential_json = content[start_idx:end_idx+1]
                data = json.loads(potential_json.strip())
        except Exception as e:
            print(f"⚠️ [clean_llm_json] Fuzzy-extracted JSON parse failed: {e}")
        
    # 4. Final attempt with prefix stripping
    if data is None:
        try:
            cleaned = content.strip().lstrip("JSON response:").lstrip("Here is the JSON:").strip()
            data = json.loads(cleaned)
        except Exception as e:
            print(f"⚠️ [clean_llm_json] Prefix-stripped JSON parse failed: {e}")

    # 5. INDUSTRIAL SURGERY: Auto-close truncated JSON
    if data is None:
        try:
            print("   🔧 LLM-FACTORY: Attempting emergency JSON surgery on truncated response...")
            # Remove trailing non-JSON garbage
            fuzzy = content.strip().split("```")[0].strip()
            start_idx = fuzzy.find('{')
            if start_idx != -1:
                fuzzy = fuzzy[start_idx:]
                
                # Balance brackets
                stack = []
                for i, char in enumerate(fuzzy):
                    if char == '{': stack.append('}')
                    elif char == '[': stack.append(']')
                    elif char in ['}', ']']:
                        if stack and stack[-1] == char:
                            stack.pop()
                
                # Append missing closers in reverse order
                repaired = fuzzy + "".join(reversed(stack))
                data = json.loads(repaired)
                print("   ✅ LLM-FACTORY: Surgery successful. Truncated JSON recovered.")
        except Exception as e:
            print(f"   ❌ LLM-FACTORY: Surgery failed: {e}")

    if data is None:
        raise ValueError(f"Failed to extract valid JSON from LLM response: {content[:200]}...")

    # INDUSTRIAL SENTINEL: Universal Unwrapping for Gemma 4
    # Gemma 4 often wraps the response in a single key named after the schema (e.g., {"DirectorOutput": {...}})
    if isinstance(data, dict) and len(data) == 1:
        key = list(data.keys())[0]
        # Schema names typically start with Uppercase
        if key[0].isupper():
            print(f"📦 LLM-FACTORY: Unwrapping JSON from '{key}' key.")
            data = data[key]
    
    return data
