import logging
import os
from typing import Optional
from agent import tools
from agent.orchestrator import ConversationalAgentOrchestrator
from retriever.search import SearchEngine
from api import config

class ApiContainer:
    """Singleton Container holding pre-loaded resources to avoid reloading on requests."""
    orchestrator: Optional[ConversationalAgentOrchestrator] = None
    logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    """Dependency injection provider for the API Logger."""
    if ApiContainer.logger is None:
        logger = logging.getLogger("shl_api")
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
            
            # Add FileHandler if NOT running on Vercel (read-only file system)
            if not os.environ.get("VERCEL"):
                try:
                    os.makedirs(os.path.dirname(config.LOG_FILE), exist_ok=True)
                    fh = logging.FileHandler(config.LOG_FILE, encoding="utf-8")
                    fh.setLevel(logging.INFO)
                    fh.setFormatter(formatter)
                    logger.addHandler(fh)
                except Exception:
                    pass
            
        ApiContainer.logger = logger
        
    return ApiContainer.logger


def get_orchestrator() -> ConversationalAgentOrchestrator:
    """Dependency injection provider for the Conversational AI Agent Orchestrator."""
    if ApiContainer.orchestrator is None:
        ApiContainer.orchestrator = ConversationalAgentOrchestrator()
    return ApiContainer.orchestrator


def get_retriever() -> SearchEngine:
    """Dependency injection provider for the FAISS Search Engine."""
    # Triggers lazy initialization inside agent.tools
    return tools.get_search_engine()
