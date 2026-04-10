# EaseToLearn — Video Generation Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FACTORY PORTAL (Mission Control)                   │
│             Dashboard for Batch Control, Overrides, & Telemetry             │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
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
│                │                                                            │
│                ▼                                                            │
│   ② VISION NODE                                                             │
│      Gemini Imagen 4.0 → concept diagram PNG                                │
│                │                                                            │
│                ▼                                                            │
│   ③ ROUTER (render_mode?)                                                   │
│        ┌────────┴────────┬───────────────┬───────────────┐                  │
│        ▼                 ▼               ▼               ▼                  │
│     "manim"        "presentation"    "explainer"    "user_generated"        │
│        │                 │               │               │                  │
│        ▼                 ▼               ▼               ▼                  │
│  ┌───────────┐     ┌───────────┐   ┌───────────┐   ┌───────────┐            │
│  │ Architect │     │ PPT Engine│   │ Explainer │   │ HeyGen    │            │
│  │ (Manim)   │     │ (Slides)  │   │ (B-Roll)  │   │ (Avatars) │            │
│  └─────┬─────┘     └─────┬─────┘   └─────┬─────┘   └─────┬─────┘            │
│        │                 │               │               │                  │
│        ▼                 ▼               ▼               ▼                  │
│  ┌───────────┐     ┌───────────┐   ┌───────────┐   ┌───────────┐            │
│  │ Supervisor│     │ PPT Video │   │ Stitching │   │ Subtitles │            │
│  │ (Rendering)     │ (FFmpeg)  │   │ (Generative)  │ (Kinetic) │            │
│  └─────┬─────┘     └─────┬─────┘   └─────┬─────┘   └─────┬─────┘            │
│        │                 │               │               │                  │
│        └─────────────────┴───────┬───────┴───────────────┘                  │
│                                  ▼                                          │
│                            ④ S3 UPLOAD                                      │
│                        video_url / S3 bucket                                │
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
```

## Production Paths

### 1. MANIM PATH (Academic Animation)
*   **Target**: Maths, Physics, Chemistry, Medical MCQs.
*   **Visuals**: Mathematical animations, formula derivations, code-based diagrams.
*   **Tech**: [manim](https://www.manim.community/), LaTeX, Gemini Imagen (concept diagrams).

### 2. PRESENTATION PATH (Doodle Slides)
*   **Target**: English Grammar, UPSC GS, History, Case Studies.
*   **Visuals**: 1920x1080 animated "doodle" slides with icons and bullets.
*   **Tech**: [ppt_engine](file:///Users/apple/Desktop/easetolearn.videogeneration/ppt_engine/), Groq (slide planning), tts_generator.

### 3. EXPLAINER PATH (Narrative B-Roll) [NEW]
*   **Target**: Abstract conceptual deep-dives, storytelling.
*   **Visuals**: Cinematographic metaphors (e.g., falling dominoes, clockwork, train rails) using generative video or stock-style clips.
*   **Tech**: [explainer_generator.py](file:///Users/apple/Desktop/easetolearn.videogeneration/explainer_generator.py) (Higgsfield strategy).

### 4. USER GENERATED PATH (Talking Head) [NEW]
*   **Target**: Personal tutor updates, news snippets, highly engaging social-style educational clips.
*   **Visuals**: HeyGen avatar + "Insta Reels" style kinetic subtitles (high-impact, word-by-word highlights).
*   **Tech**: [heygen_generator.py](file:///Users/apple/Desktop/easetolearn.videogeneration/heygen_generator.py), [subtitle_generator.py](file:///Users/apple/Desktop/easetolearn.videogeneration/subtitle_generator.py) (MoviePy kinetic engine).

## External Integrations
| Service | Role | Model/Technology |
| :--- | :--- | :--- |
| **Claude (Anthropic)** | Director | Scene planning & script orchestration |
| **Groq** | PPT Planner | Fast Llama-3.3-70b inference |
| **Gemini (Google)** | Vision | Generative concept diagrams |
| **ElevenLabs** | TTS | High-fidelity multilingual voices (Neha) |
| **HeyGen** | Avatar | AI Lip-Sync & Video Avatars |
| **Higgsfield** | Explainer | Generative cinematic B-roll |
| **AWS S3** | Storage | Video hosting in ap-south-1 |

## Components
*   **[api_bridge.py](file:///Users/apple/Desktop/easetolearn.videogeneration/api_bridge.py)**: Entry point for the factory.
*   **[autonomous_graph.py](file:///Users/apple/Desktop/easetolearn.videogeneration/autonomous_graph.py)**: The brain of the system, managing state and routing.
*   **[director_agent.py](file:///Users/apple/Desktop/easetolearn.videogeneration/director_agent.py)**: The creative lead that selects render modes.
*   **[subtitle_generator.py](file:///Users/apple/Desktop/easetolearn.videogeneration/subtitle_generator.py)**: Handles the kinetic "Insta-style" typography.
*   **[factory_portal/](file:///Users/apple/Desktop/easetolearn.videogeneration/factory_portal/)**: The web-based Mission Control interface for real-time monitoring.
