# Conversational SHL Assessment Recommender

A production-grade, highly optimized conversational agent and retrieval API developed using **FastAPI**, **SentenceTransformers (BGE-small-en-v1.5)**, **FAISS**, and agentic intent/constraint states. The application scrapes and parses the official SHL Individual Test Solutions catalog, builds a dense vector index, reasons over conversation dialogue history to formulate recommendations, side-by-side compares tests, and handles out-of-scope/prompt-injection requests.

---

## Key Features

1.  **SHL Catalog Parser (Phase 1)**: Robust scrapers with automatic retry backing, parsing descriptions, categories, and target requirements from the real SHL catalog.
2.  **Dense Semantic Retrieval (Phase 2)**: Encodes assessment details locally using `BAAI/bge-small-en-v1.5` embeddings and matches query intent with Cosine Similarity using a local FAISS index.
3.  **Agentic State Analyzer (Phase 3)**: A stateless agent architecture that classifies user intent (`clarification`, `recommendation`, `refinement`, `comparison`, `refusal`) and parses criteria constraints into strict Pydantic schemas.
4.  **FastAPI Backend & Interactive UI (Phase 4)**: Exposes endpoints `GET /health` and `POST /chat` with custom error handles and serving a premium, responsive glassmorphic chat client at root `/`.
5.  **In-Memory Client IP Rate Limiting**: Limit clients to a maximum of **10 requests per 24-hour window**, returning structured HTTP 429 Too Many Requests errors with countdown durations.

---

## Project Structure

```text
SHL-BOT/
│
├── api/                          # FastAPI Backend Layer
│   ├── templates/
│   │   └── index.html            # Premium glassmorphic chat UI
│   ├── config.py                 # API server and dotenv loading parameters
│   ├── dependencies.py           # Dependency Injection containers (Agent, SearchEngine)
│   ├── routes.py                 # GET /health, POST /chat, and root / HTML views
│   ├── schemas.py                # Pydantic validation schemas
│   └── startup.py                # Lifespan cache loader (loads index once on startup)
│
├── agent/                        # Conversational AI Agent Layer
│   ├── prompts/                  # Segmented markdown prompt templates
│   ├── config.py                 # Turn policies, logging paths, and LLM settings
│   ├── constraint_extractor.py   # Extracts criteria constraints (role, level, types)
│   ├── intent_classifier.py      # Dialog intent classifier
│   ├── models.py                 # Pydantic agent state structures
│   ├── orchestrator.py           # Central gateway manager and test harness
│   ├── planner.py                # LLM planner & Rule-based fallback simulator
│   ├── state_analyzer.py         # Constructs and transitions dialog states
│   └── tools.py                  # API wrappers exposing retriever/comparisons
│
├── retriever/                    # Semantic Retrieval Engine
│   ├── build_index.py            # FAISS index compilation script
│   ├── config.py                 # Paths, models, and embeddings settings
│   ├── embedding_model.py        # SentenceTransformer local model load wrapper
│   ├── search.py                 # Dense vector search API
│   └── utils.py                  # Pydantic schemas and serialization utilities
│
├── tests/                        # Pytest Automated Test Suite
│   └── test_api.py               # 10 comprehensive endpoint test cases
│
├── logs/                         # Operational traces
│   ├── api.log                   # API server requests and latencies logs
│   └── agent.log                 # Agent intents and tools execution logs
│
├── vector_store/                 # Compiled database assets
│   ├── faiss.index               # Dense search index
│   └── metadata.pkl              # Pickled assessment metadata
│
├── .env.example                  # Environment configuration template
├── .env                          # Local environment settings
├── .gitignore                    # Git tracking ignore rules
├── requirements.txt              # Project packages list
├── main.py                       # ASGI startup entrypoint
└── start.bat                     # Easy-run deployment script for Windows
```

---

## Installation & Setup

### Prerequisites
*   Python 3.10 or 3.11
*   Pip package manager

### Standard Setup

1.  Clone/open the project workspace directory.
2.  Create a template `.env` file by copying the example:
    ```bash
    copy .env.example .env
    ```
3.  *(Optional)* Enter your Google Gemini key in the `.env` file:
    ```env
    GEMINI_API_KEY=your-gemini-api-key-here
    ```
    *Note: If no API key is provided, the agent runs in high-fidelity rule-based Consultant Simulator mode, which passes all unit tests without requiring a paid key.*

---

## Running the Application

### One-Command Startup (Windows)
Double-click or run the batch wrapper in your terminal:
```cmd
start.bat
```
This script automatically:
1.  Installs all pip dependencies in `requirements.txt`.
2.  Ensures the FAISS index is compiled from cached data.
3.  Runs the automated unit test suite (`pytest`).
4.  Starts the local FastAPI application server on `http://127.0.0.1:8000/`.

### Manual Startup
If running on Unix-based systems:
```bash
# 1. Install packages
pip install -r requirements.txt

# 2. Build FAISS index
python -m retriever.build_index

# 3. Run server
python main.py
```

---

## Verification & Testing

Verify system robustness by running the test suite:
```bash
python -m pytest tests/test_api.py -v
```
This runs 10 key test sequences:
*   `test_health_endpoint`: Asserts health check returns HTTP 200 `{"status": "ok"}`.
*   `test_chat_clarification`: Asserts vague requests trigger clarification asks.
*   `test_chat_recommendation`: Asserts criteria filters yield 5 recommendations mapped with name, URL, and test types.
*   `test_chat_comparison`: Asserts comparisons parse side-by-side structures.
*   `test_chat_refusal_prompt_injection`: Asserts injections are refused.
*   `test_chat_refusal_out_of_scope`: Asserts out-of-scope queries (e.g. general coding requests) are blocked.
*   `test_chat_malformed_*`: Confirms that empty messages list, invalid roles, or blank content return HTTP 422 validations.
*   `test_rate_limiting`: Asserts client IP rate limiter blocks requests (HTTP 429) after the 10-query limit.

---

## API Usage Reference

### 1. GET `/health`
*   **Path**: `http://127.0.0.1:8000/health`
*   **Response**:
    ```json
    {"status": "ok"}
    ```

### 2. POST `/chat`
*   **Path**: `http://127.0.0.1:8000/chat`
*   **Payload**:
    ```json
    {
      "messages": [
        {
          "role": "user",
          "content": "Hiring a Java Developer with 3 years experience."
        }
      ]
    }
    ```
*   **Response**:
    ```json
    {
      "reply": "Based on your requirements (Job Role: Java Developer, Level: Professional), here are the top recommended SHL test solutions:\n\n*   **[Fast, Simple Technical Skill Assessment](https://www.shl.com/products/assessments/skills-and-simulations/technical-skills/)**\n    - *Type*: Multiple Choice...",
      "recommendations": [
        {
          "name": "Fast, Simple Technical Skill Assessment",
          "url": "https://www.shl.com/products/assessments/skills-and-simulations/technical-skills/",
          "test_type": "Multiple Choice"
        }
      ],
      "end_of_conversation": true
    }
    ```
