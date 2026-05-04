import asyncio
import json

from openai import AsyncOpenAI

from src.clients.base_client import BaseAIClient
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


def _openai_responses_usage(response) -> TokenUsage:
    u = getattr(response, "usage", None)
    if not u:
        return TokenUsage()
    # Responses API: input_tokens, output_tokens, input_tokens_details.cached_tokens
    input_total = getattr(u, "input_tokens", 0) or 0
    details = getattr(u, "input_tokens_details", None)
    cached = getattr(details, "cached_tokens", 0) if details else 0
    cached = cached or 0
    return TokenUsage(
        input_tokens=max(0, input_total - cached),
        cached_input_tokens=cached,
        cache_write_tokens=0,
        output_tokens=getattr(u, "output_tokens", 0) or 0,
    )


def _openai_chat_usage(response) -> TokenUsage:
    u = getattr(response, "usage", None)
    if not u:
        return TokenUsage()
    prompt_total = getattr(u, "prompt_tokens", 0) or 0
    details = getattr(u, "prompt_tokens_details", None)
    cached = getattr(details, "cached_tokens", 0) if details else 0
    cached = cached or 0
    return TokenUsage(
        input_tokens=max(0, prompt_total - cached),
        cached_input_tokens=cached,
        cache_write_tokens=0,
        output_tokens=getattr(u, "completion_tokens", 0) or 0,
    )


class OpenAICompatibleClient(BaseAIClient):
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=config.endpoint,
        )

    def _responses_reasoning_kwargs(self) -> dict:
        if self.config.reasoning_effort:
            return {"reasoning": {"effort": self.config.reasoning_effort}}
        return {}

    def _chat_reasoning_kwargs(self) -> dict:
        if self.config.reasoning_effort:
            return {"reasoning_effort": self.config.reasoning_effort}
        return {}

    @staticmethod
    def _to_responses_parts(parts: list[dict]) -> list[dict]:
        """Convert provider-neutral parts to OpenAI Responses API input format."""
        out: list[dict] = []
        for p in parts:
            if p["type"] == "text":
                out.append({"type": "input_text", "text": p["text"]})
            elif p["type"] == "image":
                data_uri = f"data:{p['media_type']};base64,{p['data']}"
                out.append({"type": "input_image", "image_url": data_uri, "detail": "high"})
            elif p["type"] == "image_url":
                out.append({"type": "input_image", "image_url": p["url"], "detail": "high"})
        return out

    @staticmethod
    def _to_chat_parts(parts: list[dict]) -> list[dict]:
        """Convert provider-neutral parts to Chat Completions format (fallback)."""
        out: list[dict] = []
        for p in parts:
            if p["type"] == "text":
                out.append({"type": "text", "text": p["text"]})
            elif p["type"] == "image":
                data_uri = f"data:{p['media_type']};base64,{p['data']}"
                out.append({"type": "image_url", "image_url": {"url": data_uri}})
            elif p["type"] == "image_url":
                out.append({"type": "image_url", "image_url": {"url": p["url"]}})
        return out

    async def get_answer(self, prompt: str | list[dict], system_prompt: str = "") -> MCQAnswer:
        timeout_s = self.config.timeout_ms / 1000
        return await asyncio.wait_for(self._get_answer_inner(prompt, system_prompt), timeout=timeout_s)

    async def _get_answer_inner(self, prompt: str | list[dict], system_prompt: str) -> MCQAnswer:
        if isinstance(prompt, list):
            content = self._to_responses_parts(prompt)
        else:
            content = prompt

        timeout_s = self.config.timeout_ms / 1000
        reasoning_kw = self._responses_reasoning_kwargs()
        temp_kw = {} if reasoning_kw else {"temperature": 0}
        try:
            # Web search disabled — structured output via `text_format`.
            response = await self.client.responses.parse(
                model=self.config.model,
                instructions=system_prompt or None,
                input=[{"role": "user", "content": content}],
                text_format=MCQAnswer,
                timeout=timeout_s,
                **reasoning_kw,
                **temp_kw,
            )
            return response.output_parsed
        except Exception:
            # Fallback for endpoints that don't support Responses API (e.g. DeepSeek)
            if isinstance(prompt, list):
                chat_content = self._to_chat_parts(prompt)
            else:
                chat_content = prompt

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": chat_content})

            chat_reasoning_kw = self._chat_reasoning_kwargs()
            chat_temp_kw = {} if chat_reasoning_kw else {"temperature": 0}
            try:
                response = await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    timeout=timeout_s,
                    **chat_reasoning_kw,
                    **chat_temp_kw,
                )
                return MCQAnswer.model_validate_json(response.choices[0].message.content)
            except Exception:
                # Final fallback: no response_format at all
                if isinstance(chat_content, str):
                    chat_content = chat_content + '\n\nRespond ONLY with JSON: {"answer": "A/B/C/D"}'
                else:
                    chat_content = chat_content + [
                        {"type": "text", "text": '\n\nRespond ONLY with JSON: {"answer": "A/B/C/D"}'}
                    ]
                messages[-1]["content"] = chat_content
                response = await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    timeout=timeout_s,
                    **chat_reasoning_kw,
                    **chat_temp_kw,
                )
                text = response.choices[0].message.content
                text = text.strip().removeprefix("```json").removesuffix("```").strip()
                return MCQAnswer.model_validate_json(text)

    async def get_batch_answer(
        self, prompt: str | list[dict], system_prompt: str = "",
    ) -> tuple[BatchMCQAnswer, TokenUsage]:
        timeout_s = self.config.timeout_ms / 1000
        return await asyncio.wait_for(self._get_batch_answer_inner(prompt, system_prompt), timeout=timeout_s)

    async def _get_batch_answer_inner(
        self, prompt: str | list[dict], system_prompt: str,
    ) -> tuple[BatchMCQAnswer, TokenUsage]:
        if isinstance(prompt, list):
            content = self._to_responses_parts(prompt)
        else:
            content = prompt

        timeout_s = self.config.timeout_ms / 1000
        reasoning_kw = self._responses_reasoning_kwargs()
        temp_kw = {} if reasoning_kw else {"temperature": 0}
        try:
            response = await self.client.responses.parse(
                model=self.config.model,
                instructions=system_prompt or None,
                input=[{"role": "user", "content": content}],
                text_format=BatchMCQAnswer,
                timeout=timeout_s,
                **reasoning_kw,
                **temp_kw,
            )
            return response.output_parsed, _openai_responses_usage(response)
        except Exception:
            if isinstance(prompt, list):
                chat_content = self._to_chat_parts(prompt)
            else:
                chat_content = prompt

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": chat_content})

            chat_reasoning_kw = self._chat_reasoning_kwargs()
            chat_temp_kw = {} if chat_reasoning_kw else {"temperature": 0}
            try:
                response = await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    timeout=timeout_s,
                    **chat_reasoning_kw,
                    **chat_temp_kw,
                )
                return (
                    BatchMCQAnswer.model_validate_json(response.choices[0].message.content),
                    _openai_chat_usage(response),
                )
            except Exception:
                if isinstance(chat_content, str):
                    chat_content = chat_content + '\n\nRespond ONLY with JSON matching the schema: {"answers": [{"question_number": 1, "answer": "A/B/C/D", "is_numerical": true/false}, ...]}'
                else:
                    chat_content = chat_content + [
                        {"type": "text", "text": '\n\nRespond ONLY with JSON matching the schema: {"answers": [{"question_number": 1, "answer": "A/B/C/D", "is_numerical": true/false}, ...]}'}
                    ]
                messages[-1]["content"] = chat_content
                response = await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    timeout=timeout_s,
                    **chat_reasoning_kw,
                    **chat_temp_kw,
                )
                text = response.choices[0].message.content
                text = text.strip().removeprefix("```json").removesuffix("```").strip()
                return BatchMCQAnswer.model_validate_json(text), _openai_chat_usage(response)

    async def get_explanation(
        self, prompt: str | list[dict], system_prompt: str = "",
    ) -> tuple[ExplanationResponse, TokenUsage]:
        timeout_s = self.config.timeout_ms / 1000
        return await asyncio.wait_for(self._get_explanation_inner(prompt, system_prompt), timeout=timeout_s)

    async def _get_explanation_inner(
        self, prompt: str | list[dict], system_prompt: str,
    ) -> tuple[ExplanationResponse, TokenUsage]:
        if isinstance(prompt, list):
            content = self._to_responses_parts(prompt)
        else:
            content = prompt

        timeout_s = self.config.timeout_ms / 1000
        reasoning_kw = self._responses_reasoning_kwargs()
        temp_kw = {} if reasoning_kw else {"temperature": 0.3}
        try:
            # Web search disabled — structured output via `text_format`.
            response = await self.client.responses.parse(
                model=self.config.model,
                instructions=system_prompt or None,
                input=[{"role": "user", "content": content}],
                text_format=ExplanationResponse,
                timeout=timeout_s,
                **reasoning_kw,
                **temp_kw,
            )
            return response.output_parsed, _openai_responses_usage(response)
        except Exception:
            # Fallback: Chat Completions with json_object mode
            if isinstance(prompt, list):
                chat_content = self._to_chat_parts(prompt)
            else:
                chat_content = prompt

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": chat_content})

            chat_reasoning_kw = self._chat_reasoning_kwargs()
            chat_temp_kw = {} if chat_reasoning_kw else {"temperature": 0.3}
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                response_format={"type": "json_object"},
                timeout=timeout_s,
                **chat_reasoning_kw,
                **chat_temp_kw,
            )
            return (
                ExplanationResponse.model_validate_json(
                    response.choices[0].message.content
                ),
                _openai_chat_usage(response),
            )

    async def get_solution_v2(
        self, prompt: str | list[dict], system_prompt: str = "",
    ) -> tuple[SolutionV2, TokenUsage]:
        timeout_s = self.config.timeout_ms / 1000
        return await asyncio.wait_for(
            self._get_solution_v2_inner(prompt, system_prompt), timeout=timeout_s,
        )

    async def _get_solution_v2_inner(
        self, prompt: str | list[dict], system_prompt: str,
    ) -> tuple[SolutionV2, TokenUsage]:
        if isinstance(prompt, list):
            content = self._to_responses_parts(prompt)
        else:
            content = prompt

        timeout_s = self.config.timeout_ms / 1000
        reasoning_kw = self._responses_reasoning_kwargs()
        temp_kw = {} if reasoning_kw else {"temperature": 0.3}
        try:
            response = await self.client.responses.parse(
                model=self.config.model,
                instructions=system_prompt or None,
                input=[{"role": "user", "content": content}],
                text_format=SolutionV2,
                timeout=timeout_s,
                **reasoning_kw,
                **temp_kw,
            )
            return response.output_parsed, _openai_responses_usage(response)
        except Exception:
            if isinstance(prompt, list):
                chat_content = self._to_chat_parts(prompt)
            else:
                chat_content = prompt

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": chat_content})

            chat_reasoning_kw = self._chat_reasoning_kwargs()
            chat_temp_kw = {} if chat_reasoning_kw else {"temperature": 0.3}
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                response_format={"type": "json_object"},
                timeout=timeout_s,
                **chat_reasoning_kw,
                **chat_temp_kw,
            )
            return (
                SolutionV2.model_validate_json(
                    response.choices[0].message.content
                ),
                _openai_chat_usage(response),
            )

    async def get_citations(self, prompt: str) -> tuple[list[Citation], TokenUsage]:
        timeout_s = self.config.timeout_ms / 1000
        reasoning_kw = self._responses_reasoning_kwargs()
        temp_kw = {} if reasoning_kw else {"temperature": 0}
        # Responses API web_search tool isn't compatible with strict
        # `text_format` structured output, so we ask for JSON in the prompt
        # and parse manually (same pattern as the Gemini grounded path).
        response = await asyncio.wait_for(
            self.client.responses.create(
                model=self.config.model,
                input=[{"role": "user", "content": prompt}],
                tools=[{"type": "web_search"}],
                timeout=timeout_s,
                **reasoning_kw,
                **temp_kw,
            ),
            timeout=timeout_s,
        )
        text = (response.output_text or "").strip()
        text = text.removeprefix("```json").removesuffix("```").strip()
        data = json.loads(text, strict=False)
        return (
            CitationListResponse.model_validate(data).citations,
            _openai_responses_usage(response),
        )

    async def count_input_tokens(
        self, prompt: str | list[dict], system_prompt: str = "",
    ) -> int:
        # tiktoken is OpenAI's own tokenizer — exact, offline, no round-trip.
        # Model-name → encoding mapping isn't always up-to-date for preview
        # variants (e.g. "gpt-5.4" isn't in tiktoken's table yet even though
        # the whole GPT-5 family uses o200k_base), so we pick by prefix.
        try:
            import tiktoken
            try:
                enc = tiktoken.encoding_for_model(self.config.model)
            except KeyError:
                model = self.config.model.lower()
                if (
                    model.startswith("gpt-5")
                    or model.startswith("gpt-4o")
                    or model.startswith("o1")
                    or model.startswith("o3")
                    or model.startswith("o4")
                ):
                    enc = tiktoken.get_encoding("o200k_base")
                else:
                    enc = tiktoken.get_encoding("cl100k_base")
        except Exception:
            text = prompt if isinstance(prompt, str) else "".join(
                p.get("text", "") for p in prompt if isinstance(p, dict) and p.get("type") == "text"
            )
            return (len(text) + len(system_prompt or "")) // 4

        if isinstance(prompt, str):
            text = prompt
        else:
            text_parts: list[str] = []
            for p in prompt:
                if not isinstance(p, dict):
                    continue
                if p.get("type") == "text":
                    text_parts.append(p.get("text", ""))
            text = "\n".join(text_parts)
        return len(enc.encode(text)) + len(enc.encode(system_prompt or ""))
