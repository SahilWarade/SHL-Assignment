from typing import Any, Dict, List, Optional
from retriever.search import SearchEngine
from agent.constraint_extractor import ConstraintExtractor
from agent.models import HiringConstraints, Message
from agent.utils import logger


# Lazy initialize search engine to avoid loading weights unless necessary
_search_engine: Optional[SearchEngine] = None
_constraint_extractor: Optional[ConstraintExtractor] = None

def get_search_engine() -> SearchEngine:
    """Lazy loader for SearchEngine to ensure local resource efficiency."""
    global _search_engine
    if _search_engine is None:
        try:
            _search_engine = SearchEngine()
        except Exception as e:
            logger.error(f"Failed to load SearchEngine in tools: {e}")
            raise e
    return _search_engine


def get_constraint_extractor() -> ConstraintExtractor:
    """Lazy loader for ConstraintExtractor."""
    global _constraint_extractor
    if _constraint_extractor is None:
        _constraint_extractor = ConstraintExtractor()
    return _constraint_extractor


def search_assessments(query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Search assessments in the FAISS index semantically.
    Applies optional metadata post-filters.
    If filtered search returns empty, falls back to unfiltered search.
    """
    try:
        se = get_search_engine()
        results = se.search(query, top_k=5, filters=filters)
        
        # Fallback to unfiltered search if category post-filtering yields 0 results
        if not results and filters and "category" in filters:
            logger.info("Filtered search returned 0 results. Running search without category filter...")
            filters_fallback = {k: v for k, v in filters.items() if k != "category"}
            results = se.search(query, top_k=5, filters=filters_fallback)
            
        return [res.model_dump() for res in results]
    except Exception as e:
        logger.error(f"Error executing search tool for query '{query}': {e}")
        return []


def get_assessment(assessment_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves the full metadata dictionary for a single assessment ID.
    Returns None if not found.
    """
    try:
        se = get_search_engine()
        if se.metadata:
            # Search case-insensitive slug or H1 name
            target_slug = str(assessment_id).lower().strip().replace(" ", "-")
            for idx, item in se.metadata.items():
                item_id = str(item.get("id", "")).lower().strip()
                item_name = str(item.get("name", "")).lower().strip()
                if item_id == target_slug or target_slug in item_id or target_slug in item_name:
                    return item
        return None
    except Exception as e:
        logger.error(f"Error retrieving assessment ID '{assessment_id}': {e}")
        return None


def compare_assessments(name1: str, name2: str) -> Dict[str, Any]:
    """
    Retrieves and bundles metadata details for two assessment names side-by-side.
    """
    item1 = get_assessment(name1)
    item2 = get_assessment(name2)
    
    return {
        "assessment1": {
            "requested_name": name1,
            "found": item1 is not None,
            "data": item1
        },
        "assessment2": {
            "requested_name": name2,
            "found": item2 is not None,
            "data": item2
        }
    }


def extract_constraints(messages: List[Message]) -> Dict[str, Any]:
    """
    Tool wrapping the ConstraintExtractor to extract constraints from dialogue history.
    """
    extractor = get_constraint_extractor()
    constraints = extractor.extract_constraints(messages)
    return constraints.model_dump(exclude_none=True)
