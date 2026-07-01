import os
import time
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from api.schemas import ChatRequest, ChatResponse, RecommendationItem
from api.dependencies import get_orchestrator, get_logger
from agent.orchestrator import ConversationalAgentOrchestrator
from agent.models import Message

router = APIRouter()

# --- In-Memory Rate Limiting Settings ---
RATE_LIMIT_STORE = {}  # client_ip -> list of timestamps
LIMIT_PER_DAY = 10
WINDOW_SECONDS = 86400  # 24 hours


def check_rate_limit(client_ip: str) -> None:
    """Checks if the client IP has exceeded the 10 prompts per day limit."""
    current_time = time.time()
    if client_ip not in RATE_LIMIT_STORE:
        RATE_LIMIT_STORE[client_ip] = []

    # Filter out timestamps older than 24 hours
    timestamps = [t for t in RATE_LIMIT_STORE[client_ip] if current_time - t < WINDOW_SECONDS]
    RATE_LIMIT_STORE[client_ip] = timestamps

    if len(timestamps) >= LIMIT_PER_DAY:
        oldest_t = timestamps[0]
        remaining = WINDOW_SECONDS - (current_time - oldest_t)
        hours = int(remaining // 3600)
        minutes = int((remaining % 3600) // 60)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum 10 queries per 24 hours allowed. Please try again in {hours} hours and {minutes} minutes."
        )

    # Record current timestamp
    RATE_LIMIT_STORE[client_ip].append(current_time)


@router.get("/", response_class=HTMLResponse)
async def get_index():
    """Serves the premium, responsive assessment chat UI at root."""
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=status.HTTP_200_OK)
    return HTMLResponse(content="<h1>SHL Recommender Server is running. Access /docs for API.</h1>", status_code=status.HTTP_200_OK)


@router.get("/health", status_code=status.HTTP_200_OK)
async def health():
    """GET /health endpoint returning static system status."""
    return {"status": "ok"}


@router.post(
    "/chat", 
    response_model=ChatResponse, 
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Bad Request"},
        422: {"description": "Unprocessable Entity"},
        429: {"description": "Too Many Requests"},
        500: {"description": "Internal Server Error"}
    }
)
async def chat(
    request: Request,
    payload: ChatRequest,
    orchestrator: ConversationalAgentOrchestrator = Depends(get_orchestrator),
    logger = Depends(get_logger)
):
    """
    POST /chat endpoint exposing the Conversational Agent.
    Accepts dialogue messages, checks rate limits, maps to Pydantic objects,
    runs the agent orchestrator, formats the output schema, and returns JSON.
    """
    t_start = time.time()
    
    # Check rate limiting using client IP
    client_ip = request.client.host if request.client else "127.0.0.1"
    check_rate_limit(client_ip)
    
    # 1. Convert api message schemas to agent messages models
    agent_messages = [
        Message(role=msg.role, content=msg.content) 
        for msg in payload.messages
    ]
    
    try:
        # 2. Invoke AI Agent Orchestrator
        agent_response = orchestrator.run(agent_messages)
        
        # 3. Formulate the official SHL Recommendations payload
        recommendations = []
        
        # Only populate recommendations if the action is recommendation or refinement
        if agent_response.action in ["recommendation", "refinement"] and agent_response.recommendations:
            for item in agent_response.recommendations:
                # Map metadata fields (category/assessment_type) to test_type
                test_type = item.get("assessment_type") or item.get("category") or "Talent Assessment"
                
                recommendations.append(
                    RecommendationItem(
                        name=item.get("name", "Unknown Assessment"),
                        url=item.get("url", "https://www.shl.com/products/assessments/"),
                        test_type=test_type
                    )
                )

        duration_ms = (time.time() - t_start) * 1000.0
        logger.info(
            f"Endpoint: POST /chat | Status: 200 | "
            f"Action: {agent_response.action.value} | "
            f"Rec Count: {len(recommendations)} | "
            f"Latency: {duration_ms:.2f}ms"
        )
        
        # 4. Return structured response
        return ChatResponse(
            reply=agent_response.reply,
            recommendations=recommendations,
            end_of_conversation=agent_response.end_of_conversation
        )
        
    except Exception as e:
        logger.error(f"Error handling /chat endpoint request: {e}", exc_info=True)
        # Raise HTTP 500 error which will be formatted cleanly by the global handler
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error"
        )
