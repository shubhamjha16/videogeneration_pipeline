# EaseToLearn Pipeline Operations Runbook

## Scope
This runbook covers failure triage and retry guidance for the integrated render paths in `autonomous_graph.py`.

## 1) Operational validation pass (multi-mode)

Run one smoke job per mode with real provider keys:

1. **Manim mode**: verify render + stitch + deploy.
2. **Presentation mode**: verify planner/critic/render/tts/video/deploy.
3. **Explainer mode**: verify explainer composition + deploy.
4. **User-generated mode**: verify HeyGen + subtitles + fusion + deploy.

Record:
- `job_id`
- final `video_url`
- fallback warnings in job logs (`event=fallback`)
- any `rendering_errors`

## 2) Failure injection checklist

Inject and verify expected behavior:

- Remove `GROQ_API_KEY` → PPT planner should use fallback split; critic should auto-approve fallback path.
- Break S3 permissions temporarily → upload retries should occur, then fallback to `file://` URL.
- Force subtitle generator exception → pipeline should keep original HeyGen video and continue.
- Force long Manim render / FFmpeg stall → timeout should set explicit `rendering_errors`.

## 3) Retry and timeout policy

Current defaults:
- `MANIM_TIMEOUT_SECONDS = 600`
- `FFMPEG_TIMEOUT_SECONDS = 600`
- `GROQ_MAX_ATTEMPTS = 2`
- `S3_UPLOAD_MAX_ATTEMPTS = 3`
- `S3_RETRY_SLEEP_SECONDS = 1` (linear backoff)

Tune by environment:
- Lower timeouts for staging to detect regressions quickly.
- Keep higher timeouts in production for large jobs.
- Increase Groq attempts only if provider reliability is poor and latency budget allows.

## 4) Triage guide

When a job fails:
1. Check `rendering_errors` first (canonical error surface).
2. Check job telemetry for structured fallback warnings (`event=fallback`).
3. If deploy skipped, inspect output artifact existence in job directory.
4. Retry manually only after fixing provider/config root cause.

## 5) What auto-falls back vs manual action

Auto-fallbacks:
- Groq unavailable -> fallback planner / critic auto-approve.
- S3 upload repeated failure -> local `file://` URL.
- Subtitle overlay failure -> original HeyGen video retained.

Manual action usually required:
- Persistent Manim/FFmpeg failures.
- Repeated provider auth/permission failures.
- Missing core assets across multiple nodes.
