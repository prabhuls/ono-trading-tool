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

REM Parse command line arguments
set "USE_DOCKER=false"
set "NO_DATABASE=false"
set "NO_CACHE=false"

:parse_args
if "%~1"=="" goto :end_parse
if /i "%~1"=="--docker" (
    set "USE_DOCKER=true"
) else if /i "%~1"=="--no-database" (
    set "NO_DATABASE=true"
) else if /i "%~1"=="--no-cache" (
    set "NO_CACHE=true"
) else if /i "%~1"=="--minimal" (
    set "NO_DATABASE=true"
    set "NO_CACHE=true"
) else if /i "%~1"=="--help" (
    echo Usage: start-dev.bat [options]
    echo.
    echo Options:
    echo   --docker        Use full Docker mode ^(all services in containers^)
    echo   --no-database   Start without PostgreSQL ^(sets ENABLE_DATABASE=false^)
    echo   --no-cache      Start without Redis ^(sets ENABLE_CACHING=false^)
    echo   --minimal       Start without database and cache ^(same as --no-database --no-cache^)
    echo   --help          Show this help message
    echo.
    echo Default: Hybrid mode ^(PostgreSQL/Redis in Docker, apps run natively^)
    echo.
    echo Examples:
    echo   start-dev.bat                    # Start with all services
    echo   start-dev.bat --minimal          # Start only backend and frontend
    echo   start-dev.bat --no-cache         # Start without Redis
    echo   start-dev.bat --docker --minimal # Use minimal docker-compose
    exit /b 0
) else (
    echo Unknown option: %~1
    echo Use --help for usage information
    exit /b 1
)
shift
goto :parse_args
:end_parse

echo Starting Trading Tools Development Environment (Windows)
echo ======================================================
echo.

REM Docker mode
if "%USE_DOCKER%"=="true" (
    if "%NO_DATABASE%"=="true" if "%NO_CACHE%"=="true" (
        echo Starting in Minimal Docker mode...
        echo Only backend and frontend will run in containers
        echo.
        docker-compose -f docker-compose.minimal.yml up
        exit /b %errorlevel%
    ) else (
        echo Starting in Full Docker mode...
        echo All services will run in containers
        echo.
        docker-compose up
        exit /b %errorlevel%
    )
)

REM Hybrid mode
echo Starting in Hybrid mode...

REM Determine which services to start
set "SERVICES_TO_START="
if "%NO_DATABASE%"=="false" set "SERVICES_TO_START=postgres"
if "%NO_CACHE%"=="false" (
    if defined SERVICES_TO_START (
        set "SERVICES_TO_START=!SERVICES_TO_START! redis"
    ) else (
        set "SERVICES_TO_START=redis"
    )
)

if defined SERVICES_TO_START (
    echo Services to start in Docker: !SERVICES_TO_START!
) else (
    echo No Docker services needed ^(minimal mode^)
)
echo.

REM Check if virtual environment exists
if not exist "server\venv\Scripts\activate.bat" (
    echo ERROR: Python virtual environment not found
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Check Docker availability (only if we need it)
if defined SERVICES_TO_START (
    docker info >nul 2>&1
    if !errorlevel! neq 0 (
        echo ERROR: Docker is not running.
        echo Please start Docker Desktop for database/cache services.
        pause
        exit /b 1
    )
    
    REM Start Docker services
    echo Starting Docker services...
    docker compose up -d !SERVICES_TO_START!
    
    REM Wait for services to be ready
    if "%NO_DATABASE%"=="false" (
        echo Waiting for database...
        set count=0
        :wait_db_loop
        docker compose exec -T postgres pg_isready -U postgres >nul 2>&1
        if !errorlevel! equ 0 (
            echo Database is ready!
            goto :db_ready
        )
        set /a count+=1
        if !count! geq 30 (
            echo ERROR: PostgreSQL failed to start
            pause
            exit /b 1
        )
        timeout /t 1 /nobreak >nul
        goto :wait_db_loop
        :db_ready
    )
    
    if "%NO_CACHE%"=="false" (
        echo Waiting for Redis...
        set count=0
        :wait_redis_loop
        docker compose exec -T redis redis-cli ping >nul 2>&1
        if !errorlevel! equ 0 (
            echo Redis is ready!
            goto :redis_ready
        )
        set /a count+=1
        if !count! geq 30 (
            echo ERROR: Redis failed to start
            pause
            exit /b 1
        )
        timeout /t 1 /nobreak >nul
        goto :wait_redis_loop
        :redis_ready
    )
)

REM Update backend .env file based on flags
cd server
if exist .env (
    REM Create a temporary file with updated values
    echo Updating environment configuration...
    
    REM Read existing .env and update ENABLE_DATABASE and ENABLE_CACHING
    set "temp_file=.env.tmp"
    
    REM Process each line of .env
    (for /f "usebackq tokens=*" %%A in (".env") do (
        set "line=%%A"
        set "updated=false"
        
        REM Check if line starts with ENABLE_DATABASE
        echo !line! | findstr /b "ENABLE_DATABASE=" >nul
        if !errorlevel! equ 0 (
            if "%NO_DATABASE%"=="true" (
                echo ENABLE_DATABASE=false
            ) else (
                echo ENABLE_DATABASE=true
            )
            set "updated=true"
        )
        
        REM Check if line starts with ENABLE_CACHING
        echo !line! | findstr /b "ENABLE_CACHING=" >nul
        if !errorlevel! equ 0 (
            if "%NO_CACHE%"=="true" (
                echo ENABLE_CACHING=false
            ) else (
                echo ENABLE_CACHING=true
            )
            set "updated=true"
        )
        
        REM If not updated, keep original line
        if "!updated!"=="false" echo !line!
    )) > !temp_file!
    
    REM Replace original file
    move /y !temp_file! .env >nul
) else (
    echo Warning: server\.env file not found
    echo Creating minimal .env file...
    (
        echo ENVIRONMENT=development
        echo DEBUG=True
        echo SECRET_KEY=dev-secret-key-%RANDOM%%RANDOM%%RANDOM%%RANDOM%
        if "%NO_DATABASE%"=="true" (
            echo ENABLE_DATABASE=false
        ) else (
            echo ENABLE_DATABASE=true
            echo DATABASE_URL=postgresql://postgres:password@localhost:5432/trading_tools
        )
        if "%NO_CACHE%"=="true" (
            echo ENABLE_CACHING=false
        ) else (
            echo ENABLE_CACHING=true
            echo REDIS_URL=redis://localhost:6379
        )
    ) > .env
)

REM Start backend in new window with environment variables
echo Starting backend server...
start "Trading Tools - Backend" cmd /k "venv\Scripts\activate && for /f "tokens=*" %%i in ('type .env ^| findstr /v ^#') do set %%i && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

cd ..

REM Wait a moment
timeout /t 2 /nobreak >nul

REM Start frontend in new window
echo Starting frontend server...
start "Trading Tools - Frontend" cmd /k "cd client && npm run dev"

echo.
echo =======================================
echo Development environment is ready!
echo =======================================
echo.
echo Access your application at:
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/api/v1/docs
echo.
echo Service Status:
if "%NO_DATABASE%"=="true" (
    echo   Database: Disabled
) else (
    echo   Database: Running
)
if "%NO_CACHE%"=="true" (
    echo   Cache:    Disabled
) else (
    echo   Cache:    Running
)
echo   Backend:  Running ^(with hot-reload^)
echo   Frontend: Running ^(with hot-reload^)
echo.
echo To stop servers, close the command windows or use stop-dev.bat
echo.
pause