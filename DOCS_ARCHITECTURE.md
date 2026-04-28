# RAG vs. Autonomous Video Factory: Architecture Comparison

This document defines the structural differences between standard **Retrieval-Augmented Generation (RAG)** and the **Industrial Agentic Video Factory** implemented in this project.

---

## 1. Ordinary RAG Architecture
**Objective**: Text-to-Text response (Chatbot).

```mermaid
graph TD
    Input([User Query]) --> Search{Vector Search}
    Search --> Context[Relevant Text Chunks]
    Context --> LLM[LLM Synthesis]
    LLM --> Output[/Text Answer/]

    style Output fill:#f8f9fa,stroke:#333
```

---

## 2. Industrial Video Factory Architecture
**Objective**: Industrial-grade, multi-modal video production.

```mermaid
graph TD
    Input([Topic / Curriculum]) --> RAG_Memory{Semantic Memory\nVector DB}
    
    subgraph INTEL ["Intelligence Hub (Loop)"]
        RAG_Memory --> Director[Director Agent\nPlans Scenes & Style]
        Director --> Vision[Vision Agent\nGenerates AI Assets]
    end

    subgraph PROD ["Production Line (Code + Render)"]
        Vision --> Architect[Architect Agent\nWrites Manim Code]
        Architect --> Render[Render Engine\nManim + LaTeX]
        Render --> Audio[Audio Fusion\nTTS + Narrator Sync]
    end

    subgraph QA ["Resilience & Healing"]
        Audio --> Healer{Healer Node\nError Detect?}
        Healer -- "REMEDIATE (Retry < 3)" --> Architect
        Healer -- "SUCCESS" --> Final
    end

    Final[/1080p Cinematic MP4/]

    style INTEL fill:#fff4e5,stroke:#d4a017
    style PROD fill:#e3f2fd,stroke:#1976d2
    style Final fill:#e8f5e9,stroke:#2e7d32
```

---

## Final Comparison Table

| Feature | Ordinary RAG | **Industrial Video Factory** |
| :--- | :--- | :--- |
| **Output Type** | Text Paragraph | **Cinematic 1080p Video** |
| **Multimodality** | Limited (Text focus) | **Built-in (Images, Audio, Python Code)** |
| **Self-Correction** | None | **Autonomous Healer Agent** |
| **Control** | LLM-driven | **Design-Token & Logic driven** |
| **Goal** | To Inform | **To Teach & Visualize** |
