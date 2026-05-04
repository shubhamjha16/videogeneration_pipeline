from typing import Literal

from pydantic import BaseModel, model_validator


Status = Literal["Matched", "Manual_Review", "QB_Updated", "Error"]


class TokenUsage(BaseModel):
    """Normalized per-call token usage across providers.

    Providers expose usage differently; clients map their native shape into
    this unified record so cost math is provider-agnostic.
    """
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0


class Pricing(BaseModel):
    """USD price per 1M tokens for a single model.

    Dimensions a provider doesn't bill for should be set to 0 (e.g. OpenAI /
    Gemini has no separate cache-write charge; QWEN has no cache
    pricing at all today).
    """
    input_per_mtok: float
    cached_input_per_mtok: float = 0.0
    cache_write_per_mtok: float = 0.0
    output_per_mtok: float


PipelineTag = Literal["sanity_check", "explanation", "single_question"]


class LedgerEntry(BaseModel):
    """One row in the append-only usage ledger (data/usage_ledger.jsonl).

    The ledger is shared across every pipeline that makes model calls; the
    ``pipeline`` field is the discriminator. The full_run pipeline does not
    appear here — it dispatches to ``sanity_check`` / ``explanation`` and
    those pipelines tag their own rows.
    """
    ts: str
    run_id: str
    pipeline: PipelineTag = "sanity_check"
    model: str
    stage: str | None = None
    phase: str | None = None
    subject_id: int | None = None
    question_ids: list[int] = []
    call_type: Literal["verify_batch", "explanation", "citation"]
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float


class MCQAnswer(BaseModel):
    """Structured output schema for answer verification."""
    answer: Literal["A", "B", "C", "D"]
    is_numerical: bool


class SingleQuestionAnswer(BaseModel):
    """One answer within a batched verification response."""
    question_number: int
    answer: Literal["A", "B", "C", "D"]
    is_numerical: bool


class BatchMCQAnswer(BaseModel):
    """Structured output schema for batched answer verification."""
    answers: list[SingleQuestionAnswer]


class TrackingState(BaseModel):
    """Minimal resume state persisted to tracking.json.

    ``pipeline`` is self-describing: each pipeline writes its own slug so a
    misplaced file is detectable on load.
    """
    pipeline: Literal["sanity_check", "explanation"] | None = None
    status: Literal["pending", "completed"] = "pending"
    subject_id: int | None = None
    subject_ids: list[int] | None = None
    subject_index: int = 0
    max_budget_usd: float | None = None
    last_completed_id_regular: int = 0
    last_completed_id_common_data: int = 0
    phase: Literal["regular", "common_data"] = "regular"
    activity: Literal[
        "idle",
        "processing",
        "reprocessing_missing",
    ] = "idle"
    pending: list[int] = []
    stage: Literal["A", "B", "C"] = "A"
    run_id: str | None = None
    batches_completed: int = 0
    batches_completed_regular: int = 0
    batches_completed_common_data: int = 0
    questions_sanitized: int = 0

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy(cls, data):
        if isinstance(data, dict):
            if "last_completed_id" in data:
                data.setdefault("last_completed_id_regular", data["last_completed_id"])
                data.setdefault("phase", "regular")
                data.pop("last_completed_id")
            # Legacy M1/M2/M3 stage labels → collapse to "A" (replay from start).
            stage = data.get("stage")
            if stage in ("M1", "M2", "M3"):
                data["stage"] = "A"
            # Drop any legacy web-search-audit tracking fields and activity
            # labels (the audit step was removed).
            for k in (
                "ws_audit_total", "ws_audit_done",
                "ws1_audit_total", "ws1_audit_done",
                "ws2_audit_total", "ws2_audit_done",
            ):
                data.pop(k, None)
            if data.get("activity") in (
                "web_search_audit",
                "web_search_auditing",
                "web_search_audit_1",
                "web_search_audit_2",
            ):
                data["activity"] = "idle"
        return data


class ExhaustedModelRecord(BaseModel):
    """One model that a provider has reported as balance/quota-exhausted.

    Persisted to ``output_dir/exhausted_models.json``. Cleared only when the
    caller invokes ``/sanity-check/start?reset_exhausted=true`` after topping up
    the provider balance or rotating the key.
    """
    model: str
    reason: str
    status_code: int | None = None
    detected_at: str
    run_id: str | None = None
    subject_id: int | None = None


class SolutionSection(BaseModel):
    """One titled section inside ``questions_openai.solution_v2``.

    ``description`` is GitHub-flavored markdown rendered by remark+rehype on
    the frontend (math, code blocks, headings — no HTML, no GFM tables, no
    mermaid).
    """
    title: str
    description: str


class SolutionV2(BaseModel):
    """Structured-output schema for the model-generated portion of solution_v2.

    The model emits ``Concept Explanation``, optional ``Step-by-Step Solution``,
    ``Option Analysis``, and ``Final Answer``. The ``Citations`` section is
    appended in code from a separate grounded Gemini call.
    """
    sections: list[SolutionSection]


class ExplanationResponse(BaseModel):
    """Structured output schema for explanation generation.

    Each field holds markdown content (including KaTeX where applicable).
    """
    concept_explanation: str
    step_by_step_explanation: str | None = None
    option_a_analysis: str
    option_b_analysis: str
    option_c_analysis: str
    option_d_analysis: str
    final_answer: str


class SubjectConfig(BaseModel):
    subject_id: int
    name: str = ""


class ModelResponse(BaseModel):
    model: str
    answer: str
    raw_answer: str
    agreed_with_db: bool
    latency_ms: int


STATUS_V2_MAP: dict[str, int] = {
    "Matched": 1,
    "Manual_Review": 0,
    "QB_Updated": 2,
    "Error": 0,
}


def status_to_v2(status: str) -> int:
    return STATUS_V2_MAP[status]


def format_vote_string(votes: list[ModelResponse]) -> str | None:
    """Serialise per-model votes into the ai_answer column format.

    Format: "<model_name>~<answer>|<model_name>~<answer>|..." preserving
    the order in which the votes were received (cascade stage order).
    Returns None when no votes were cast (so the caller can write NULL).
    """
    if not votes:
        return None
    return "|".join(f"{v.model}~{v.answer}" for v in votes)


class VerificationResult(BaseModel):
    question_id: int
    question_type_id: int
    db_answer: str
    status: Status
    ai_answer: str | None = None
    model_responses: list[ModelResponse] = []
    total_called: int = 0
    models_failed: int = 0
    db_confidence: float = 0.0
    ai_consensus_confidence: float | None = None
    explanation_model: str | None = None
    is_numerical: bool = False


class Citation(BaseModel):
    type: Literal["web", "textbook", "article", "paper"]
    title: str
    source: str | None = None
    author: str | None = None
    url: str | None = None


class CitationListResponse(BaseModel):
    """Structured output schema for citation fetching."""
    citations: list[Citation]


class QuestionResult(BaseModel):
    question_id: int
    question_type_id: int
    db_answer: str
    status: Status
    status_v2: int | None = None
    ai_answer: str | None = None
    explanation: str | None = None
    model_responses: list[ModelResponse] = []
    confidence: float = 0.0
    ai_consensus_confidence: float | None = None
    explanation_model: str | None = None
    citation_model: str | None = None
    template_used: str | None = None
    question_display_id: str | None = None
    item_id: int | None = None  # etl_question_grouped.id for grouped children; NULL for regular bank rows
    is_grouped_child: bool = False
    subject_id: int | None = None
    topic_id: int | None = None
    topic_name: str | None = None


