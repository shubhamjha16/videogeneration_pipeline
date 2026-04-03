import os
import sys
import json
from autonomous_graph import app
import config

def launch_production(raw_content: str, topic_name: str):
    """
    Triggers the 'Team Tony' autonomous orchestrator for a single module.
    """
    print(f"🚀 [FACTORY] Starting Production for: {topic_name}")
    
    initial_state = {
        "raw_input": raw_content,
        "topic": topic_name,
        "attempt_count": 0,
        "image_prompts": []
    }
    
    # Run the LangGraph Factory
    final_state = app.invoke(initial_state)
    
    video_path = final_state.get("output_path")
    if video_path:
        print(f"🏆 [FACTORY] Success! Masterclass delivered to: {video_path}")
    else:
        print(f"❌ [FACTORY] Logic failure in orchestrator. Check Supervisor logs.")
    
    return video_path

if __name__ == "__main__":
    # Example: User provides HTML/JSON locally or via CLI
    if len(sys.argv) > 2:
        file_path = sys.argv[1]
        topic = sys.argv[2]
        
        with open(file_path, "r") as f:
            content = f.read()
            
        launch_production(content, topic)
    else:
        print("Usage: python3 factory_manager.py <file.html> <TopicName>")
