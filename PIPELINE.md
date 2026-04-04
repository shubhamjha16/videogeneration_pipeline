# EaseToLearn — Video Generation Pipeline

```mermaid
flowchart TD
    SB([Spring Boot\nTony AI Backend])
    SB -->|POST /render\n{topic, html}| API

    subgraph API ["FastAPI — api_bridge.py"]
        API[/POST /render/]
        API -->|returns job_id\nimmediately| SB
        API -->|background thread| GRAPH
        POLL[/GET /status\n{job_id}/]
        SB -->|poll every 5s| POLL
        WEBHOOK([Webhook callback\nvideo_url → Spring Boot])
    end

    subgraph GRAPH ["LangGraph Pipeline — autonomous_graph.py"]
        direction TB

        subgraph D ["① Director Node"]
            HP[html_parser\nparse_tony_html]
            HP -->|topic, subject\ncontent_type, concept\noptions / steps| CL
            CL([Claude Opus 4.6\nadaptive thinking\nmessages.parse])
            CL -->|render_mode\nscenes list| DOUT
            DOUT[[render_mode:\nmanim / presentation\n\nscenes: title_card,\nformula_display,\noption_highlight ...]]
        end

        subgraph V ["② Vision Node"]
            IMGCHECK{render_mode\n== manim?}
            IMGCHECK -->|yes| GEM
            IMGCHECK -->|no| SKIP1[skip\nimage = None]
            GEM([Gemini Imagen 4.0\nSubject-aware prompt\n16:9 concept diagram])
            GEM -->|PNG or None\non failure| IOUT[[image_path]]
        end

        subgraph A ["③ Architect Node"]
            MODECHECK{render_mode?}
            MODECHECK -->|manim| TR[template_renderer\nbuild_manim_script\nDeterministic — no LLM]
            MODECHECK -->|presentation| TP[tony_pipeline\nSlide + avatar video]
            TR --> SCRIPT[[scene_script.py\nEaseToLearnScene]]
            TP --> PRESOUT[[tony_ai_video.mp4\npresentation done]]
        end

        subgraph S ["④ Supervisor Node"]
            MAN[Manim render\n-ql EaseToLearnScene]
            MAN -->|EaseToLearnScene.mp4| TTS
            TTS[tts_generator\nper-scene audio]
            TTS -->|ElevenLabs API\nor Mac say → mp3| CONCAT
            CONCAT[MoviePy\nconcatenate audio clips]
            CONCAT --> STITCH
            STITCH[ffmpeg\nvideo + audio stitch]
            STITCH --> S3
            S3([S3 Upload\nboto3\nap-south-1])
            S3 -->|s3:// URL\nor file:// local| VURL[[video_url]]
        end

        subgraph H ["⑤ Healer Node  — on failure only"]
            FIX([Claude Opus 4.6\nreads stderr + broken script\nreturns fixed script])
        end

        RETRY{render error?\nattempt < 3}
    end

    GRAPH -->|raw_input, topic| D
    D --> V
    V --> A
    A -->|manim| S
    S --> RETRY
    RETRY -->|yes — error| H
    H -->|fixed script| S
    RETRY -->|no — success| WEBHOOK
    PRESOUT --> WEBHOOK

    subgraph EXT ["External Services"]
        CL
        GEM
        S3
        EL([ElevenLabs TTS\nNeha voice\neleven_multilingual_v2])
        TTS --> EL
    end

    style API fill:#1a1a2e,color:#fff,stroke:#4ECDC4
    style GRAPH fill:#0d0d1a,color:#fff,stroke:#4ECDC4
    style EXT fill:#111133,color:#fff,stroke:#555
    style D fill:#162032,color:#fff,stroke:#4ECDC4
    style V fill:#162032,color:#fff,stroke:#4ECDC4
    style A fill:#162032,color:#fff,stroke:#4ECDC4
    style S fill:#162032,color:#fff,stroke:#4ECDC4
    style H fill:#2a1020,color:#fff,stroke:#FF6B6B
    style SB fill:#1a2e1a,color:#fff,stroke:#4CAF50
```

## Flow Summary

| Step | Node | Does What |
|------|------|-----------|
| 1 | **Director** | Parses Tony AI HTML → Claude Opus decides render mode + writes scenes |
| 2 | **Vision** | Gemini Imagen 4.0 generates concept diagram PNG (manim only) |
| 3 | **Architect** | Converts scenes → Manim script (deterministic, no LLM) |
| 4 | **Supervisor** | Renders Manim → TTS per scene → ffmpeg stitch → S3 upload |
| 5 | **Healer** | Claude Opus fixes broken Manim scripts (max 3 retries) |

## Render Modes

| Mode | When | Engine |
|------|------|--------|
| `manim` | Maths, Physics, Medical MCQ, Chemistry | Manim + Gemini diagram |
| `presentation` | English, UPSC, MBA, simple concepts | Slide + avatar (tony_pipeline) |
| `human_face` | Conversational (future) | — |
```
