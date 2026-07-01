import uvicorn
from api import config

if __name__ == "__main__":
    print(f"Starting {config.TITLE} server...")
    print(f"Docs available at: http://{config.HOST}:{config.PORT}/docs")
    uvicorn.run(
        "api.app:app", 
        host=config.HOST, 
        port=config.PORT, 
        reload=False  # Disabled reload for production pre-loading stability
    )
