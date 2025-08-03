@echo off
REM Trading Tools Boilerplate Setup Script for Windows
REM This script sets up the development environment on Windows

echo Trading Tools Boilerplate Setup (Windows)
echo ========================================
echo.

REM Check Python version
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://www.python.org/
    pause
    exit /b 1
)

REM Run the cross-platform Python setup script
echo Running setup...
python setup.py
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Setup failed
    pause
    exit /b 1
)

echo.
echo Setup completed successfully!
echo.
echo To activate the Python virtual environment, run:
echo   server\venv\Scripts\activate
echo.
pause