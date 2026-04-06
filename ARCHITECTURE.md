# EaseToLearn — Video Generation Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          TONY AI (Spring Boot)                              │
│              POST /render {topic, html, render_mode, with_avatar}           │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FastAPI  —  api_bridge.py                            │
│                                                                             │
│   POST /render  →  job_id (immediate)                                       │
│   GET  /status/{job_id}  →  {status, video_url}                             │
│   Webhook  →  Spring Boot callback when done                                │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   LangGraph  —  autonomous_graph.py                         │
│                                                                             │
│   ① DIRECTOR NODE                                                           │
│      html_parser → parse Tony AI HTML                                       │
│      Claude Opus 4.6 → render_mode + scenes                                 │
│      (user render_mode overrides Claude if provided)                        │
│                │                                                            │
│                ▼                                                            │
│   ② VISION NODE                                                             │
│      Gemini Imagen 4.0 → concept diagram PNG                                │
│      (manim mode only — skipped for presentation)                           │
│                │                                                            │
│                ▼                                                            │
│   ③ ARCHITECT NODE                                                          │
│         render_mode?                                                        │
│        ┌────────┴────────┐                                                  │
│        ▼                 ▼                                                  │
│     "manim"        "presentation"                                           │
│        │                 │                                                  │
│        │                 ▼                                                  │
│        │    ┌────────────────────────────┐                                 │
│        │    │   PPT Engine               │                                 │
│        │    │   ppt_engine/              │                                 │
│        │    │                            │                                 │
│        │    │  Groq llama-3.3-70b        │                                 │
│        │    │  → slide planner           │                                 │
│        │    │  → layouts + narration     │                                 │
│        │    │                            │                                 │
│        │    │  slide_generator.py        │                                 │
│        │    │  → 1920x1080 PNG           │                                 │
│        │    │  → 7 layout types:         │                                 │
│        │    │    chaos_chapter           │                                 │
│        │    │    title_card              │                                 │
│        │    │    bullets                 │                                 │
│        │    │    big_statement           │                                 │
│        │    │    steps                   │                                 │
│        │    │    two_column              │                                 │
│        │    │    key_highlight           │                                 │
│        │    │    summary                 │                                 │
│        │    │                            │                                 │
│        │    │  tts_generator.py          │                                 │
│        │    │  → ElevenLabs (Neha)       │                                 │
│        │    │  → Mac say fallback        │                                 │
│        │    │                            │                                 │
│        │    │  with_avatar=True?         │                                 │
│        │    │  → avatar_generator.py     │                                 │
│        │    │    logo / human / pro      │                                 │
│        │    │    moving mouth + blink    │                                 │
│        │    │                            │                                 │
│        │    │  ffmpeg → clips → MP4      │                                 │
│        │    └────────────┬───────────────┘                                 │
│        │                 │                                                  │
│        ▼                 │                                                  │
│  template_renderer       │                                                  │
│  → Manim script          │                                                  │
│                │         │                                                  │
│                ▼         ▼                                                  │
│   ④ SUPERVISOR NODE                                                         │
│      Manim render → EaseToLearnScene.mp4                                    │
│      tts_generator → per-scene MP3                                          │
│      ffmpeg → stitch video + audio                                          │
│      S3 upload → ap-south-1                                                 │
│                │                                                            │
│                ▼                                                            │
│      render error?  attempt < 3?                                            │
│        ┌──────┴──────┐                                                      │
│       yes            no                                                     │
│        ▼              ▼                                                     │
│   ⑤ HEALER NODE    video_url                                                │
│   Claude Opus                                                               │
│   fixes Manim script                                                        │
│   → retry supervisor                                                        │
│                                                                             │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AWS S3  —  ap-south-1                               │
│                    s3://{bucket}/videos/{topic}.mp4                         │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              Webhook → Spring Boot → Student sees video                     │
└─────────────────────────────────────────────────────────────────────────────┘


EXTERNAL SERVICES
─────────────────
  Claude Opus 4.6    → Director (scene planning) + Healer (script fixing)
  Groq llama-3.3-70b → PPT slide planner
  Gemini Imagen 4.0  → Concept diagram PNG (manim only)
  ElevenLabs         → TTS, Neha voice (eleven_multilingual_v2)
  AWS S3             → Video storage, ap-south-1


RENDER MODES
────────────
  manim        → Maths, Physics, Medical, Chemistry  (animated Manim)
  presentation → English, UPSC, MBA, History         (PPT doodle slides)
  human_face   → (future)


WHAT'S PENDING
──────────────
  [ ] PPT engine as proper LangGraph graph (ppt_graph.py)
  [ ] S3 upload for PPT output
  [ ] Spring Boot ↔ FastAPI E2E test
  [ ] Docker + ECS deploy
  [ ] ElevenLabs quota fix
  [ ] Error monitoring (CloudWatch / Sentry)
```
