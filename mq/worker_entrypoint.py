import os
import sys
import time

# Ensure project root is in path
sys.path.append(os.getcwd())

from mq.consumer import start_consumer
from api_bridge import _run_pipeline

if __name__ == "__main__":
    print("🚀 Starting Standalone Video Render Queue Worker...")
    # start_consumer launches a daemon thread
    success = start_consumer(pipeline_fn=_run_pipeline)
    if not success:
        print("❌ Failed to start consumer. Verify RabbitMQ environment settings.")
        sys.exit(1)
        
    print("🐇 Worker is active and listening for messages. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("👋 Worker stopping...")
