import os
from dotenv import load_dotenv

# Absolute path to project root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

# Load environment variables
load_dotenv(ENV_PATH)

# API Keys
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
HEYGEN_API_KEY = os.environ.get("HEYGEN_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
HIGGSFIELD_API_ID = os.environ.get("HIGGSFIELD_API_ID", "")
HIGGSFIELD_API_KEY = os.environ.get("HIGGSFIELD_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://localhost:8080")
SEARXNG_RESULTS_LIMIT = int(os.environ.get("SEARXNG_RESULTS_LIMIT", "5"))
SEARXNG_TIMEOUT = int(os.environ.get("SEARXNG_TIMEOUT", "25"))
SEARXNG_RETRIES = int(os.environ.get("SEARXNG_RETRIES", "3"))

# LLM Providers (groq | google | local | openai)
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai")
LOCAL_LLM_URL = os.environ.get("LOCAL_LLM_URL", "http://localhost:11434/v1")
LOCAL_LLM_MODEL = os.environ.get("LOCAL_LLM_MODEL", "gemma:4b")

# Disk Hygiene (Staging Area Cleanup)
HYGIENE_RETENTION_HOURS = int(os.environ.get("HYGIENE_RETENTION_HOURS", "24"))
HYGIENE_CHECK_INTERVAL_SECONDS = int(os.environ.get("HYGIENE_CHECK_INTERVAL_SECONDS", "3600")) # Default: 1 hour


# Pipeline Settings
DEFAULT_AVATAR = "logo"
HEYGEN_AVATAR_ID = os.environ.get("HEYGEN_AVATAR_ID", "josh_video_20230607") # High-quality stock instructor
DEFAULT_RESOLUTION = (854, 480) # 480p for speed
FPS = 24

# Path Helpers
def get_path(*args):
    return os.path.join(BASE_DIR, *args)
