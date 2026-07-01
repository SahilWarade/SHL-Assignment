import os

# CENTRAL PROJECT DIRECTORIES
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
VECTOR_STORE_DIR = os.path.join(PROJECT_ROOT, "vector_store")

# FILE PATHS
ASSESSMENTS_JSON_PATH = os.path.join(DATA_DIR, "assessments.json")
VECTOR_INDEX_PATH = os.path.join(VECTOR_STORE_DIR, "faiss.index")
METADATA_PATH = os.path.join(VECTOR_STORE_DIR, "metadata.pkl")
LOG_FILE = os.path.join(LOG_DIR, "retriever.log")

# EMBEDDING SETTINGS
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
FALLBACK_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384  # Dimension for both BGE-small and all-MiniLM-L6-v2

# SEARCH SETTINGS
TOP_K = 10

# Ensure directories exist
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
