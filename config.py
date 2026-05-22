import os
from dotenv import load_dotenv

# Absolute path to project root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

# Load environment variables
load_dotenv(ENV_PATH)

ENV = os.environ.get("ENV", "dev").lower().strip()

# Try to load credentials from AWS Secrets Manager in production or staging environments
if ENV in ("production", "staging"):
    SECRET_NAME = os.environ.get("AWS_SECRETS_NAME", "easetolearn/video-factory/prod")
    AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")
    print(f"☁️ AWS Secrets Manager: Attempting to pull secrets from '{SECRET_NAME}' in region '{AWS_REGION}'...")
    try:
        import boto3
        import json
        from botocore.exceptions import ClientError
        
        # Boto3 will automatically inherit task roles or instance profiles
        client = boto3.client("secretsmanager", region_name=AWS_REGION)
        response = client.get_secret_value(SecretId=SECRET_NAME)
        
        if "SecretString" in response:
            secrets = json.loads(response["SecretString"])
            for key, val in secrets.items():
                os.environ[key] = str(val)
            print("✅ AWS Secrets Manager: Secrets loaded successfully into environment.")
    except Exception as e:
        print(f"⚠️ AWS Secrets Manager: Could not retrieve secrets (falling back to standard environment/dotenv): {e}")

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

# Database Settings
DATABASE_URL = os.environ.get("DATABASE_URL", "")


# Pipeline Settings
DEFAULT_AVATAR = "logo"
HEYGEN_AVATAR_ID = os.environ.get("HEYGEN_AVATAR_ID", "josh_video_20230607") # High-quality stock instructor
DEFAULT_RESOLUTION = (854, 480) # 480p for speed
FPS = 24

# Path Helpers
def get_path(*args):
    return os.path.join(BASE_DIR, *args)


def verify_production_dependencies():
    """
    Validates that all critical production dependencies and environment variables
    are fully resolved. Halts boot immediately with a loud exit code if
    anything is missing in staging or production environments.
    """
    env = os.environ.get("ENV", "dev").lower().strip()
    if env not in ("production", "staging"):
        return

    print("======================================================================")
    print(f"🔒 INDUSTRIAL SENTINEL: ENFORCING STRICT PRODUCTION/STAGING CHECKS ({env.upper()})")
    print("======================================================================")

    errors = []

    # 1. Critical Environment Variables Check
    required_env_vars = {
        "FACTORY_API_KEY": "Required to secure the REST APIs from unauthorized access.",
        "DATABASE_URL": "Required for production MySQL database persistence."
    }
    
    # Check LLM specific API Keys
    llm_provider = os.environ.get("LLM_PROVIDER", "openai").lower().strip()
    if llm_provider == "openai":
        required_env_vars["OPENAI_API_KEY"] = "Required for primary OpenAI LLM API calls."
    elif llm_provider == "groq":
        required_env_vars["GROQ_API_KEY"] = "Required for fast Groq LLM inference."
    elif llm_provider == "google":
        required_env_vars["GEMINI_API_KEY"] = "Required for Google Gemini API calls."

    for var, desc in required_env_vars.items():
        val = os.environ.get(var, "").strip()
        if not val:
            errors.append(f"❌ Missing environment variable: {var}\n   Reason: {desc}")
        elif var == "DATABASE_URL" and val.startswith("sqlite"):
            errors.append(f"❌ DATABASE_URL uses SQLite fallback in production/staging: '{val}'\n   Reason: Production/Staging requires a robust centralized relational database (e.g. MySQL).")

    # 2. Critical Module Dependencies Check
    required_modules = [
        ("redis", "Used for centralized distributed job synchronization and caching."),
        ("fcntl", "Required for Unix-based cross-process file-level locking."),
        ("sqlalchemy", "SQLAlchemy ORM for database connectivity."),
        ("pymysql", "Pure Python MySQL driver for database connectivity."),
        ("groq", "Groq Python SDK for fast LLM inference."),
        ("openai", "OpenAI Python SDK."),
    ]
    
    for mod_name, desc in required_modules:
        try:
            __import__(mod_name)
        except ImportError as e:
            errors.append(f"❌ Missing library dependency: '{mod_name}'\n   Reason: {desc}\n   Import error: {e}")

    # Check google-genai package
    try:
        from google import genai
    except ImportError as e:
        errors.append(f"❌ Missing library dependency: 'google-genai' (imported via 'from google import genai')\n   Reason: Required for Google Gemini Imagen 3 thumbnail and explainer generation.\n   Import error: {e}")

    # 3. Critical Binary Commands Check
    import shutil
    import sys
    
    # ffmpeg is required on all platforms
    if not shutil.which("ffmpeg"):
        errors.append("❌ Missing external command: 'ffmpeg'\n   Reason: Required for video compilation, audio stitching, and timeline processing.")

    # espeak or espeak-ng is required on staging/production non-macOS platforms
    if sys.platform != "darwin":
        espeak_found = shutil.which("espeak") or shutil.which("espeak-ng")
        if not espeak_found:
            errors.append("❌ Missing external command: 'espeak' or 'espeak-ng'\n   Reason: Required for offline Text-to-Speech narration generation in Linux environments.")

    if errors:
        print("\n🚨 CRITICAL BOOTSTRAP FAILURE: Missing production-ready elements!")
        for err in errors:
            print(err)
        print("\n⚠️ Application booting aborted. Please correct these issues before redeploying.")
        print("======================================================================\n")
        import sys
        sys.exit(1)
    else:
        print("✅ All staging/production dependencies and settings validated successfully.")
        print("======================================================================\n")

# Run validation on initialization
verify_production_dependencies()

