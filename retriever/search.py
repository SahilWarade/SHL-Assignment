import os
import sys
import time
from typing import Any, Dict, List, Optional
from pydantic import ValidationError
from retriever import config, utils
from retriever.embedding_model import EmbeddingModel
from retriever.models import SearchResult
from retriever.utils import logger

try:
    # Skip loading heavy C++ FAISS library on Vercel serverless runs
    if os.environ.get("VERCEL"):
        raise ImportError("Vercel environment: skipping FAISS imports")
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False
    faiss = None

try:
    import numpy as np
except ImportError:
    np = None


class SearchEngine:
    """
    Search engine class that loads the FAISS index and metadata
    and executes semantic searches with post-filtering.
    Provides a keyword-overlap search fallback for serverless deployments.
    """

    def __init__(self):
        self.index = None
        self.metadata = None
        self.embedding_model = None
        self._load_resources()

    def _load_resources(self):
        """Loads FAISS index, metadata mapping, and embedding model."""
        if not os.path.exists(config.METADATA_PATH):
            raise FileNotFoundError(
                f"Metadata file not found at {config.METADATA_PATH}. Please ensure it is built."
            )

        logger.info("Loading search engine resources...")
        self.metadata = utils.metadata_loader(config.METADATA_PATH)
        
        if HAS_FAISS and os.path.exists(config.VECTOR_INDEX_PATH):
            try:
                self.index = faiss.read_index(config.VECTOR_INDEX_PATH)
                logger.info("FAISS index loaded successfully.")
            except Exception as e:
                logger.warning(f"Failed to load FAISS index: {e}. Falling back to keyword search.")
                self.index = None
        else:
            logger.info("FAISS index not loaded (running in serverless or fallback mode). Using keyword search.")
            self.index = None

        self.embedding_model = EmbeddingModel()
        logger.info("Search engine resources loaded.")

    def match_filter(self, filter_val: Any, meta_val: Any) -> bool:
        """
        Helper method to check if a metadata value satisfies a filter criteria.
        Handles list overlaps and case-insensitive string matching.
        """
        if filter_val is None:
            return True
        if meta_val is None:
            return False

        if isinstance(meta_val, list):
            meta_val_lower = [str(item).lower().strip() for item in meta_val]
            if isinstance(filter_val, list):
                filter_val_lower = [str(item).lower().strip() for item in filter_val]
                return any(v in meta_val_lower for v in filter_val_lower)
            else:
                filter_str = str(filter_val).lower().strip()
                return filter_str in meta_val_lower
        else:
            if isinstance(filter_val, list):
                filter_val_lower = [str(item).lower().strip() for item in filter_val]
                return str(meta_val).lower().strip() in filter_val_lower
            else:
                return str(meta_val).lower().strip() == str(filter_val).lower().strip()

    def search(
        self, 
        query: str, 
        top_k: int = config.TOP_K, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Executes semantic search against the FAISS index.
        Falls back to keyword-based relevance matching if FAISS index is not loaded.
        """
        t_start = time.time()
        
        # 1. Normalize query
        norm_q = utils.normalize_query(query)
        if not norm_q:
            return []

        # 2. Check if FAISS is loaded, else fallback to keyword-based search
        if not HAS_FAISS or not self.index:
            logger.info("FAISS index not loaded. Executing keyword matching search...")
            return self._keyword_search(norm_q, top_k, filters)

        # Get query vector
        query_vector = self.embedding_model.get_embeddings([norm_q])
        
        # 3. Retrieve candidates from FAISS
        total_items = self.index.ntotal
        retrieval_k = min(100, total_items)
        scores, indices = self.index.search(query_vector, retrieval_k)
        
        scores = scores[0]
        indices = indices[0]
        results: List[SearchResult] = []
        
        # 4. Post-filtering and mapping
        for score, idx in zip(scores, indices):
            if idx == -1 or idx not in self.metadata:
                continue
                
            meta_item = self.metadata[idx]
            
            passed_filters = True
            if filters:
                for field, filter_val in filters.items():
                    if filter_val is not None:
                        meta_val = meta_item.get(field)
                        if not self.match_filter(filter_val, meta_val):
                            passed_filters = False
                            break
                            
            if not passed_filters:
                continue

            sim_score = float(score)
            try:
                search_res = SearchResult(
                    id=meta_item["id"],
                    name=meta_item["name"],
                    similarity_score=sim_score,
                    url=meta_item["url"],
                    metadata=meta_item
                )
                results.append(search_res)
            except ValidationError as e:
                logger.warning(f"Failed to validate search result: {e}")
                
            if len(results) >= top_k:
                break
                
        q_time = (time.time() - t_start) * 1000.0
        logger.info(
            f"Query: '{query}' | Semantic Search Time: {q_time:.2f}ms | "
            f"Retrieved Count: {len(results)}"
        )
        return results

    def _keyword_search(
        self, 
        query: str, 
        top_k: int = 5, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Stateless keyword-based search fallback for serverless environments (no FAISS/PyTorch)."""
        query_words = set(query.lower().split())
        scored_items = []
        
        # metadata can be a dict (keyed by index) or a list
        items = self.metadata.values() if isinstance(self.metadata, dict) else self.metadata
        
        for item in items:
            # Apply filters first
            passed_filters = True
            if filters:
                for field, filter_val in filters.items():
                    if filter_val is not None:
                        meta_val = item.get(field)
                        if not self.match_filter(filter_val, meta_val):
                            passed_filters = False
                            break
            if not passed_filters:
                continue
                
            name_text = item.get("name", "").lower()
            desc_text = item.get("description", "").lower()
            skills_text = " ".join(item.get("skills_measured", [])).lower()
            
            score = 0.0
            for word in query_words:
                if word in name_text:
                    score += 5.0
                if word in desc_text:
                    score += 1.0
                if word in skills_text:
                    score += 2.0
            
            if score > 0:
                scored_items.append((score, item))
                
        # Sort by score descending
        scored_items.sort(key=lambda x: x[0], reverse=True)
        
        # Fallback: if no keyword matches, return first top_k filtered items
        if not scored_items:
            fallback_items = []
            for item in items:
                passed_filters = True
                if filters:
                    for field, filter_val in filters.items():
                        if filter_val is not None:
                            meta_val = item.get(field)
                            if not self.match_filter(filter_val, meta_val):
                                passed_filters = False
                                break
                if passed_filters:
                    fallback_items.append((0.01, item))
                    if len(fallback_items) >= top_k:
                        break
            scored_items = fallback_items
            
        results = []
        for score, meta_item in scored_items[:top_k]:
            try:
                search_res = SearchResult(
                    id=meta_item["id"],
                    name=meta_item["name"],
                    similarity_score=float(score),
                    url=meta_item["url"],
                    metadata=meta_item
                )
                results.append(search_res)
            except ValidationError as e:
                logger.warning(f"Failed to validate keyword search result: {e}")
                
        return results


def run_interactive_cli():
    """Runs the interactive Command Line Interface for searching the index."""
    print("\n" + "="*60)
    print("SHL ASSESSMENT SEMANTIC SEARCH CLI")
    print("="*60)
    print("Loading Search Engine... Please wait.")
    
    try:
        engine = SearchEngine()
        print("Search Engine Loaded Successfully!")
        print("Type your query to search. Type 'exit' or 'quit' to close.")
        print("="*60 + "\n")
    except Exception as e:
        print(f"\nError initializing search engine: {e}")
        sys.exit(1)

    while True:
        try:
            query = input("Search > ")
            if not query.strip():
                continue
            if query.strip().lower() in ["exit", "quit"]:
                break
                
            results = engine.search(query, top_k=10)
            if not results:
                print("\nNo matching assessments found.\n")
                continue
                
            print(f"\nTop {len(results)} matches:")
            print("-" * 80)
            for idx, res in enumerate(results, 1):
                print(f"{idx}. [{res.id}] {res.name} (Relevance Score: {res.similarity_score:.4f})")
                print(f"   URL: {res.url}")
                print("-" * 80)
            print()
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Search failed with error: {e}\n")


if __name__ == "__main__":
    run_interactive_cli()
