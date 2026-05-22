# Bug Fix Count Summary

Date: 2026-04-13

## Concrete bugs fixed so far

1. Job-state race in `_load_jobs()` assignment without lock (`api_bridge.py`).
2. Over-broad `BaseException` in pipeline path (`api_bridge.py`).
3. Corrupt-file archival failure silently swallowed (`api_bridge.py`).
4. Mutable internal job state returned directly from `/render` (`api_bridge.py`).
5. Mutable internal job state returned directly from `/jobs` and `/status/{job_id}` (`api_bridge.py`).
6. Silent-audio fallback pacing mismatch (`tts_generator.py`).
7. Bare `except` in slide font loading fallback (`ppt_engine/slide_generator.py`).
8. Silent `except: pass` in explainer cleanup (`explainer_generator.py`).
9. Silent broad catch in discovery probing path (`scratch/discover_muapi_endpoint.py`).
10. Subtitle cleanup crash risk when `VideoFileClip` initialization fails (`autonomous_graph.py`).
11. Missing env var guard in discovery utility (`scratch/discover_muapi_endpoint.py`).
12. `_save_jobs()` persistence failures now raise instead of being silently swallowed (`api_bridge.py`).
13. Webhook retry now catches `requests.RequestException` instead of all exceptions (`api_bridge.py`).
14. Groq retry now treats JSON/schema/type parse errors as non-retryable (`autonomous_graph.py`).
15. Vision fallback now emits structured telemetry when concept image generation fails (`autonomous_graph.py`).
16. Architect duration fallback now logs structured telemetry when audio duration probing fails (`autonomous_graph.py`).
17. PPT critic failure now forces replanning instead of auto-approving (`autonomous_graph.py`).
18. PPT TTS node now fails fast with explicit node error on slide TTS failure instead of silently degrading (`autonomous_graph.py`).
19. Cleanup/hygiene failures now emit structured fallback telemetry (`autonomous_graph.py`).
20. `_save_jobs()` failures are now context-handled via `_safe_save_jobs()` with fatal mapping for enqueue paths (`api_bridge.py`).
21. Explainer failure now triggers automatic presentation-path recovery pipeline (`autonomous_graph.py`).
22. HeyGen failure now triggers automatic presentation-path recovery pipeline (`autonomous_graph.py`).
23. Fallback policy in critical non-presentation nodes now routes through a unified recovery helper (`autonomous_graph.py`).

## Total

**23 concrete bugs fixed.**

## Notes

- Prior ranges like "8–20" or "11–23" were risk estimates for *potential* bugs from static heuristics, not confirmed bug counts.
- The count above includes only concrete issues that were directly remediated in code.
