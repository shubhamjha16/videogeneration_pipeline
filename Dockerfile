# Industrial Autonomous Video Factory — Production Container
# Base: Official Manim Community Image (Pre-installed with TeX Live, FFmpeg, and Python 3)
FROM manimcommunity/manim:stable

# Switch to root to install system dependencies and configure environment
USER root

# Industrial Optimization: Install required system packages and clean up apt cache
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    procps \
    redis-tools \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Upgrade pip to avoid warnings and ensure latest wheel support
RUN pip install --no-cache-dir --upgrade pip --break-system-packages

# Industrial Layer Caching: Copy only requirements first
COPY requirements.txt .

# Install Python dependencies
# --no-cache-dir prevents storing downloaded wheels, crucial for 11GB constraint
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt \
    && rm -rf /root/.cache/pip

# Copy the application source code
COPY . .

# Set up required persistent directories and permissions
RUN mkdir -p /app/output \
    && mkdir -p /app/factory_vector_db \
    && mkdir -p /app/assets \
    && chown -R manimuser:manimuser /app

# Switch to non-root user for security
USER manimuser

# Default Environment Variables
ENV PORT=8000 \
    HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1 \
    MANIM_MEDIA_DIR=/app/output \
    PYTHONDONTWRITEBYTECODE=1

# Expose the API port
EXPOSE 8000

# Healthcheck for orchestrator (ECS/Docker Swarm/Compose)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start the Fast API Bridge
CMD ["python3", "-m", "uvicorn", "api_bridge:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
