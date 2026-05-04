import asyncio
import base64
import json

import httpx
from google import genai
from google.genai import types

from src.clients.base_client import BaseAIClient
from src.config.logger import logger
from src.config.pipeline_config import ModelConfig
from src.schema.domain import (
    BatchMCQAnswer,
    Citation,
    CitationListResponse,
    ExplanationResponse,
    SolutionV2,
    MCQAnswer,
    TokenUsage,
)


def _gemini_usage(response) -> TokenUsage:
    u = getattr(response, "usage_metadata", None)
    if not u:
        return TokenUsage()
    prompt_tokens = getattr(u, "prompt_token_count", 0) or 0
    cached = getattr(u, "cached_content_token_count", 0) or 0
    candidates = getattr(u, "candidates_token_count", 0) or 0
    thoughts = getattr(u, "thoughts_token_count", 0) or 0
    return TokenUsage(
        input_tokens=max(0, prompt_tokens - cached),
        cached_input_tokens=cached,
        cache_write_tokens=0,
        output_tokens=candidates + thoughts,
    )


class GeminiClient(BaseAIClient):
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.client = genai.Client(api_key=self.api_key)

    def _build_thinking_config(self):
        if self.config.thinking_level:
            return types.ThinkingConfig(thinking_level=self.config.thinking_level)
        if self.config.thinking_budget and self.config.thinking_budget > 0:
            return types.ThinkingConfig(thinking_budget=self.config.thinking_budget)
        return None

    @staticmethod
    async def _to_gemini_parts(parts: list[dict]) -> list:
        out: list = []
        for p in parts:
            if p["type"] == "text":
                out.append(p["text"])
            elif p["type"] == "image":
                out.append(types.Part(inline_data=types.Blob(
                    mime_type=p["media_type"],
                    data=base64.b64decode(p["data"]),
                )))
            elif p["type"] == "image_url":
                try:
                    async with httpx.AsyncClient(timeout=30) as http:
                        resp = await http.get(p["url"])
                        resp.raise_for_status()
                    content_type = resp.headers.get("content-type", "image/png").split(";")[0]
                    out.append(types.Part(inline_data=types.Blob(
                        mime_type=content_type,
                        data=resp.content,
                    )))
                except Exception as e:
                    logger.warning(f"Failed to download image {p['url']}: {e}")
        return out

    async def get_answer(self, prompt: str | list[dict], system_prompt: str = "") -> MCQAnswer:
        if isinstance(prompt, list):
            contents = await self._to_gemini_parts(prompt)
        else:
            contents = prompt

        # Web search disabled for answer calls — native schema enforcement
        # (response_schema + response_mime_type) is only legal when tools are
        # not attached.
        gen_config = types.GenerateContentConfig(
            temperature=0,
            system_instruction=system_prompt or None,
            response_mime_type="application/json",
            response_schema=MCQAnswer,
        )
        thinking = self._build_thinking_config()
        if thinking:
            gen_config.thinking_config = thinking

        timeout_s = self.config.timeout_ms / 1000
        response = await asyncio.wait_for(
            self.client.aio.models.generate_content(
                model=self.config.model,
                contents=contents,
                config=gen_config,
            ),
            timeout=timeout_s,
        )
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, MCQAnswer):
            return parsed
        # Defensive fallback: SDK did not populate `parsed` — validate the raw text.
        text = (response.text or "").strip().removeprefix("```json").removesuffix("```").strip()
        return MCQAnswer.model_validate_json(text)

    async def get_batch_answer(
        self, prompt: str | list[dict], system_prompt: str = "",
    ) -> tuple[BatchMCQAnswer, TokenUsage]:
        if isinstance(prompt, list):
            contents = await self._to_gemini_parts(prompt)
        else:
            contents = prompt

        gen_config = types.GenerateContentConfig(
            temperature=0,
            system_instruction=system_prompt or None,
            response_mime_type="application/json",
            response_schema=BatchMCQAnswer,
        )
        thinking = self._build_thinking_config()
        if thinking:
            gen_config.thinking_config = thinking

        timeout_s = self.config.timeout_ms / 1000
        response = await asyncio.wait_for(
            self.client.aio.models.generate_content(
                model=self.config.model,
                contents=contents,
                config=gen_config,
            ),
            timeout=timeout_s,
        )
        usage = _gemini_usage(response)
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, BatchMCQAnswer):
            return parsed, usage
        text = (response.text or "").strip().removeprefix("```json").removesuffix("```").strip()
        if not text:
            candidates = getattr(response, "candidates", None) or []
            finish = getattr(candidates[0], "finish_reason", None) if candidates else None
            prompt_feedback = getattr(response, "prompt_feedback", None)
            block = getattr(prompt_feedback, "block_reason", None) if prompt_feedback else None
            raise ValueError(
                f"Gemini returned empty response (finish_reason={finish}, "
                f"block_reason={block})"
            )
        return BatchMCQAnswer.model_validate_json(text), usage

    async def get_explanation(
        self, prompt: str | list[dict], system_prompt: str = "",
    ) -> tuple[ExplanationResponse, TokenUsage]:
        if isinstance(prompt, list):
            contents = await self._to_gemini_parts(prompt)
        else:
            contents = prompt

        gen_config = types.GenerateContentConfig(
            temperature=0.3,
            system_instruction=system_prompt or None,
            response_mime_type="application/json",
            response_schema=ExplanationResponse,
        )
        thinking = self._build_thinking_config()
        if thinking:
            gen_config.thinking_config = thinking

        timeout_s = self.config.timeout_ms / 1000
        response = await asyncio.wait_for(
            self.client.aio.models.generate_content(
                model=self.config.model,
                contents=contents,
                config=gen_config,
            ),
            timeout=timeout_s,
        )
        usage = _gemini_usage(response)
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, ExplanationResponse):
            return parsed, usage
        text = (response.text or "").strip().removeprefix("```json").removesuffix("```").strip()
        return ExplanationResponse.model_validate_json(text), usage

    async def get_solution_v2(
        self, prompt: str | list[dict], system_prompt: str = "",
    ) -> tuple[SolutionV2, TokenUsage]:
        if isinstance(prompt, list):
            contents = await self._to_gemini_parts(prompt)
        else:
            contents = prompt

        gen_config = types.GenerateContentConfig(
            temperature=0.3,
            system_instruction=system_prompt or None,
            response_mime_type="application/json",
            response_schema=SolutionV2,
        )
        thinking = self._build_thinking_config()
        if thinking:
            gen_config.thinking_config = thinking

        timeout_s = self.config.timeout_ms / 1000
        response = await asyncio.wait_for(
            self.client.aio.models.generate_content(
                model=self.config.model,
                contents=contents,
                config=gen_config,
            ),
            timeout=timeout_s,
        )
        usage = _gemini_usage(response)
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, SolutionV2):
            return parsed, usage
        text = (response.text or "").strip().removeprefix("```json").removesuffix("```").strip()
        return SolutionV2.model_validate_json(text), usage

    async def get_citations(self, prompt: str) -> tuple[list[Citation], TokenUsage]:
        # Gemini doesn't support response_mime_type with tools (Google Search),
        # so we parse the JSON response manually and validate with Pydantic.
        response = await self.client.aio.models.generate_content(
            model=self.config.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0,
            ),
        )
        text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
        # Gemini's grounded output can't use response_mime_type=application/json
        # alongside tools, so it occasionally emits raw control characters (e.g.
        # literal newlines) inside string values. Parse with strict=False to
        # tolerate those, then validate with Pydantic.
        data = json.loads(text, strict=False)
        return CitationListResponse.model_validate(data).citations, _gemini_usage(response)

    async def count_input_tokens(
        self, prompt: str | list[dict], system_prompt: str = "",
    ) -> int:
        if isinstance(prompt, list):
            contents = await self._to_gemini_parts(prompt)
        else:
            contents = prompt
        # System prompt isn't counted via contents; count separately and add.
        resp = await self.client.aio.models.count_tokens(
            model=self.config.model, contents=contents,
        )
        total = int(getattr(resp, "total_tokens", 0) or 0)
        if system_prompt:
            sys_resp = await self.client.aio.models.count_tokens(
                model=self.config.model, contents=system_prompt,
            )
            total += int(getattr(sys_resp, "total_tokens", 0) or 0)
        return total
