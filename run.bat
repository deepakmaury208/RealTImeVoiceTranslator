@echo off
REM Real-Time Voice Translator - Windows Startup Script

echo.
echo ================================================
echo  Real-Time Voice Translator
echo  FastAPI Application Launcher
echo ================================================
echo.

REM Check if .venv exists, if not use venv
if exist .venv (
    echo Activating virtual environment (.venv)...
    call .venv\Scripts\activate.bat
) else if exist venv (
    echo Activating virtual environment (venv)...
    call venv\Scripts\activate.bat
) else (
    echo ERROR: Virtual environment not found!
    echo Please create a virtual environment first:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate.bat
    pause
    exit /b 1
)

echo.
echo Virtual environment activated successfully!
echo.
echo Starting Real-Time Voice Translator...
echo Server will be available at: http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the FastAPI server
python main.py

pause
