# Industrial Video Factory: Production Lifecycle & State Machine

This document defines the states, transitions, and financial implications of the autonomous video generation pipeline for the EaseToLearn production environment.

## 1. Job State Machine

| State | Description | Cost Implication |
| :--- | :--- | :--- |
| **QUEUED** | Job received by API and persisted to Redis. Waiting for a worker slot. | **$0.00** |
| **PROCESSING** | Worker has acquired the semaphore and initiated the LangGraph. | **$0.00** (Initial) |
| **DIRECTING** | Director Agent is analyzing the curriculum and planning scenes. | **LLM Input + Output tokens** |
| **ASSET_GEN** | Parallel generation of TTS audio and AI images. | **TTS Chars + Image Call Fees** |
| **RENDERING** | The primary engine (Manim/PPT) is stitching assets into a video. | **$0.00** (Compute only) |
| **AVATAR_GEN** | (HeyGen Path Only) Video uploaded and polling HeyGen API. | **HeyGen Credits / Min** |
| **COMPLETED** | Video uploaded to storage and webhook fired successfully. | **Total Accumulated Cost** |
| **FAILED** | A terminal error occurred. Sunk costs are ledgered and reported. | **Sunk Cost (up to failure)** |

## 2. Failure Recovery & Ledgering

### 2.1 The "Sunk Cost" Rule
In a production environment, an API call is considered "spent" the moment the response is received. 
*   **Immediate Ledgering**: The `LedgerManager` appends every successful API call to `cost_records.jsonl` immediately. 
*   **Failure Reporting**: If a job fails at the Rendering stage, the Webhook notification to Spring Boot will include the `usd_cost` representing the LLM, TTS, and Image generation that occurred before the crash.

### 2.2 Healer Agent Retries
The `healer_agent` can attempt to fix failed nodes (e.g., repairing a Manim syntax error). 
*   **Ledger Impact**: Each retry is a new LLM call and is ledgered independently.
*   **Transparency**: Analytics will show multiple "llm" entries for a single `job_id` if retries occurred.

## 3. Webhook Delivery Policy (At-Least-Once)

To ensure the Spring Boot backend never "loses" a job status, the following policy is enforced:
*   **Retry Count**: 5 attempts.
*   **Backoff Strategy**: Jittered exponential backoff ([2s, 6s, 14s, 30s] average).
*   **Idempotency**: The `job_id` is the primary key. If the backend receives two notifications for the same job, it should overwrite its local state.
*   **DLQ (Dead Letter Queue)**: If all 5 retries fail, the payload is written to `webhook_dlq.json` for manual replay or administrative audit.

## 4. Grounder Synchronization
The `vision_node` (Grounder) is architecturally downstream from the `image_node`. The graph ensures that the Grounder never attempts to analyze an asset before the Generator has finalized the file on disk.
