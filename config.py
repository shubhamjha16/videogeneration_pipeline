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

# Pipeline Settings
DEFAULT_AVATAR = "logo"
DEFAULT_RESOLUTION = (854, 480) # 480p for speed
FPS = 24

# Path Helpers
def get_path(*args):
    return os.path.join(BASE_DIR, *args)
