@echo off
setlocal enabledelayedexpansion

REM ============================================================================
REM VibeVerse AI - Local Windows Startup Script
REM Starts FastAPI backend (port 8000) and Streamlit frontend (port 8501)
REM ============================================================================

cd /d "%~dp0"
echo.
echo ========================================================
echo   VibeVerse AI - Local Launcher
echo   Working Directory: %CD%
echo ========================================================
echo.

REM 1. Check virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Project virtual environment ".venv" was not found.
    echo Please create it first:
    echo     python -m venv .venv
    echo     .venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM 2. Check .env configuration
if not exist ".env" (
    if exist ".env.example" (
        echo [WARN] ".env" not found. Creating ".env" from ".env.example"...
        copy /Y ".env.example" ".env" >nul
        echo [INFO] Please review ".env" and configure your database settings.
    ) else (
        echo [ERROR] Neither ".env" nor ".env.example" was found.
        pause
        exit /b 1
    )
)

REM 3. Quick dependency sanity check inside .venv
".venv\Scripts\python.exe" -c "import fastapi, uvicorn, streamlit, sqlalchemy, plotly, sklearn" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Some required Python packages are missing in ".venv".
    echo Run: .venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM 4. Start FastAPI Backend if port 8000 is not already listening
netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    echo [INFO] FastAPI backend is already running on port 8000. Skipping duplicate launch.
) else (
    echo [START] Launching FastAPI backend on http://127.0.0.1:8000 ...
    start "VibeVerse AI - FastAPI Backend" cmd /k "cd /d "%CD%" && call ".venv\Scripts\activate.bat" && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"
    timeout /t 3 /nobreak >nul
)

REM 5. Start Streamlit Frontend if port 8501 is not already listening
netstat -ano | findstr ":8501 " | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    echo [INFO] Streamlit frontend is already running on port 8501. Skipping duplicate launch.
) else (
    echo [START] Launching Streamlit frontend on http://localhost:8501 ...
    start "VibeVerse AI - Streamlit Frontend" cmd /k "cd /d "%CD%" && call ".venv\Scripts\activate.bat" && python -m streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501"
)

echo.
echo ========================================================
echo   VibeVerse AI is ready!
echo   - Frontend App : http://localhost:8501
echo   - Backend API  : http://127.0.0.1:8000
echo   - Swagger Docs : http://127.0.0.1:8000/docs
echo ========================================================
echo.
exit /b 0
