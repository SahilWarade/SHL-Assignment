from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.dependencies import get_logger, get_orchestrator, get_retriever


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI.
    Loads FAISS index, metadata, embedding models, and agent orchestrator once on startup.
    """
    logger = get_logger()
    logger.info("--- Starting FastAPI Server Startup Sequence ---")
    
    try:
        # Pre-load FAISS retriever and embedding model weights
        logger.info("Loading FAISS Index and local SentenceTransformer model...")
        get_retriever()
        
        # Pre-load Agent Orchestrator
        logger.info("Loading Conversational Agent Orchestrator...")
        get_orchestrator()
        
        logger.info("--- Startup Sequence Completed Successfully ---")
    except Exception as e:
        logger.critical(f"Critical error during startup resource loading: {e}", exc_info=True)
        raise e

    yield
    
    logger.info("--- Starting FastAPI Server Shutdown Sequence ---")
    logger.info("--- Shutdown Sequence Completed ---")
