#!/bin/bash
# Industrial Hygiene — Production Cleanup Script
# Purges temporary media and old job data to maintain disk stability.

RETENTION_HOURS=${HYGIENE_RETENTION_HOURS:-24}
OUTPUT_DIR="./output"

echo "🧹 Starting Factory Hygiene: Purging data older than ${RETENTION_HOURS} hours..."

# 1. Purge temporary media (Manim videos, images)
# We keep the final .mp4 if it's in the job root, but clear the media/ subfolders
find "$OUTPUT_DIR" -type d -name "media" -mmin +$((RETENTION_HOURS * 60)) -exec rm -rf {} +

# 2. Purge failed or incomplete job directories
find "$OUTPUT_DIR" -type d -mmin +$((RETENTION_HOURS * 60)) -not -path "$OUTPUT_DIR" -exec rm -rf {} +

# 3. Trim the KB retrieval log if it gets too large (> 10MB)
LOG_FILE="./output/kb_retrievals.jsonl"
if [ -f "$LOG_FILE" ]; then
    FILE_SIZE=$(du -k "$LOG_FILE" | cut -f1)
    if [ "$FILE_SIZE" -gt 10240 ]; then
        echo "📂 Trimming KB log (exceeded 10MB)..."
        tail -n 1000 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
    fi
fi

echo "✅ Hygiene complete."
