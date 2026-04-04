"""
Factory Orchestrator — Team Tony
Bulk process medical lessons from a directory.
"""

import os
import sys
import glob
import concurrent.futures
from autonomous_graph import app as graph

def process_file(file_path: str):
    """Run the full pipeline for a single HTML file."""
    topic = os.path.basename(file_path).replace(".html", "").replace("_", " ").title()
    print(f"\n🏭 [Factory] Starting job: {topic}")

    with open(file_path, "r") as f:
        html = f.read()

    try:
        result = graph.invoke({
            "raw_input":    html,
            "topic":        topic,
            "attempt_count": 0,
            "parsed_facts": None, "render_mode": None, "scenes": None,
            "image_path": None, "manim_script_path": None,
            "output_path": None, "video_url": None, "rendering_errors": None,
        })
        print(f"✅ [Factory] Finished: {topic} -> {result.get('video_url')}")
        return topic, result.get("video_url")
    except Exception as e:
        print(f"❌ [Factory] Failed: {topic} | Error: {e}")
        return topic, None

def main(input_dir: str, max_workers: int = 2):
    """Process all HTML files in a directory in parallel."""
    files = glob.glob(os.path.join(input_dir, "*.html"))
    if not files:
        print(f"Empty directory: {input_dir}")
        return

    print(f"🚀 [Factory] Processing {len(files)} lessons with {max_workers} workers...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(process_file, f): f for f in files}
        for future in concurrent.futures.as_completed(future_to_file):
            topic, url = future.result()

if __name__ == "__main__":
    indir = sys.argv[1] if len(sys.argv) > 1 else "lessons/"
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    main(indir, max_workers=workers)
