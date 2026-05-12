import os
import sys
import json

# Ensure parent directory is in path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from autonomous_graph import TonyState
from nodes.ambient_visual_node import ambient_visual_node
from dotenv import load_dotenv

load_dotenv()

state: TonyState = {
    "job_id": "test_ambient_001",
    "topic": "The Human Heart",
    "render_mode": "presentation",
    "parsed_facts": {"subject": "medical", "content_type": "anatomy"},
    "video_type": "educational",
    "with_avatar": False,
    "ledger": {},
    "script_segments": [],
    "raw_input": "Test input",
    "source_type": "markdown",
    "use_elevenlabs": False,
    "avatar_type": "logo",
    "avatar_id": None,
    "overrides": None,
    "scenes": None,
    "image_path": None,
    "image_paths": None,
    "landmark_coords": None,
    "ambient_assets": {},
    "manim_script_path": None,
    "audio_files": None,
    "output_path": None,
    "video_url": None,
    "thumbnail_url": None,
    "slides": None,
    "slide_paths": None,
    "clip_paths": None,
    "critic_feedback": None,
    "ppt_attempt_count": 0,
    "search_queries": None,
    "search_results": None,
    "knowledge_base": None,
    "heygen_video_path": None,
    "subtitle_style": None,
    "rendering_errors": None,
    "attempt_count": 0,
    "no_vision": False,
    "research_count": 0,
    "rejected_attempts": [],
    "media_manifest": []
}

print(f"Testing ambient_visual_node for topic: {state['topic']}")
result_state = ambient_visual_node(state)

print("\n--- Output State ambient_assets ---")
print(json.dumps(result_state.get("ambient_assets"), indent=2))
