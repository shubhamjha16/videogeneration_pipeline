# 📚 Integration Guide: Spring Boot to Video Factory

This document provides the mapping instructions for the **Spring Boot** team to integrate existing `teacherapi.easetolearn.com` content with the **Autonomous Video Factory**.

## 1. The Data Source (Teacher API)
When calling `https://teacherapi.easetolearn.com/app/studentpanel/openai?questionId=...`, the response structure is:

```json
{
  "responseTxt": "success",
  "obj": {
    "solution": "<html>...</html>",
    "questionId": 212173
  }
}
```

## 2. The Target (Video Factory /render)
The Video Factory endpoint is `POST /render`. 
It expects the following JSON payload:

```json
{
  "topic": "String",    // Used for AI Scene Planning
  "html": "String",     // Raw HTML for the lesson
  "render_mode": "auto" // (Optional) manim | presentation | explainer
}
```

## 3. Mapping Logic (Spring Boot Implementation)

To initiate a video generation job, Spring Boot must "Re-package" the Teacher API response into the Factory Request:

| Factory Field | Source (Teacher API) | Logic / Notes |
| :--- | :--- | :--- |
| **`topic`** | `obj.questionId` | Look up the Descriptive Topic name in the Spring Boot DB using the `questionId`. **Do not pass the raw ID number** as the topic; the AI Director needs a semantic name (e.g., "Larynx Innervation"). |
| **`html`** | `obj.solution` | Pass the raw string from the `solution` field exactly as received. |
| **`render_mode`** | Optional | Set to `manim` for Math/Physics or `presentation` for English/History. If null, the AI Director will decide. |

### Java Sample (WebClient / RestTemplate)

```java
// 1. Extract data from Teacher API
String rawSolution = response.getObj().getSolution();
Integer qId = response.getObj().getQuestionId();

// 2. Resolve topic name (Critical for AI performance)
String topicName = questionService.getTopicName(qId); 

// 3. Build the request for the Video Factory
Map<String, Object> factoryRequest = new HashMap<>();
factoryRequest.put("topic", topicName);
factoryRequest.put("html", rawSolution);
factoryRequest.put("render_mode", "auto");

// 4. Fire and Forget (Factory returns immediate job_id)
factoryClient.post().uri("/render").bodyValue(factoryRequest).retrieve().bodyToMono(Map.class).subscribe();
```

## 4. Authentication
Ensure all requests from Spring Boot include the following header:
*   `X-API-Key`: (Retrieved from environment variable `FACTORY_API_KEY`)

## 5. Webhook Callback (Recommended)
The Factory can notify Spring Boot when a video is ready.
*   **Factory fires**: `POST {WEBHOOK_URL}`
*   **Payload**: `{"job_id": "...", "status": "completed", "video_url": "...", "thumbnail_url": "..."}`

---
**Status**: Ready for Implementation.
**Endpoint**: `https://{factory-load-balancer-url}/render`
**Swagger Documentation**: `https://{factory-load-balancer-url}/docs`
