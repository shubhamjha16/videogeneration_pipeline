# Tony AI — Video Generation Factory Integration Guide

This guide documents the API contract for the **Tony AI (Spring Boot)** backend to trigger and monitor architectural video production.

## 🚀 Quick Start
All requests require the `X-API-Key` header for authentication.

- **Base URL**: `http://<factory-ip>:8000`
- **Auth Header**: `X-API-Key: <your-secure-key>`

---

## 1. Triggering a Render
To start a new video production job, send a `POST` request to `/render`.

### Endpoint
`POST /render`

### Request Body (JSON)
| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `topic` | `string` | **Yes** | The title/subject of the lesson. |
| `html` | `string` | **Yes** | The raw curriculum HTML content. |
| `render_mode` | `string` | No | `manim` (default), `presentation`, `explainer`, `user_generated` |
| `video_type` | `string` | No | `educational` (default), `marketing` |
| `with_avatar` | `boolean`| No | If `true`, includes a HeyGen talking head (if supported by mode). |
| `webhook_url` | `string` | No | URL to notify when the job completes. |

### Example Request
```json
{
  "topic": "The Human Heart",
  "html": "<html><body><h1>Lesson 1</h1>...</body></html>",
  "render_mode": "manim",
  "video_type": "educational",
  "with_avatar": false,
  "webhook_url": "https://tony-ai-backend.com/api/v1/factory/callback"
}
```

### Response (200 OK)
```json
{
  "job_id": "4a8d5928-cae",
  "status": "queued",
  "topic": "The Human Heart"
}
```

---

## 2. Monitoring Status (Polling)
If you do not use webhooks, you can poll the status of a specific job.

### Endpoint
`GET /status/{job_id}`

### Response (200 OK)
```json
{
  "job_id": "4a8d5928-cae",
  "status": "completed",
  "video_url": "https://s3.ap-south-1.amazonaws.com/.../heart.mp4",
  "thumbnail_url": "https://s3.ap-south-1.amazonaws.com/.../thumb.png",
  "progress": 100,
  "current_step": "DEPLOY",
  "logs": [
    {"node": "RESEARCH", "msg": "🔎 Metasearch: 'Human Heart anatomy'", "type": "info"},
    {"node": "DEPLOY", "msg": "Video production finalized.", "type": "success"}
  ]
}
```

---

## 3. Webhook Callback
Once a job reaches a terminal state (`completed` or `failed`), the factory will send a `POST` request to your `webhook_url`.

### Payload (JSON)
The payload is a full `JobStatus` object (identical to the status endpoint response).

---

## 4. Render Modes Explained

| Mode | Visual Style | Best For |
| :--- | :--- | :--- |
| **manim** | Mathematical/Scientific Motion Graphics | Maths, Physics, Medical MCQs, Deep-dive Science. |
| **presentation** | Animated "Doodle" slides with icons | Case studies, UPSC GS, History, Languages. |
| **explainer** | Cinematic B-roll + Generative Metaphors | High-impact storytelling, abstract concepts. |
| **user_generated** | AI Avatar (Talking Head) + Kinetic Subs | Direct teacher messages, short motivational updates. |

---

## 🛰 Intelligence Features (Automated)
The factory automatically performs the following actions during production:
1. **Agentic Research**: If the input HTML is thin, the factory uses SearXNG (metasearch) to fetch ground-truth data.
2. **Knowledge Persistence**: Verified facts are saved in a local cache. Future videos on the same topic will skip the search phase.
3. **Self-Healing**: If a rendering error occurs (e.g., Manim script crash), a "Healer Agent" identifies the fix online and re-attempts the render.

---

## 📊 Analytics
To get a high-level overview of the factory performance, call `/analytics`.

### Endpoint
`GET /analytics`

### Response
```json
{
  "total_jobs": 1250,
  "completed": 1200,
  "failed": 50,
  "success_rate": "96.0%",
  "avg_render_time_sec": 425.5
}
```
