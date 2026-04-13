# Potential Bugs — Full Current Inventory (Static Heuristic)

Date: 2026-04-13

This list is a **potential-bug inventory** generated from static heuristics.
It is not equivalent to confirmed runtime defects.

## 1) High-confidence potential bugs (specific lines)

No high-confidence bare-`except` bugs remain after remediation (latest static pass).

## 2) Broad exception hotspots (potential reliability bugs)

Broad `except Exception` blocks are not always wrong, but high density usually indicates hidden edge-case behavior.

- `autonomous_graph.py` — 16 occurrences (highest concentration).
- `api_bridge.py` — 7 occurrences.
- `explainer_generator.py` — 3 occurrences.
- `heygen_generator.py` — 3 occurrences.
- `higgsfield_generator.py` — 3 occurrences.
- `eleven_lip_sync.py` — 3 occurrences.
- `ppt_engine/ppt_pipeline.py` — 2 occurrences.
- `template_renderer.py` — 2 occurrences.
- `tts_generator.py` — 2 occurrences.
- `avatar_generator.py` — 1 occurrence.
- `director_agent.py` — 1 occurrence.
- `image_generator.py` — 1 occurrence.
- `infrastructure/verify_heygen.py` — 1 occurrence.
- `manim_generator.py` — 1 occurrence.
- `ppt_engine/slide_generator.py` — 1 occurrence.
- `scripts/automated_smoke_runner.py` — 1 occurrence.
- `subtitle_generator.py` — 1 occurrence.
- `text_renderer.py` — 1 occurrence.
- `verify_explainer_counting.py` — 1 occurrence.
- `verify_heygen.py` — 1 occurrence.
- `scratch/discover_muapi_endpoint.py` — 1 occurrence.

## 3) Estimated unresolved potential bug count

- High-confidence still-open potential bugs: **0**.
- Additional medium/low-confidence potential bugs: **8–20** (estimated from broad exception density and multi-stage pipeline complexity).
- Estimated total unresolved potential bugs: **8–20**.

## 4) Recommended next validation pass

1. Add targeted integration tests for `autonomous_graph.py` and `api_bridge.py` unhappy paths.
2. Add cleanup/finalizer tests for `explainer_generator.py` to verify resource release on failure.
3. Introduce a lint rule to fail CI on new bare `except:` usage.
