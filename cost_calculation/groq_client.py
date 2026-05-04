import asyncio
import json
from groq import AsyncGroq
from src.clients.base_client import BaseAIClient
from src.config.pipeline_config import ModelConfig
from src.schema.domain import (
    BatchMCQAnswer,
    Citation,
    ExplanationResponse,
    SolutionV2,
    MCQAnswer,
    TokenUsage,
)

def _groq_usage(response) -> TokenUsage:
    u = getattr(response, "usage", None)
    if not u:
        return TokenUsage()
    # Groq returns prompt_tokens and completion_tokens
    return TokenUsage(
        input_tokens=getattr(u, "prompt_tokens", 0) or 0,
        cached_input_tokens=0, # Groq doesn't support prompt caching yet
        cache_write_tokens=0,
        output_tokens=getattr(u, "completion_tokens", 0) or 0,
    )

class GroqClient(BaseAIClient):
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.client = AsyncGroq(
            api_key=self.api_key,
            timeout=self.config.timeout_ms / 1000,
        )

    async def get_answer(self, prompt: str | list[dict], system_prompt: str = "") -> MCQAnswer:
        timeout_s = self.config.timeout_ms / 1000
        return await asyncio.wait_for(self._get_answer_inner(prompt, system_prompt), timeout=timeout_s)

    async def _get_answer_inner(self, prompt: str | list[dict], system_prompt: str) -> MCQAnswer:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        if isinstance(prompt, list):
            # Groq supports vision (Llama 3.2), but for simplicity we treat it as text here
            # to match the base MCQ requirement.
            text = "\n".join([p["text"] for p in prompt if p["type"] == "text"])
            messages.append({"role": "user", "content": text})
        else:
            messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0,
        )
        return MCQAnswer.model_validate_json(response.choices[0].message.content)

    async def get_batch_answer(
        self, prompt: str | list[dict], system_prompt: str = "",
    ) -> tuple[BatchMCQAnswer, TokenUsage]:
        timeout_s = self.config.timeout_ms / 1000
        return await asyncio.wait_for(self._get_batch_answer_inner(prompt, system_prompt), timeout=timeout_s)

    async def _get_batch_answer_inner(
        self, prompt: str | list[dict], system_prompt: str,
    ) -> tuple[BatchMCQAnswer, TokenUsage]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt if isinstance(prompt, str) else str(prompt)})

        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0,
        )
        return (
            BatchMCQAnswer.model_validate_json(response.choices[0].message.content),
            _groq_usage(response),
        )

    async def get_explanation(
        self, prompt: str | list[dict], system_prompt: str = "",
    ) -> tuple[ExplanationResponse, TokenUsage]:
        timeout_s = self.config.timeout_ms / 1000
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt if isinstance(prompt, str) else str(prompt)})

        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        return (
            ExplanationResponse.model_validate_json(response.choices[0].message.content),
            _groq_usage(response),
        )

    async def get_solution_v2(
        self, prompt: str | list[dict], system_prompt: str = "",
    ) -> tuple[SolutionV2, TokenUsage]:
        timeout_s = self.config.timeout_ms / 1000
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt if isinstance(prompt, str) else str(prompt)})

        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        return (
            SolutionV2.model_validate_json(response.choices[0].message.content),
            _groq_usage(response),
        )

    async def get_citations(self, prompt: str) -> tuple[list[Citation], TokenUsage]:
        # Groq doesn't have native web search tools in the standard API yet
        raise NotImplementedError("Citations only supported via Gemini grounded search")

    async def count_input_tokens(
        self, prompt: str | list[dict], system_prompt: str = "",
    ) -> int:
        # Llama 3 uses tiktoken-compatible encoding (o200k_base or similar)
        # but for an exact count we'd need their specific tokenizer.
        # Fallback to a rough estimate (chars / 4) or 0 if strictly required.
        text = prompt if isinstance(prompt, str) else str(prompt)
        return (len(text) + len(system_prompt)) // 4
