import os
import uuid
import threading
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from autonomous_graph import app as tony_app

app = FastAPI(title="Team Tony API Bridge")

# Enable CORS for Chrome Extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store job status
jobs = {}

class RenderRequest(BaseModel):
    topic: str
    html: str

def run_render(job_id: str, topic: str, html: str):
    try:
        jobs[job_id] = {"status": "processing", "video_url": None}
        # Invoke the LangGraph Brain with FULL initial state
        result = tony_app.invoke({
            "raw_input": html, 
            "topic": topic,
            "attempt_count": 0,
            "image_prompts": []
        })
        
        output_path = result.get("output_path")
        if output_path and os.path.exists(output_path):
            # Move to a public folder for serving
            public_name = f"{job_id}.mp4"
            os.rename(output_path, f"public/{public_name}")
            jobs[job_id] = {"status": "completed", "video_url": f"http://localhost:8000/public/{public_name}"}
        else:
            jobs[job_id] = {"status": "failed", "error": "Render produced no output"}
    except Exception as e:
        jobs[job_id] = {"status": "failed", "error": str(e)}

@app.post("/render")
async def start_render(request: RenderRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "queued", "video_url": None}
    background_tasks.add_task(run_render, job_id, request.topic, request.html)
    return {"job_id": job_id}

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

# Serve the finished videos
os.makedirs("public", exist_ok=True)
app.mount("/public", StaticFiles(directory="public"), name="public")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
