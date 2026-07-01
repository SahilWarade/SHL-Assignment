import os
import sys
import time
from typing import Any, Dict, List, Optional
import faiss
import numpy as np
from pydantic import ValidationError
from retriever import config, utils
from retriever.embedding_model import EmbeddingModel
from retriever.models import SearchResult
from retriever.utils import logger


class SearchEngine:
    """
    Search engine class that loads the FAISS index and metadata
    and executes semantic searches with post-filtering.
    """

    def __init__(self):
        self.index = None
        self.metadata = None
        self.embedding_model = None
        self._load_resources()

    def _load_resources(self):
        """Loads FAISS index, metadata mapping, and embedding model."""
        if not os.path.exists(config.VECTOR_INDEX_PATH) or not os.path.exists(config.METADATA_PATH):
            raise FileNotFoundError(
                "FAISS index or metadata file not found. Please build the index first using build_index.py."
            )

        logger.info("Loading search engine resources...")
        self.index = faiss.read_index(config.VECTOR_INDEX_PATH)
        self.metadata = utils.metadata_loader(config.METADATA_PATH)
        self.embedding_model = EmbeddingModel()
        logger.info("Resources loaded successfully.")

    def match_filter(self, filter_val: Any, meta_val: Any) -> bool:
        """
        Helper method to check if a metadata value satisfies a filter criteria.
        Handles list overlaps and case-insensitive string matching.
        """
        if filter_val is None:
            return True
        if meta_val is None:
            return False

        # If metadata is a list (e.g. skills, job_roles, tags)
        if isinstance(meta_val, list):
            meta_val_lower = [str(item).lower().strip() for item in meta_val]
            
            if isinstance(filter_val, list):
                # Check overlap (at least one filter element must be in metadata list)
                filter_val_lower = [str(item).lower().strip() for item in filter_val]
                return any(v in meta_val_lower for v in filter_val_lower)
            else:
                # Check inclusion of string in list
                filter_str = str(filter_val).lower().strip()
                return filter_str in meta_val_lower
                
        # If metadata is a string or single value
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
        First performs semantic retrieval, then applies metadata post-filtering,
        and returns Pydantic verified SearchResult structures.
        """
        t_start = time.time()
        
        # 1. Normalize and embed the query
        norm_q = utils.normalize_query(query)
        if not norm_q:
            return []

        # Get query vector (norm_embeddings=True makes it L2 unit length)
        query_vector = self.embedding_model.get_embeddings([norm_q])
        
        # 2. Retrieve candidates
        # Fetch a larger pool of candidates to allow for post-filtering
        total_items = self.index.ntotal
        retrieval_k = min(100, total_items)
        
        scores, indices = self.index.search(query_vector, retrieval_k)
        
        # Flatten outputs
        scores = scores[0]
        indices = indices[0]
        
        results: List[SearchResult] = []
        
        # 3. Post-filtering and mapping
        for score, idx in zip(scores, indices):
            # Check for invalid or empty FAISS indices
            if idx == -1 or idx not in self.metadata:
                continue
                
            meta_item = self.metadata[idx]
            
            # Apply optional filters
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

            # Convert FAISS Inner Product score (which is cosine similarity for normalized vectors)
            sim_score = float(score)
            
            # Format and validate using Pydantic model
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
                logger.warning(f"Failed to validate search result for item index {idx}: {e}")
                
            # Stop once we have reached the desired top_k count
            if len(results) >= top_k:
                break
                
        q_time = (time.time() - t_start) * 1000.0  # in ms
        logger.info(
            f"Query: '{query}' | Dimension: {config.EMBEDDING_DIMENSION} | "
            f"Index Size: {total_items} | Query Time: {q_time:.2f}ms | "
            f"Retrieved Count: {len(results)}"
        )
        
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
        print("Please build the FAISS index first by running:\n  python retriever/build_index.py\n")
        sys.exit(1)

    while True:
        try:
            query = input("Search > ")
            if not query.strip():
                continue
            if query.strip().lower() in ["exit", "quit"]:
                print("Exiting search CLI. Goodbye!")
                break
                
            t_start = time.time()
            results = engine.search(query, top_k=10)
            t_taken = (time.time() - t_start) * 1000.0
            
            if not results:
                print("\nNo matching assessments found.\n")
                continue
                
            print(f"\nTop {len(results)} assessments (similarity search in {t_taken:.2f}ms):")
            print("-" * 80)
            for idx, res in enumerate(results, 1):
                # Print similarity score, name, and URL
                print(f"{idx}. [{res.id}] {res.name}")
                print(f"   Similarity Score: {res.similarity_score:.4f}")
                print(f"   URL:              {res.url}")
                desc_snippet = res.metadata.get("description", "")
                if len(desc_snippet) > 150:
                    desc_snippet = desc_snippet[:150] + "..."
                print(f"   Description:      {desc_snippet}")
                print("-" * 80)
            print()
            
        except KeyboardInterrupt:
            print("\nExiting search CLI. Goodbye!")
            break
        except Exception as e:
            print(f"Search failed with error: {e}\n")


if __name__ == "__main__":
    run_interactive_cli()
