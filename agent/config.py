import os
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")

# 1. Load dotenv variables
dotenv_path = os.path.join(PROJECT_ROOT, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# 2. AGENT SETTINGS
GEMINI_MODEL = "gemini-1.5-flash"
MAX_TURNS = 8
LOG_FILE = os.path.join(LOG_DIR, "agent.log")

# Ensure logs dir exists if NOT running on Vercel
if not os.environ.get("VERCEL"):
    os.makedirs(LOG_DIR, exist_ok=True)
