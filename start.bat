@echo off
echo ====================================================================
echo SHL Conversational Recommender - Local Deployment Script
echo ====================================================================
echo.

echo [1/4] Checking and installing Python dependencies...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to install Python dependencies.
    pause
    exit /b %errorlevel%
)
echo.

echo [2/4] Guaranteeing FAISS search index is compiled...
python -m retriever.build_index
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to build semantic index.
    pause
    exit /b %errorlevel%
)
echo.

echo [3/4] Executing unit and API test suite...
python -m pytest tests/test_api.py -v
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Pytest suite had failures. Correct errors before running in production.
    pause
    exit /b %errorlevel%
)
echo.

echo [4/4] Starting FastAPI server on http://127.0.0.1:8000...
echo Docs are available at: http://127.0.0.1:8000/docs
echo.
python main.py

pause
