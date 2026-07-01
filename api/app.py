import time
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from api import config
from api.routes import router
from api.startup import lifespan
from api.dependencies import get_logger

# 1. Initialize FastAPI with metadata and lifespan pre-loader
app = FastAPI(
    title=config.TITLE,
    description=config.DESCRIPTION,
    version=config.VERSION,
    lifespan=lifespan
)

# 2. Register Router
app.include_router(router)


# --- Custom Exception Handlers (Never expose stack traces) ---

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Formats clean JSON responses for standard HTTP exceptions (400, 404, etc)."""
    logger = get_logger()
    logger.warning(f"HTTPException on {request.url.path}: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Formats clean JSON validation errors (422) for bad user payloads."""
    logger = get_logger()
    logger.warning(f"ValidationError on {request.url.path}: {exc.errors()}")
    # Simplify the validation error details for response shielding
    errors_summary = [
        {"loc": err["loc"], "msg": err["msg"], "type": err["type"]} 
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation Error", "errors": errors_summary}
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception shield (500) logging trace to file and returning general message."""
    logger = get_logger()
    logger.critical(
        f"Unhandled Server Error on {request.method} {request.url.path}: {exc}", 
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal Server Error"}
    )


# --- Logging and Latency Middleware ---

@app.middleware("http")
async def log_request_middleware(request: Request, call_next):
    """Logs incoming request method, path, final status code, and latency in ms."""
    logger = get_logger()
    t_start = time.time()
    
    # Log incoming request
    logger.info(f"Incoming Request: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        duration_ms = (time.time() - t_start) * 1000.0
        
        logger.info(
            f"Response: {request.method} {request.url.path} | "
            f"Status: {response.status_code} | "
            f"Latency: {duration_ms:.2f}ms"
        )
        return response
    except Exception as e:
        duration_ms = (time.time() - t_start) * 1000.0
        logger.error(
            f"Failed Request: {request.method} {request.url.path} | "
            f"Latency: {duration_ms:.2f}ms | Error: {e}"
        )
        raise e
