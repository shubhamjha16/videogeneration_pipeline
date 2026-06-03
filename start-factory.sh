#!/bin/bash
# =============================================================================
# EaseToLearn Factory — Mac Mini boot/start script
# Brings up colima (sized for Manim/FFmpeg + sidecars) and the staging stack.
# Invoked by the LaunchAgent at login. Safe to run manually too.
# =============================================================================
set -euo pipefail

# Homebrew (Apple Silicon) is NOT on launchd's default PATH — set it explicitly.
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin"

# --- EDIT THIS to the repo path on the Mini ---
FACTORY_DIR="/Users/easetolearn/factory"
COMPOSE_FILE="docker-compose.macmini.yaml"

echo "[$(date)] Ensuring colima is running..."
if ! colima status >/dev/null 2>&1; then
  # Size the VM so the factory (4 CPU / 6G) + sidecars fit with headroom.
  # Tune to the Mini's actual specs.
  colima start --cpu 6 --memory 12 --disk 60
fi

echo "[$(date)] Waiting for the Docker socket..."
until docker info >/dev/null 2>&1; do sleep 2; done

echo "[$(date)] Bringing up the factory stack..."
cd "$FACTORY_DIR"
docker compose -f "$COMPOSE_FILE" up -d

echo "[$(date)] Stack is up. Portal: ${LOCAL_CDN_URL:-http://localhost:8000}/portal"
