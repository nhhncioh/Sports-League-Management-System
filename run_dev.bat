@echo off
REM Development server launcher for Windows

echo Sports League Management System - Development Server
echo ======================================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

REM Check if virtual environment exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo No virtual environment found. Using system Python...
    echo Tip: Create a virtual environment with: python -m venv venv
)

REM Check if requirements are installed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Flask not found. Installing requirements...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install requirements
        pause
        exit /b 1
    )
)

REM Set environment variables
set FLASK_APP=main.py
set FLASK_ENV=development
set FLASK_DEBUG=1

echo.
echo Starting development server...
echo Available at: http://localhost:5000
echo Press Ctrl+C to stop
echo.

REM Run the development server
python run_dev.py

pause