import os

# Crawler configuration
BASE_URL = "https://www.shl.com"
REQUEST_TIMEOUT = 10.0  # seconds
RETRY_COUNT = 3
DELAY = 1.0  # seconds between requests to prevent hitting rate limits

# Headers to blend in with normal browser requests
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Directories and Output paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(PROJECT_ROOT, "catalog", "raw")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "catalog", "processed")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
LOG_FILE = os.path.join(LOG_DIR, "scraper.log")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "data", "assessments.json")

# Ensure folders exist
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

# Run mode
# Set MOCK_MODE = True to run the crawler against local generated mock pages (fast, offline, deterministic)
# Set MOCK_MODE = False to crawl the live SHL website
MOCK_MODE = False

# Seed URLs for crawling
# When MOCK_MODE is True, the scraper will map these URLs to custom mock HTML pages.
# When MOCK_MODE is False, the scraper will visit these URLs directly.
SEED_URLS = [
    f"{BASE_URL}/products/assessments/personality-assessment/shl-occupational-personality-questionnaire-opq/",
    f"{BASE_URL}/products/assessments/personality-assessment/shl-motivation-questionnaire-mq/",
    f"{BASE_URL}/products/assessments/behavioral-assessments/situation-judgement-tests-sjt/",
    f"{BASE_URL}/products/assessments/behavioral-assessments/universal-competency-framework/",
    f"{BASE_URL}/products/assessments/behavioral-assessments/global-skills-assessment-gsa/",
    f"{BASE_URL}/products/assessments/skills-and-simulations/coding-simulations/",
    f"{BASE_URL}/products/assessments/skills-and-simulations/language-evaluation/",
    f"{BASE_URL}/products/assessments/skills-and-simulations/call-center-simulations/",
    f"{BASE_URL}/products/assessments/skills-and-simulations/business-skills/",
    f"{BASE_URL}/products/assessments/skills-and-simulations/technical-skills/",
    f"{BASE_URL}/products/assessments/cognitive-assessments/",
    f"{BASE_URL}/products/assessments/job-focused-assessments/",
]
