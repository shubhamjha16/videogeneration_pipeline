import asyncio

from anthropic import AsyncAnthropic

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


def _anthropic_usage(response) -> TokenUsage:
    u = getattr(response, "usage", None)
    if not u:
        return TokenUsage()
    return TokenUsage(
        input_tokens=getattr(u, "input_tokens", 0) or 0,
        cached_input_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
        cache_write_tokens=getattr(u, "cache_creation_input_tokens", 0) or 0,
        output_tokens=getattr(u, "output_tokens", 0) or 0,
    )


class AnthropicClient(BaseAIClient):
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        # SDK-level timeout (httpx) + per-call asyncio.wait_for hard cap
        # both derive from config.timeout_ms.
        self.client = AsyncAnthropic(
            api_key=self.api_key,
            timeout=self.config.timeout_ms / 1000,
        )

    def _build_thinking_param(self) -> dict | None:
        if self.config.thinking_budget and self.config.thinking_budget > 0:
            return {
                "type": "adaptive",
            }
        return None

    @staticmethod
    def _to_anthropic_parts(parts: list[dict]) -> list[dict]:
        out: list[dict] = []
        for p in parts:
            if p["type"] == "text":
                out.append({"type": "text", "text": p["text"]})
            elif p["type"] == "image":
                out.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": p["media_type"],
                        "data": p["data"],
                    },
                })
            elif p["type"] == "image_url":
                out.append({
                    "type": "image",
                    "source": {
                        "type": "url",
                        "url": p["url"],
                    },
                })
        return out

    async def get_answer(self, prompt: str | list[dict], system_prompt: str = "") -> MCQAnswer:
        if isinstance(prompt, list):
            content = self._to_anthropic_parts(prompt)
        else:
            content = prompt

        # Web search disabled — rely on native structured output via output_format.
        kwargs = {
            "model": self.config.model,
            "max_tokens": 4096,
            "output_format": MCQAnswer,
            "messages": [
                {
                    "role": "user",
                    "content": content,
                }
            ],
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        thinking = self._build_thinking_param()
        if thinking:
            kwargs["thinking"] = thinking
            kwargs["temperature"] = 1  # Required when thinking is enabled
        else:
            kwargs["temperature"] = 0

        timeout_s = self.config.timeout_ms / 1000
        response = await asyncio.wait_for(
            self.client.messages.parse(**kwargs),
            timeout=timeout_s,
        )
        return response.parsed_output

    async def get_batch_answer(
        self, prompt: str | list[dict], system_prompt: str = "",
    ) -> tuple[BatchMCQAnswer, TokenUsage]:
        if isinstance(prompt, list):
            content = self._to_anthropic_parts(prompt)
        else:
            content = prompt

        kwargs = {
            "model": self.config.model,
            "max_tokens": 32000,
            "output_format": BatchMCQAnswer,
            "messages": [{"role": "user", "content": content}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        thinking = self._build_thinking_param()
        if thinking:
            kwargs["thinking"] = thinking
            kwargs["temperature"] = 1
        else:
            kwargs["temperature"] = 0

        timeout_s = self.config.timeout_ms / 1000
        response = await asyncio.wait_for(
            self.client.messages.parse(**kwargs),
            timeout=timeout_s,
        )
        if response.parsed_output is None:
            stop = getattr(response, "stop_reason", "unknown")
            raise ValueError(
                f"Anthropic returned no parsed output (stop_reason={stop}); "
                f"likely truncated or refused."
            )
        return response.parsed_output, _anthropic_usage(response)

    async def get_explanation(
        self, prompt: str | list[dict], system_prompt: str = "",
    ) -> tuple[ExplanationResponse, TokenUsage]:
        if isinstance(prompt, list):
            content = self._to_anthropic_parts(prompt)
        else:
            content = prompt

        # Web search disabled — rely on native structured output via output_format.
        kwargs = {
            "model": self.config.model,
            "max_tokens": 8192,
            "output_format": ExplanationResponse,
            "messages": [{"role": "user", "content": content}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        thinking = self._build_thinking_param()
        if thinking:
            kwargs["thinking"] = thinking
            kwargs["temperature"] = 1
        else:
            kwargs["temperature"] = 0.3

        timeout_s = self.config.timeout_ms / 1000
        response = await asyncio.wait_for(
            self.client.messages.parse(**kwargs),
            timeout=timeout_s,
        )
        return response.parsed_output, _anthropic_usage(response)

    async def get_solution_v2(
        self, prompt: str | list[dict], system_prompt: str = "",
    ) -> tuple[SolutionV2, TokenUsage]:
        if isinstance(prompt, list):
            content = self._to_anthropic_parts(prompt)
        else:
            content = prompt

        kwargs = {
            "model": self.config.model,
            "max_tokens": 8192,
            "output_format": SolutionV2,
            "messages": [{"role": "user", "content": content}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        thinking = self._build_thinking_param()
        if thinking:
            kwargs["thinking"] = thinking
            kwargs["temperature"] = 1
        else:
            kwargs["temperature"] = 0.3

        timeout_s = self.config.timeout_ms / 1000
        response = await asyncio.wait_for(
            self.client.messages.parse(**kwargs),
            timeout=timeout_s,
        )
        return response.parsed_output, _anthropic_usage(response)

    async def get_citations(self, prompt: str) -> tuple[list[Citation], TokenUsage]:
        raise NotImplementedError("Citations only supported via Gemini grounded search")

    async def count_input_tokens(
        self, prompt: str | list[dict], system_prompt: str = "",
    ) -> int:
        if isinstance(prompt, list):
            content = self._to_anthropic_parts(prompt)
        else:
            content = prompt
        kwargs = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": content}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        resp = await self.client.messages.count_tokens(**kwargs)
        return int(getattr(resp, "input_tokens", 0) or 0)
