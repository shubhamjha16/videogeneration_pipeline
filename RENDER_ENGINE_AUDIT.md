# EaseToLearn — Render Engine Audit

This document tracks the industrialization status, reliability, and verification of the four primary video generation engines.

## Status Summary

| Engine | Path | Status | Reliability | Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **Manim** | Academic | **Battle-tested** | High (Self-healing) | `render_stderr.txt` (Kinematics) |
| **PPT** | Presentation | **Battle-tested** | High (Deterministic) | Skull, EDH, Carpopedal videos |
| **Explainer** | B-Roll | **Partial** | Medium (Placeholder fallbacks) | Local verify script (Counting) |
| **HeyGen** | Avatar | **Untested** | Unknown (Code-complete) | N/A |

---

## 1. Manim Engine
*   **Role**: Primary engine for Science, Maths, and Medical animations.
*   **Process**: `template_renderer.py` → Deterministic Python scripts → `manim -ql` subprocess.
*   **Code Completeness**: **100% (Baseline)**.
    - **Render Depth**: ~800 lines in `template_renderer.py`. 
    - **Visual Diversity**: 14 visual types, all fully implemented.
    - **Config Gaps**: **None**. All keys finalized in `config.py` and `.env.template`.
*   **Dependencies & Network**:
    - **Required**: `manim`, `ffmpeg`, `LaTeX (texlive)`, `Cairo/Pango` (All included in `Dockerfile`).
    - **Connectivity**: **ElevenLabs TTS** only.
    - **Offline Ability**: **Success**. Silent WAV fallback enables full offline render if needed.
*   **Output Reliability**: **High**. `healer_node` catches failures and retries up to 3x with Groq-powered fixes.
*   **Safety Fallbacks**:
    - **Render Error**: `healer_node` reads stderr; Groq fixes script; retries (Max 3).
    - **TTS Error**: 4-level chain (ElevenLabs → Mac 'say' → gTTS → Silent WAV).
    - **Image Error**: If Gemini fails, template renderer draws a **dark Rectangle** placeholder.
*   **Verification**: **Success**. `render_stderr.txt` confirms kinematics rendered fully without manual intervention.

## 2. PPT Engine
*   **Role**: Fast, clean animated slides for general subjects.
*   **Process**: `slide_generator.py` → PIL builds 1920x1080 PNGs → ffmpeg image+audio integration → concat.
*   **Code Completeness**: **100% (Visual)**.
    - **Render Depth**: ~900 lines in `slide_generator.py`.
    - **Visual Diversity**: 16 layouts, all implemented with PIL.
    - **Known Gaps**: **Caveat font missing** (`assets/fonts/Caveat.zip` not found). Currently falls back to DejaVu—functional but visual branding varies.
*   **Dependencies & Network**:
    - **Required**: `PIL (Pillow)`, `ffmpeg`, `DejaVu fonts` (All included in `Dockerfile`).
    - **Connectivity**: **ElevenLabs TTS** only.
    - **Offline Ability**: **Success**. gTTS needs internet but silent WAV is the final logic-safe fallback.
*   **Output Reliability**: **High**. `_fallback_split` exists if Groq fails. ffmpeg is deterministic.
*   **Safety Fallbacks**:
    - **Layout Error**: Layout exception → automatically falls back to **Bullets** layout.
    - **Clip Error**: If a clip is missing (e.g. TTS fail), it is **skipped with warning** to prevent total stall.
    - **Groq Error**: `_fallback_split` handles long text by sentence-splitting into basic slides.
*   **Verification**: **Success**. Carpopedal, Skull, and EDH combo files prove PPT videos were stitched and delivered correctly.

## 3. Explainer Engine
*   **Role**: Narrative B-roll using generative video and imagery.
*   **Process**: `explainer_generator.py` → MoviePy composite of Higgsfield video + Imagen PNGs + TTS.
*   **Code Completeness**: **~60% (Partial)**.
    - **Render Depth**: ~200 lines in `explainer_generator.py`.
    - **Implementation**: Counting metaphor is solid; `generative_video` path is currently a **shell** around Higgsfield.
    - **Config Gaps**: `HIGGSFIELD_API_ID/KEY` placeholders added to `config.py` for future injection.
*   **Dependencies & Network**:
    - **Required**: `MoviePy`, `ffmpeg`, `PIL` (All included in `Dockerfile`).
    - **Connectivity**: **Higgsfield API** (Generative B-roll) + **ElevenLabs TTS**.
    - **Offline Ability**: **Partial**. Counting metaphors work offline; generative video falls to placeholder Zoom clips.
*   **Output Reliability**: **Partial**. Counting metaphor scenes are solid. Generative video scenes now fall back to Imagen assets.
*   **Safety Fallbacks**:
    - **Render Error**: `_create_fallback_clip` produces a **dark background + text** card.
    - **Higgsfield Error**: Automatically falls back to **Imagen cinematic zoom** of the prompt concept.
    - **Image Error**: Falls to a plain **text card** if the Imagen asset is missing.
*   **Verification**: **Partial**. `verify_explainer_counting.py` ran locally. Full pipeline with Higgsfield has never been tested end-to-end.

## 4. HeyGen Engine
*   **Role**: Talking-head AI avatars for personal updates.
*   **Process**: `heygen_generator.py` → upload audio → HeyGen v2 API → poll → download → subtitle overlay.
*   **Code Completeness**: **~40% (Skeleton)**.
    - **Render Depth**: ~180 lines total. API plumbing is complete but untested live.
    - **Config Gaps**: `HEYGEN_API_KEY` placeholder verified. `avatar_id` is still a terminal-level placeholder.
*   **Dependencies & Network**:
    - **Required**: `MoviePy`, `PIL` (All included in `Dockerfile`).
    - **Connectivity**: **HeyGen API is the entire path**. No network = no video output.
    - **Offline Ability**: **None**. Black mock video is the only output (not production usable).
*   **Output Reliability**: **Untested**. Code structure is correct, but requires real API credentials.
*   **Safety Fallbacks**:
    - **Key Missing**: Generates a **black ColorClip mock** video with audio (pipeline continues).
    - **API Timeout**: Returns `None` after 40 polls (10 min); `fusion_node` catches and sets error status.
    - **Subtitle Error**: `subtitle_node` **skips gracefully** if the video is missing, delivering the raw file.
*   **Verification**: **None**. Zero evidence of a successful HeyGen API call in the codebase.
