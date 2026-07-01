import os
import sys
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")

# 1. Load variables from .env file
dotenv_path = os.path.join(PROJECT_ROOT, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# 2. Bind host & port from environment or fallback
HOST = os.environ.get("HOST", "127.0.0.1")
try:
    PORT = int(os.environ.get("PORT", "8000"))
except ValueError:
    PORT = 8000

LOG_FILE = os.path.join(LOG_DIR, "api.log")

# 3. OpenAPI documentation metadata
TITLE = "Conversational SHL Assessment Recommender API"
VERSION = "1.0.0"
DESCRIPTION = (
    "Production-grade FastAPI backend exposing the conversational AI agent "
    "for searching, recommending, and comparing official SHL assessments."
)

# 4. Warn if Gemini key is missing
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
if not GEMINI_KEY:
    # Log warning to stdout so it shows up in console during startup
    print(
        "WARNING: 'GEMINI_API_KEY' is not set in the environment or .env file.\n"
        "The Conversational Agent will run in high-fidelity Consultant Simulator Mode.\n",
        file=sys.stderr
    )

# Ensure logs dir exists if NOT running on Vercel
if not os.environ.get("VERCEL"):
    os.makedirs(LOG_DIR, exist_ok=True)
