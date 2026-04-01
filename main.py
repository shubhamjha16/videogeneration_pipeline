from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import os
import uuid
import subprocess

app = FastAPI(title="EaseToLearn Video Generation API")

class VideoRequest(BaseModel):
    topic: str
    text: str
    avatar: str = "human"
    mode: str = "auto"
    manim_code: str = None  # Raw Python code from Tony AI

# Simple in-memory job store
jobs = {}

def process_video(job_id: str, topic: str, text: str, avatar: str, mode: str, manim_code: str = None):
    jobs[job_id] = "Processing"
    
    # Create a temp text file for the generator
    txt_path = f"temp_input_{job_id}.txt"
    with open(txt_path, "w") as f:
        f.write(text)
    
    try:
        # Build command
        cmd = [
            "./venv/bin/python3", "easeto_generate.py",
            "--mode", mode,
            "--topic", topic,
            "--text", txt_path,
            "--avatar", avatar
        ]
        
        if manim_code:
            cmd.extend(["--inline-script", manim_code])
        
        print(f"🎬 Starting job {job_id}: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            jobs[job_id] = "Completed"
            print(f"✅ Job {job_id} finished successfully.")
        else:
            jobs[job_id] = f"Error: {result.stderr}"
            print(f"❌ Job {job_id} failed: {result.stderr}")
            
    except Exception as e:
        jobs[job_id] = f"Exception: {str(e)}"
    finally:
        if os.path.exists(txt_path):
            os.remove(txt_path)

@app.post("/generate")
async def generate_video(request: VideoRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = "Queued"
    
    background_tasks.add_task(
        process_video, 
        job_id, 
        request.topic, 
        request.text, 
        request.avatar, 
        request.mode,
        request.manim_code
    )
    
    return {
        "status": "Queued",
        "job_id": job_id,
        "message": "Video generation has started in the background."
    }

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "status": jobs[job_id]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
