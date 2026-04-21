# EaseToLearn: Standalone SearXNG Research Node

This is a decoupled research engine used by the **Autonomous Video Factory**. It is optimized for high-fidelity agentic research (JSON enabled, privacy focused).

## 🚀 Setup & Launch (Industrial Mode)

The most reliable way to run the research node is using **Docker Compose**. This automatically handles the research engine and its Redis cache.

### 1. Configure the Environment
```bash
cp .env.template .env
# Edit .env with your specific SEARXNG_BASE_URL and SEARXNG_SECRET_KEY
```

### 2. Launch the Stack
```bash
docker-compose up -d --build
```

## 🧪 Testing
Verify the instance is working independently of the Video Factory:
```bash
python3 test_searxng.py http://localhost:8080
```

## 🔗 Integration with Video Factory
Once this instance is running (e.g. on your Mac Mini), update the Video Factory `.env` file:
```bash
SEARXNG_URL=http://<MAC_MINI_IP>:8080
```
