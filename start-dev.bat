@echo off
REM Start development servers on Windows
REM Default mode: Hybrid (Database in Docker, Apps native for hot-reloading)

REM Check for local override script
if exist "start-dev.local.bat" (
    echo Using local override script: start-dev.local.bat
    call start-dev.local.bat %*
    exit /b %errorlevel%
)

setlocal enabledelayedexpansion

echo Starting Trading Tools Development Environment (Windows)
echo ======================================================
echo.

REM Check if virtual environment exists
if not exist "server\venv\Scripts\activate.bat" (
    echo ERROR: Python virtual environment not found
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Check Docker availability
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Docker is not running.
    echo Please start Docker Desktop for database services.
    echo.
    echo Continuing with local services only...
    echo.
) else (
    echo Starting PostgreSQL and Redis in Docker...
    docker-compose up -d postgres redis
    
    REM Wait for PostgreSQL to be ready
    echo Waiting for database...
    set count=0
    :wait_loop
    docker-compose exec -T postgres pg_isready -U postgres >nul 2>&1
    if %errorlevel% equ 0 (
        echo Database is ready!
        goto :db_ready
    )
    set /a count+=1
    if %count% geq 30 (
        echo ERROR: Database failed to start
        pause
        exit /b 1
    )
    timeout /t 1 /nobreak >nul
    goto :wait_loop
    :db_ready
)

REM Start backend in new window with environment variables
echo Starting backend server...
start "Trading Tools - Backend" cmd /k "cd server && venv\Scripts\activate && for /f "tokens=*" %%i in ('type .env ^| findstr /v ^#') do set %%i && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

REM Wait a moment
timeout /t 2 /nobreak >nul

REM Start frontend in new window
echo Starting frontend server...
start "Trading Tools - Frontend" cmd /k "cd client && npm run dev"

echo.
echo Development servers started in separate windows:
echo - Backend:  http://localhost:8000
echo - Frontend: http://localhost:3000
echo - API Docs: http://localhost:8000/docs
echo.
echo To stop servers, close the command windows or use stop-dev.bat
echo.
pause