# ─────────────────────────────────────────────────────────────────────────────
# EaseToLearn Video Generation Service
# Runs the LangGraph pipeline: HTML → Manim → TTS → ffmpeg → S3
#
# Base: Python 3.11 slim (Debian Bookworm)
# Heavy deps: LaTeX (Manim), Cairo/Pango (Manim), ffmpeg (stitching)
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim-bookworm

# ── System labels ─────────────────────────────────────────────────────────────
LABEL org.opencontainers.image.title="EaseToLearn Video Generation"
LABEL org.opencontainers.image.description="AI video generation pipeline for Indian competitive exams"

# ── Environment ───────────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    # Tell Manim where to write media (mapped to EFS/ephemeral in ECS)
    MANIM_MEDIA_DIR=/app/output \
    # Manim config: no GUI, low quality default (overridden per job)
    MANIM_CONFIG_FILE=/app/manim.cfg

# ── System dependencies ───────────────────────────────────────────────────────
# Split into groups so Docker layer cache stays valid when only one group changes

# 1. Build essentials + libraries Manim needs at build time
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    python3-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libglib2.0-dev \
    libffi-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 2. ffmpeg + fonts (slide_generator uses DejaVu on Linux)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-dejavu-core \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# 3. LaTeX (Heavy Layer) — Optimized for Science/Math Masterclasses
# We split this to allow easier layer auditing.
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-science \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    dvipng \
    dvisvgm \
    cm-super \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ───────────────────────────────────────────────────────
WORKDIR /app

COPY requirements.txt .

# Upgrade pip first, then install all deps
# --no-cache-dir keeps the image lean
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Manim configuration ───────────────────────────────────────────────────────
# Tell Manim to use /app/output for media and suppress GUI prompts
RUN mkdir -p /app/output
COPY manim.cfg /app/manim.cfg

# ── Application code ──────────────────────────────────────────────────────────
COPY . .

# Remove local venv and Mac-specific artifacts if accidentally copied
RUN rm -rf venv __pycache__ .DS_Store output/*.mp4 output/*.png 2>/dev/null || true

# ── Non-root user (ECS security best practice) ────────────────────────────────
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# ── Port ──────────────────────────────────────────────────────────────────────
EXPOSE 8000

# ── Health check (mirrors /health endpoint, used by ALB) ─────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ── Entry point ───────────────────────────────────────────────────────────────
CMD ["python", "-m", "uvicorn", "api_bridge:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--timeout-keep-alive", "75"]
