import logging
import os
from agent import config

# --- Setup Logger ---
def setup_logging():
    """Configures structured logging to logs/agent.log and stdout."""
    logger = logging.getLogger("shl_agent")
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(filename)s:%(lineno)d]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        if not os.environ.get("VERCEL"):
            try:
                os.makedirs(os.path.dirname(config.LOG_FILE), exist_ok=True)
                fh = logging.FileHandler(config.LOG_FILE, encoding="utf-8")
                fh.setLevel(logging.INFO)
                fh.setFormatter(formatter)
                logger.addHandler(fh)
            except Exception:
                pass
        
    return logger

logger = setup_logging()
