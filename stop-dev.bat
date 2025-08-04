@echo off
REM Stop development servers on Windows

echo Stopping Trading Tools Development Environment (Windows)
echo ======================================================
echo.

REM Kill backend processes by window title (most reliable on Windows)
echo Stopping backend server...
taskkill /F /FI "WindowTitle eq Trading Tools - Backend*" >nul 2>&1
if %errorlevel% equ 0 (
    echo Backend stopped successfully
) else (
    echo Backend was not running or already stopped
)

REM Kill frontend processes by window title
echo Stopping frontend server...
taskkill /F /FI "WindowTitle eq Trading Tools - Frontend*" >nul 2>&1
if %errorlevel% equ 0 (
    echo Frontend stopped successfully
) else (
    echo Frontend was not running or already stopped
)

REM Stop Docker services if running
docker info >nul 2>&1
if %errorlevel% equ 0 (
    REM Check which services are actually running
    set "services_running=false"
    docker compose ps --quiet postgres 2>nul | findstr . >nul
    if %errorlevel% equ 0 set "services_running=true"
    docker compose ps --quiet redis 2>nul | findstr . >nul
    if %errorlevel% equ 0 set "services_running=true"
    
    if "%services_running%"=="true" (
        echo Stopping Docker services...
        docker compose stop postgres redis >nul 2>&1
        if %errorlevel% equ 0 (
            echo Docker services stopped
        )
    ) else (
        echo No Docker services were running
    )
) else (
    echo Docker is not running
)

echo.
echo All services stopped.
echo.
pause