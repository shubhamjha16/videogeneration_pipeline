# Industrial Autonomous Video Factory — Production Container
# Base: Official Manim Community Image (Pre-installed with TeX Live, FFmpeg, and Python)
FROM manimcommunity/manim:stable

# Switch to root to install system dependencies
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Industrial Optimization: Copy requirements first for Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Copy the rest of the application
COPY . .

# Ensure the output directory exists and is writable for the 'manim' user
RUN mkdir -p /app/output && chmod -R 777 /app/output
RUN mkdir -p /app/factory_vector_db && chmod -R 777 /app/factory_vector_db

# Switch back to the manim user for secure execution
USER manim

# Environment Variables Audit: Port should be configurable
ENV PORT=8000
EXPOSE 8000

# Entry point: Start the FastAPI API Bridge
CMD ["python3", "api_bridge.py"]
