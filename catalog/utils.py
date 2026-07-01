import html
import logging
import os
import re
import time
from typing import List, Optional
from urllib.parse import urljoin
import requests
from catalog import config

# --- Setup Logger ---
def setup_logging():
    """Configures structured logging to file and stream handlers."""
    log_dir = config.LOG_DIR
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger("shl_scraper")
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers
    if not logger.handlers:
        # File handler (logs/scraper.log)
        fh = logging.FileHandler(config.LOG_FILE, encoding="utf-8")
        fh.setLevel(logging.INFO)

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(filename)s:%(lineno)d]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger

logger = setup_logging()


# --- HTTP Requesting with Exponential Backoff ---
def fetch_url(url: str, retries: int = config.RETRY_COUNT, timeout: float = config.REQUEST_TIMEOUT) -> Optional[str]:
    """
    Fetches the content of a URL using requests.
    Retries failed requests using exponential backoff.
    """
    headers = config.HEADERS
    backoff_factor = 2.0
    initial_delay = 1.0  # seconds

    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Fetching: {url} (Attempt {attempt}/{retries})")
            response = requests.get(url, headers=headers, timeout=timeout)
            
            # Raise exception for 4xx or 5xx client/server errors
            response.raise_for_status()
            
            # Respect request delays
            if config.DELAY > 0:
                time.sleep(config.DELAY)
                
            return response.text

        except (requests.RequestException, Exception) as e:
            logger.warning(f"Failed to fetch {url} on attempt {attempt}: {e}")
            if attempt == retries:
                logger.error(f"Failed to fetch {url} after {retries} attempts.")
                return None
            
            sleep_time = initial_delay * (backoff_factor ** (attempt - 1))
            logger.info(f"Sleeping for {sleep_time:.2f} seconds before retrying...")
            time.sleep(sleep_time)
            
    return None


# --- General Normalization & Cleanups ---
def clean_text(text: Optional[str]) -> str:
    """
    Cleans general string input by:
    - Decoding HTML entities
    - Stripping newlines and replacing with space
    - Removing duplicate spaces/whitespace
    - Removing duplicate commas
    """
    if not text:
        return ""
    
    # 1. Unescape HTML entities
    text = html.unescape(text)
    
    # 2. Replace newlines, tabs, and carriage returns with spaces
    text = re.sub(r"[\r\n\t]+", " ", text)
    
    # 3. Collapse multiple spaces into a single space
    text = re.sub(r"\s+", " ", text)
    
    # 4. Clean up duplicate commas (e.g. "a,,b" -> "a, b") and surrounding spaces
    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    
    return text.strip()


def normalize_url(relative_or_absolute_url: str) -> str:
    """Converts relative URLs to absolute URLs using BASE_URL."""
    if not relative_or_absolute_url:
        return ""
    # Ensure it uses absolute mapping
    return urljoin(config.BASE_URL, relative_or_absolute_url)


def generate_slug_id(name: str) -> str:
    """
    Generates a stable slug-based ID from a string name.
    Example: 'SHL Verify G+ Test' -> 'verify-g'
             'Occupational Personality Questionnaire OPQ32' -> 'opq32'
             'Java 8 New Skills' -> 'java-8-new'
    """
    # 1. Lowercase
    s = name.lower().strip()
    
    # Special manual maps for SHL standard products to ensure high compatibility
    if "verify" in s and re.search(r"\bg\b|\bg\+", s):
        return "verify-g"
    if "opq" in s or "occupational personality" in s:
        # Match opq32, opq32r, etc.
        m = re.search(r"opq\d*[a-z]*", s)
        if m:
            return m.group(0)
        return "opq32"
    if "java" in s and "8" in s:
        return "java-8-new"
    
    # 2. Replace non-alphanumeric characters with hyphens
    s = re.sub(r"[^a-z0-9]+", "-", s)
    
    # 3. Clean up duplicate hyphens and leading/trailing hyphens
    s = re.sub(r"-+", "-", s)
    s = s.strip("-")
    
    return s


def normalize_duration(duration_str: Optional[str]) -> Optional[str]:
    """
    Normalizes time durations.
    Converts:
    - '30 Minutes', '30 mins', 'Half Hour' -> '30 minutes'
    - '45 mins', '45 min' -> '45 minutes'
    - '1 Hour', '1 hr', '60 mins' -> '60 minutes'
    """
    if not duration_str:
        return None
    
    s = duration_str.lower().strip()
    
    # Direct mappings
    if s in ["half hour", "half-hour", "0.5 hour", "0.5 hr", "30 mins", "30 min", "30 minutes"]:
        return "30 minutes"
    if s in ["one hour", "1 hour", "1 hr", "60 mins", "60 min", "60 minutes"]:
        return "60 minutes"
    if s in ["45 mins", "45 min", "45 minutes"]:
        return "45 minutes"
    if s in ["15 mins", "15 min", "15 minutes"]:
        return "15 minutes"
    
    # Regex extract digits
    # Match strings like "35 mins", "35 minutes", "35 min", "35-minute"
    match = re.search(r"(\d+)\s*(?:min|minute|mins|minutes|hr|hour|hours|hrs)", s)
    if match:
        number = int(match.group(1))
        if "hour" in s or "hr" in s or "hrs" in s:
            # Convert hours to minutes
            return f"{number * 60} minutes"
        return f"{number} minutes"
        
    return clean_text(duration_str)


def clean_list(items: Optional[List[str]]) -> List[str]:
    """Cleans a list of strings by removing empty values, stripping whitespace, and deduplicating."""
    if not items:
        return []
    
    seen = set()
    cleaned = []
    for item in items:
        cleaned_item = clean_text(item)
        if cleaned_item and cleaned_item not in seen:
            seen.add(cleaned_item)
            cleaned.append(cleaned_item)
            
    return cleaned
