from src.schema.domain import Pricing, TokenUsage


def compute_cost_usd(usage: TokenUsage, pricing: Pricing) -> float:
    return (
        usage.input_tokens * pricing.input_per_mtok
        + usage.cached_input_tokens * pricing.cached_input_per_mtok
        + usage.cache_write_tokens * pricing.cache_write_per_mtok
        + usage.output_tokens * pricing.output_per_mtok
    ) / 1_000_000


def project_cost_usd(
    estimated_input_tokens: int,
    max_output_tokens: int,
    pricing: Pricing,
) -> float:
    """Conservative pre-call cost projection.

    Assumes no cached input and charges full output price on the configured
    per-call-type max output cap. Intended for the admission gate before a
    parallel fan-out — actuals are written to the ledger after the call.
    """
    return (
        estimated_input_tokens * pricing.input_per_mtok
        + max_output_tokens * pricing.output_per_mtok
    ) / 1_000_000
