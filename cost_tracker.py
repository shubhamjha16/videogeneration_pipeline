import os
import json
import threading
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class TokenUsage(BaseModel):
    """Normalized per-call token usage across providers."""
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0

class Pricing(BaseModel):
    """USD price per 1M tokens for a single model."""
    input_per_mtok: float
    cached_input_per_mtok: float = 0.0
    cache_write_per_mtok: float = 0.0
    output_per_mtok: float
    flat_fee: float = 0.0

# Pricing map (costs per 1 million tokens, or static logic)
MODELS_PRICING = {
    # Groq Models
    "llama-3.3-70b-versatile": Pricing(input_per_mtok=0.59, output_per_mtok=0.79),
    "llama3-70b-8192": Pricing(input_per_mtok=0.59, output_per_mtok=0.79),
    "llama3-8b-8192": Pricing(input_per_mtok=0.05, output_per_mtok=0.08),
    "mixtral-8x7b-32768": Pricing(input_per_mtok=0.24, output_per_mtok=0.24),
    
    # OpenAI Models
    "gpt-4o": Pricing(input_per_mtok=2.50, cached_input_per_mtok=1.25, output_per_mtok=10.0),
    "gpt-4o-mini": Pricing(input_per_mtok=0.150, cached_input_per_mtok=0.075, output_per_mtok=0.60),
    "gpt-3.5-turbo": Pricing(input_per_mtok=0.50, output_per_mtok=1.50),
    
    # Anthropic Models (Claude 3.5 / 4.5 / 4.7)
    "claude-4-7-opus-latest": Pricing(input_per_mtok=5.00, cached_input_per_mtok=0.50, cache_write_per_mtok=6.25, output_per_mtok=25.0),
    "claude-4-5-sonnet-latest": Pricing(input_per_mtok=3.00, cached_input_per_mtok=0.30, cache_write_per_mtok=3.75, output_per_mtok=15.0),
    "claude-3-5-sonnet-latest": Pricing(input_per_mtok=3.00, cached_input_per_mtok=0.30, cache_write_per_mtok=3.75, output_per_mtok=15.0),
    "claude-3-5-haiku-20241022": Pricing(input_per_mtok=0.25, cached_input_per_mtok=0.03, cache_write_per_mtok=0.30, output_per_mtok=1.25),
    
    # Google Gemini Models (1.5 / 2.0 / 3.0 / 3.1)
    "gemini-3.1-pro": Pricing(input_per_mtok=2.00, cached_input_per_mtok=0.20, output_per_mtok=12.00),
    "gemini-3-flash": Pricing(input_per_mtok=0.50, cached_input_per_mtok=0.05, output_per_mtok=3.00),
    "gemini-2.0-flash": Pricing(input_per_mtok=0.10, cached_input_per_mtok=0.01, output_per_mtok=0.40),
    "gemini-1.5-pro": Pricing(input_per_mtok=1.25, cached_input_per_mtok=0.125, output_per_mtok=5.00),
    "gemini-1.5-flash": Pricing(input_per_mtok=0.075, cached_input_per_mtok=0.0075, output_per_mtok=0.30),
    
    # Local Models (Free)
    "gemma:4b": Pricing(input_per_mtok=0.0, output_per_mtok=0.0),
    "gemma:7b": Pricing(input_per_mtok=0.0, output_per_mtok=0.0),
    # Search & Vision (Flat fee logic)
    "searxng": Pricing(input_per_mtok=0, output_per_mtok=0, flat_fee=0.005), # $0.005 per metasearch
    "gpt-4o-vision": Pricing(input_per_mtok=0, output_per_mtok=0, flat_fee=0.02), # $0.02 per grounding call
    "eleven-lip-sync": Pricing(input_per_mtok=0, output_per_mtok=0, flat_fee=0.20), # $0.20 per lip-sync call
    "elevenlabs": Pricing(input_per_mtok=0, output_per_mtok=0, flat_fee=0.0), # Handled by characters logic
}

class LedgerEntry(BaseModel):
    ts: str
    job_id: str
    provider: str
    model: str
    call_type: str
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float
    from_cache: bool = False

def compute_cost_usd(usage: TokenUsage, pricing: Pricing) -> float:
    return (
        usage.input_tokens * pricing.input_per_mtok
        + usage.cached_input_tokens * pricing.cached_input_per_mtok
        + usage.cache_write_tokens * pricing.cache_write_per_mtok
        + usage.output_tokens * pricing.output_per_mtok
    ) / 1_000_000

class LedgerManager:
    _lock = threading.Lock()
    
    @classmethod
    def get_ledger_path(cls) -> str:
        # Default to "output/cost_records.jsonl" relative to project root
        media_root = os.environ.get("MANIM_MEDIA_DIR", "output")
        return os.path.join(media_root, "cost_records.jsonl")

    @classmethod
    def record_cost(cls, entry: LedgerEntry):
        path = cls.get_ledger_path()
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with cls._lock:
            with open(path, "a", encoding="utf-8") as f:
                f.write(entry.model_dump_json() + "\n")
        
        # DB Persistence: Record usage to MySQL
        try:
            from db.repository import insert_token_usage
            tts_chars = entry.input_tokens if entry.call_type == "audio" else 0
            img_count = 1 if entry.call_type == "image" else 0
            
            insert_token_usage(
                job_id=entry.job_id,
                provider=entry.provider,
                service=entry.model,
                call_type=entry.call_type,
                input_tokens=entry.input_tokens,
                output_tokens=entry.output_tokens,
                cost_usd=entry.cost_usd,
                from_cache=entry.from_cache,
                tts_characters=tts_chars,
                image_count=img_count
            )
        except Exception as e:
            # Repository already logs, but we ensure record_cost itself never raises
            print(f"⚠️ [cost_tracker] Failed to record cost: {e}")

    @classmethod
    def _log_entry(cls, data: dict):
        """Unified logging for all entry types."""
        if not data.get("job_id"):
            return
            
        entry = LedgerEntry(
            ts=datetime.utcnow().isoformat() + "Z",
            job_id=data["job_id"],
            provider=data["provider"],
            model=data.get("model", "unknown"),
            call_type=data.get("call_type", "unknown"),
            input_tokens=data.get("input_tokens", 0),
            cached_input_tokens=data.get("cached_input_tokens", 0),
            cache_write_tokens=data.get("cache_write_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            cost_usd=data.get("api_cost_usd", 0.0),
            from_cache=data.get("from_cache", False)
        )
        cls.record_cost(entry)

    @classmethod
    def record_llm_call(cls, job_id: Optional[str], provider: str, model: str, usage_dict: dict, from_cache: bool = False):
        if not job_id:
            return
            
        if from_cache:
            # Full Redis cache hit (No API call)
            cost = 0.0
            usage = TokenUsage()
        else:
            # API call (may include provider-level prompt caching)
            usage = TokenUsage(
                input_tokens=usage_dict.get("prompt_tokens", 0),
                cached_input_tokens=usage_dict.get("cached_input_tokens", 0),
                cache_write_tokens=usage_dict.get("cache_write_tokens", 0),
                output_tokens=usage_dict.get("completion_tokens", 0)
            )
            pricing = MODELS_PRICING.get(model, Pricing(input_per_mtok=0.0, output_per_mtok=0.0))
            cost = compute_cost_usd(usage, pricing)
        
        cls._log_entry({
            "job_id": job_id,
            "provider": provider,
            "model": model,
            "call_type": "llm",
            "input_tokens": usage.input_tokens,
            "cached_input_tokens": usage.cached_input_tokens,
            "cache_write_tokens": usage.cache_write_tokens,
            "output_tokens": usage.output_tokens,
            "api_cost_usd": cost,
            "from_cache": from_cache
        })

    @classmethod
    def record_tts_call(cls, job_id: Optional[str], provider: str, characters: int, cost_per_char: float = 0.00003):
        cls._log_entry({
            "job_id": job_id,
            "provider": provider,
            "model": "tts",
            "call_type": "audio",
            "input_tokens": characters,
            "api_cost_usd": characters * cost_per_char
        })

    @classmethod
    def record_heygen_call(cls, job_id: Optional[str], duration_seconds: float, cost_per_second: float = 0.0333):
        """Record HeyGen v3 Video Agents cost. Pricing: $0.0333/sec of output."""
        cls._log_entry({
            "job_id": job_id,
            "provider": "heygen",
            "model": "avatar-v3",
            "call_type": "video",
            "api_cost_usd": duration_seconds * cost_per_second
        })
        
    @classmethod
    def record_higgsfield_call(cls, job_id: Optional[str], cost_per_call: float = 0.10):
        cls._log_entry({
            "job_id": job_id,
            "provider": "higgsfield",
            "model": "image",
            "call_type": "image",
            "api_cost_usd": cost_per_call
        })

    @classmethod
    def record_search_call(cls, job_id: Optional[str], provider: str = "searxng"):
        pricing = MODELS_PRICING.get(provider)
        cost = pricing.flat_fee if pricing else 0.005
        cls._log_entry({
            "job_id": job_id,
            "provider": provider,
            "model": provider,
            "call_type": "search",
            "api_cost_usd": cost
        })

    @classmethod
    def record_vision_call(cls, job_id: Optional[str], model: str = "gpt-4o-vision"):
        pricing = MODELS_PRICING.get(model)
        cost = pricing.flat_fee if pricing else 0.02
        cls._log_entry({
            "job_id": job_id,
            "provider": "openai",
            "model": model,
            "call_type": "vision",
            "api_cost_usd": cost
        })

    @classmethod
    def record_dalle_call(cls, job_id: Optional[str], model: str = "dall-e-3", cost: float = 0.04):
        """Record DALL-E 3 image generation cost. Pricing depends on size/quality."""
        cls._log_entry({
            "job_id": job_id,
            "provider": "openai",
            "model": model,
            "call_type": "image",
            "api_cost_usd": cost
        })

    @classmethod
    def get_job_total_cost(cls, job_id: str) -> float:
        total = 0.0
        path = cls.get_ledger_path()
        if not os.path.exists(path):
            return 0.0
        try:
            with open(path, "r") as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get("job_id") == job_id:
                        total += entry.get("cost_usd", 0.0)
        except Exception as e:
            print(f"⚠️ Error reading ledger for job {job_id}: {e}")
        return round(total, 6)
