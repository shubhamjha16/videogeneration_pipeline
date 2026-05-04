import os
from abc import ABC, abstractmethod

from dotenv import load_dotenv

from src.config.pipeline_config import ModelConfig
from src.schema.domain import (
    BatchMCQAnswer,
    Citation,
    ExplanationResponse,
    MCQAnswer,
    SolutionV2,
    TokenUsage,
)

load_dotenv()


class BaseAIClient(ABC):
    def __init__(self, config: ModelConfig):
        self.config = config
        self.api_key = os.environ[config.api_key_env]

    @abstractmethod
    async def get_answer(self, prompt: str | list[dict], system_prompt: str = "") -> MCQAnswer:
        """Returns structured MCQ answer. (Legacy single-question path — unused by runtime cascade.)"""

    @abstractmethod
    async def get_batch_answer(
        self, prompt: str | list[dict], system_prompt: str = "",
    ) -> tuple[BatchMCQAnswer, TokenUsage]:
        """Returns (batch answers, token usage) for cost accounting."""

    @abstractmethod
    async def get_explanation(
        self, prompt: str | list[dict], system_prompt: str = "",
    ) -> tuple[ExplanationResponse, TokenUsage]:
        """Returns (structured explanation, token usage)."""

    @abstractmethod
    async def get_solution_v2(
        self, prompt: str | list[dict], system_prompt: str = "",
    ) -> tuple[SolutionV2, TokenUsage]:
        """Returns (structured ``SolutionV2``, token usage).

        Used by the single-question pipeline to produce the model-generated
        portion of ``questions_openai.solution_v2`` — a list of titled
        markdown sections (Concept Explanation / Step-by-Step Solution /
        Option Analysis / Final Answer). Citations are appended in code from
        a separate grounded Gemini call.
        """

    @abstractmethod
    async def get_citations(self, prompt: str) -> tuple[list[Citation], TokenUsage]:
        """Returns (citations, token usage). Only implemented by grounded client."""

    @abstractmethod
    async def count_input_tokens(
        self, prompt: str | list[dict], system_prompt: str = "",
    ) -> int:
        """Exact input-token count via the provider SDK (or offline tokenizer).

        Used by the pre-call budget gate. Should be cheap: offline for OpenAI
        via tiktoken, network for Gemini / Anthropic via their native
        count_tokens endpoints.
        """
