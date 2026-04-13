# Bug Audit Report

Date: 2026-04-13
Scope: full repository static audit + basic runtime sanity checks

## Checks executed

1. `python -m compileall -q .`
2. `rg -n "except:\\s*pass|except BaseException|Thread\\(" *.py ppt_engine/*.py`
3. Manual source review of `api_bridge.py`, `tts_generator.py`, and error-handling hotspots.

---

## Confirmed / High-Confidence Bugs

### 1) Job-state race condition in API workers (data corruption risk)
**Severity:** High  
**File:** `api_bridge.py`  

`_load_jobs()` writes to the global `jobs` object without acquiring `_jobs_lock`. At the same time, request handlers and worker threads mutate `jobs` while holding the lock. This creates an inconsistent locking model where one thread can replace the dictionary while another thread is mutating it.

**Why this is a bug:**
- Lost updates can happen when a thread assigns `jobs = data` during concurrent mutation.
- Readers may observe partially inconsistent state across requests.

**Evidence lines:**
- Global assignment in `_load_jobs`: `jobs = data`.
- Concurrent locked mutation in `_run_pipeline` and `/render` handlers.

---

### 2) Over-broad exception capture blocks clean process termination
**Severity:** High  
**File:** `api_bridge.py`

`_run_pipeline()` uses `except BaseException as e:` around pipeline execution.

**Why this is a bug:**
- `BaseException` catches `KeyboardInterrupt` and `SystemExit`, which are normally used for graceful shutdown.
- In production, this can prevent workers from exiting promptly on stop/redeploy signals.

**Expected fix direction:** Catch `Exception` instead of `BaseException` unless there is an explicit, documented reason.

---

### 3) Silent-audio fallback duration is inconsistent with its own comment
**Severity:** Medium  
**File:** `tts_generator.py`

Code comment says `~12 words per second`, but duration uses `word_count / 3.0`.

**Why this is a bug:**
- The implementation is 4x slower than documented behavior.
- In fallback scenarios, this inflates timeline length and can desync scene pacing.

**Expected behavior examples:**
- 120 words at 12 words/sec should be ~10s.
- Current code produces 40s.

---

### 4) Bare `except: pass` suppresses persistence corruption diagnostics
**Severity:** Medium  
**File:** `api_bridge.py`

In `_load_jobs()`, archival of a corrupt job file does:
```python
except: pass
```

**Why this is a bug:**
- It hides the reason archival failed (permissions, readonly FS, path issues).
- Incident debugging becomes harder exactly when data corruption is already occurring.

**Fix direction:** Catch `Exception as e` and log at least one-line diagnostics.

---

## Likely Reliability Issues (need targeted validation)

### 5) Shared mutable job object exposure from API responses
**Severity:** Medium (Likely)
**File:** `api_bridge.py`

`/jobs` and `/status/{job_id}` return direct references from `jobs`. While FastAPI usually serializes immediately, returning internal mutable objects can still create maintenance hazards and accidental shared-state leakage in future refactors.

**Fix direction:** return copies (`dict(...)`, deep copy where nested fields exist).

---

## Summary

The most urgent problems are in concurrent job-state management and shutdown-safe exception handling in `api_bridge.py`. The TTS fallback pacing mismatch is medium severity but likely visible to end users when upstream TTS fails.
