# EaseToLearn — Video Generation Architecture

This document defines the industrial architecture of the Autonomous Video Factory. The system uses an **Adaptive Agentic RAG** orchestration to generate high-fidelity educational content with zero human intervention.

## 🫀 The Master Graph (Technical Schematic)

```text
========================================================================================
                      EASETOLEARN AI VIDEO FACTORY - SYSTEM BLUEPRINT
========================================================================================

    [ EXTERNAL INPUT ]             [ INTELLIGENCE LAYER ]            [ OBSERVABILITY ]
    Curriculum HTML  ──────┐        (Gemma 4 Orchestration)          (Mission Control)
                           │                                                 │
                           ▼                                                 ▼
    ┌────────────────────────────────────────────────────────┐       ┌───────────────┐
    │                  THE DIRECTOR AGENT                    │◀─────▶│ LIVE TELEMETRY │
    │           (Powered by Gemma 4 Intelligence)            │       └───────────────┘
    └──────────────────────────┬─────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            │        ADAPTIVE RESEARCH LOOP       │
            ▼                                     ▼
    ┌───────────────┐                     ┌───────────────┐
    │ RESEARCH NODE │────────────────────▶│ DISTILLATION  │
    │ (SearXNG 70+) │                     │   (Gemma 4)   │
    └───────┬───────┘                     └───────┬───────┘
            │                                     │
            ▼                                     ▼
    ┌───────────────┐                     ┌───────────────┐
    │   OPEN WEB    │                     │KNOWLEDGE BASE │
    │ (Global Brain)│                     │(Local Memory) │
    └───────────────┘                     └───────┬───────┘
                                                  │
            ┌─────────────────────────────────────┘
            ▼
    ┌───────────────┐        ┌───────────────┐        ┌───────────────┐
    │  VISION NODE  │───────▶│  PATH ROUTER  │───────▶│ MEDIA ENGINE  │
    │ (Imagen / SD) │        │ (Mode Logic)  │        │ (FFmpeg/Glue) │
    └───────────────┘        └──────┬────────┘        └──────┬────────┘
                                    │                        │
            ┌───────────────────────┼────────────────────────┴───────┐
            ▼                       ▼                                ▼
    ┌───────────────┐       ┌───────────────┐                ┌───────────────┐
    │  MANIM PATH   │       │   PPT PATH    │                │ HEYGEN PATH   │
    │ (Scientific)  │       │ (Educational) │                │ (Talking Head)│
    └───────┬───────┘       └───────┬───────┘                └───────┬───────┘
            │                       │                                │
            ▼                       ▼                                ▼
    ┌───────────────┐       ┌───────────────┐                ┌───────────────┐
    │ HEALER AGENT  │       │  PPT CRITIC   │                │ SUBTITLE ENG  │
    │ (Self-Repair) │       │ (QC Review)   │                │ (Kinetic)     │
    └───────┬───────┘       └───────┬───────┘                └───────┬───────┘
            │                       │                                │
            └───────────────────────┼────────────────────────────────┘
                                    ▼
                          ┌───────────────────┐
                          │    S3 GATEWAY     │
                          │ (ap-south-1 IDR)  │
                          └─────────┬─────────┘
                                    ▼
                          [ WEBHOOK HANDOVER ]
========================================================================================
```

---

## 🛠 Production Path Specifications

### 1. MANIM PATH (Scientific Accuracy)
*   **Target**: Maths, Physics, Biology, Medical (FMGE/NEET).
*   **Visuals**: Mathematical animations, anatomical diagrams.
*   **Self-Healing**: Uses the **Healer Agent** to autonomously fix Python rendering errors by searching web documentation.

### 2. PRESENTATION PATH (High Efficiency)
*   **Target**: UPSC, History, Geography, Case Studies.
*   **Visuals**: Animated "Doodle" slides with kinetic bullet points.
*   **Control**: Uses the **PPT Critic** to peer-review slide layouts before final export.

### 3. EXPLAINER PATH (Generative Narrative)
*   **Target**: Abstract concepts and high-impact storytelling.
*   **Visuals**: Cinematographic metaphors (e.g., ticking clocks, molecular vistas) using generative video strategies.

### 4. PERSONALIZED PATH (Human Avatars)
*   **Target**: Personal tutor engagements and short motivational snippets.
*   **Visuals**: HeyGen AI Avatars with lip-synced narration and kinetic subtitles.

---

## 📊 External Intelligence Matrix

| Service | Role | Model/Provider |
| :--- | :--- | :--- |
| **Gemma 4** | Director | Agentic orchestration (Local) |
| **SearXNG** | Research | Privacy-focused Metasearch |
| **Gemini / Imagen** | Vision | Generative concept diagrams |
| **ElevenLabs** | TTS | Neural voice synthesis (Neha) |
| **HeyGen** | Avatars | AI Video Avatars |
| **AWS S3** | Cloud | Persistent storage (ap-south-1) |

---

## 🛰 Observability
All internal events are streamed via the **Factory Portal**. 
- **🔍 Research**: Telemetry highlighted in Golden Yellow.
- **📚 Knowledge**: Telemetry highlighted in Emerald Green.
- **🚨 Healer**: Pulsing Red alerts when self-repair is active.
