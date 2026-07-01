import os
from typing import List
import numpy as np
from retriever import config

try:
    # Skip loading heavy PyTorch sentence-transformers on Vercel serverless environment
    if os.environ.get("VERCEL"):
        raise ImportError("Vercel environment: skipping heavy ML imports")
    from sentence_transformers import SentenceTransformer
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False


class EmbeddingModel:
    """
    Local embedding model wrapper using sentence-transformers.
    Attempts to load BAAI/bge-small-en-v1.5 and falls back to all-MiniLM-L6-v2.
    """

    def __init__(self):
        self.model = None
        if HAS_TRANSFORMERS:
            self._load_model()

    def _load_model(self):
        """Attempts to load the configured embedding model with a fallback mechanism."""
        try:
            # Try to load primary BGE model
            self.model = SentenceTransformer(config.EMBEDDING_MODEL)
        except Exception as e:
            # Fall back if primary model is unavailable (offline or network issues)
            try:
                self.model = SentenceTransformer(config.FALLBACK_MODEL)
            except Exception as ex:
                raise RuntimeError(
                    f"Failed to load both primary and fallback embedding models.\n"
                    f"Primary ({config.EMBEDDING_MODEL}) error: {e}\n"
                    f"Fallback ({config.FALLBACK_MODEL}) error: {ex}"
                )

    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generates dense vector embeddings for a list of text strings.
        Vectors are L2-normalized to allow FAISS Inner Product to represent Cosine Similarity.
        """
        if not self.model:
            # Stub embedding vectors when running without heavy PyTorch
            dim = getattr(config, "EMBEDDING_DIMENSION", 384)
            return np.zeros((len(texts), dim), dtype=np.float32)
            
        # normalize_embeddings=True guarantees unit vectors (L2 norm = 1.0)
        embeddings = self.model.encode(
            texts, 
            normalize_embeddings=True, 
            show_progress_bar=False
        )
        return np.array(embeddings, dtype=np.float32)
