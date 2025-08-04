#!/bin/bash

# Stop all services gracefully

echo "Stopping all services..."

# Read PIDs from files if they exist
BACKEND_PID=""
FRONTEND_PID=""

if [ -f .backend.pid ]; then
    BACKEND_PID=$(cat .backend.pid)
    rm -f .backend.pid
fi

if [ -f .frontend.pid ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    rm -f .frontend.pid
fi

# Stop backend
if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "Stopping backend (PID: $BACKEND_PID)..."
    kill "$BACKEND_PID"
else
    echo "Backend not found via PID file, searching for process..."
    # More specific pattern to avoid killing unrelated processes
    pkill -f "uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
fi

# Stop frontend
if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    echo "Stopping frontend (PID: $FRONTEND_PID)..."
    kill "$FRONTEND_PID"
else
    echo "Frontend not found via PID file, searching for process..."
    # More specific pattern for Next.js dev server
    pkill -f "next dev"
fi

# Stop Docker services if they're running
if docker info >/dev/null 2>&1; then
    # Check if any services are actually running
    services_running=false
    if docker compose ps --quiet postgres 2>/dev/null | grep -q .; then
        services_running=true
    fi
    if docker compose ps --quiet redis 2>/dev/null | grep -q .; then
        services_running=true
    fi
    
    if [ "$services_running" = true ]; then
        echo "Stopping Docker services..."
        docker compose stop postgres redis
        echo "Docker services stopped"
    else
        echo "No Docker services were running"
    fi
else
    echo "Docker is not running"
fi

echo ""
echo "All services stopped"
