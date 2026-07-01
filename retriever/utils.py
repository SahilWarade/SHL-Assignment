import logging
import os
import pickle
import re
from typing import Any, Dict, Optional
from retriever import config

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False

# --- Setup Logger ---
def setup_logging():
    """Configures logging to logs/retriever.log and stdout."""
    logger = logging.getLogger("shl_retriever")
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
                os.makedirs(config.LOG_DIR, exist_ok=True)
                fh = logging.FileHandler(config.LOG_FILE, encoding="utf-8")
                fh.setLevel(logging.INFO)
                fh.setFormatter(formatter)
                logger.addHandler(fh)
            except Exception:
                pass
        
    return logger

logger = setup_logging()


# --- Math & Cleaning Utilities ---
def normalize_query(query: str) -> str:
    """Normalizes query text by lowercasing and collapsing redundant spacing."""
    if not query:
        return ""
    q = query.lower().strip()
    q = re.sub(r"\s+", " ", q)
    return q


def cosine_similarity(v1, v2) -> float:
    """
    Computes cosine similarity between two 1-D numpy arrays.
    If they are already L2 normalized, this is simply the dot product.
    """
    if not HAS_NUMPY:
        return 0.0
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    if norm_v1 == 0.0 or norm_v2 == 0.0:
        return 0.0
    return float(np.dot(v1, v2) / (norm_v1 * norm_v2))


# --- File Persistence Helpers ---
def save_embeddings(embeddings, filepath: str) -> None:
    """Saves dense embedding vectors to a numpy .npy file."""
    if not HAS_NUMPY:
        return
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    np.save(filepath, embeddings)
    logger.info(f"Saved {embeddings.shape} embedding matrix to: {filepath}")


def load_embeddings(filepath: str):
    """Loads dense embedding vectors from a numpy .npy file."""
    if not HAS_NUMPY:
        return None
    if not os.path.exists(filepath):
        logger.warning(f"Embedding matrix file not found: {filepath}")
        return None
    embeddings = np.load(filepath)
    logger.info(f"Loaded {embeddings.shape} embedding matrix from: {filepath}")
    return embeddings


def metadata_loader(filepath: str) -> Optional[Dict[str, Any]]:
    """Loads metadata dictionary from a pickle file."""
    if not os.path.exists(filepath):
        logger.warning(f"Metadata file not found: {filepath}")
        return None
    with open(filepath, "rb") as f:
        metadata = pickle.load(f)
    logger.info(f"Loaded metadata for {len(metadata)} assessments from: {filepath}")
    return metadata


def save_metadata(metadata: Dict[str, Any], filepath: str) -> None:
    """Saves metadata dictionary to a pickle file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "wb") as f:
        pickle.dump(metadata, f)
    logger.info(f"Saved metadata for {len(metadata)} assessments to: {filepath}")
