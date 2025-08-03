#!/bin/bash

# Trading Tools Development Environment Startup Script
# Default mode: Hybrid (Database in Docker, Apps native for hot-reloading)
# For full Docker mode, use: docker-compose up

# Check for local override script
if [ -f "start-dev.local.sh" ]; then
    echo "Using local override script: start-dev.local.sh"
    exec ./start-dev.local.sh "$@"
fi

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse command line arguments
USE_DOCKER=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --docker)
            USE_DOCKER=true
            shift
            ;;
        --help)
            echo "Usage: ./start-dev.sh [options]"
            echo ""
            echo "Options:"
            echo "  --docker    Use full Docker mode (all services in containers)"
            echo "  --help      Show this help message"
            echo ""
            echo "Default: Hybrid mode (PostgreSQL/Redis in Docker, apps run natively)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

if [ "$USE_DOCKER" = true ]; then
    echo -e "${BLUE}Starting in Full Docker mode...${NC}"
    echo "All services will run in containers"
    echo ""
    
    # Start all services with Docker Compose
    docker-compose up
else
    echo -e "${BLUE}Starting in Hybrid mode...${NC}"
    echo "Database/Cache in Docker, Apps run natively for hot-reloading"
    echo ""
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        echo -e "${YELLOW}Docker is not running. Please start Docker Desktop first.${NC}"
        exit 1
    fi
    
    # Start Docker services (PostgreSQL and Redis only)
    echo "Starting PostgreSQL and Redis..."
    docker compose up -d postgres redis
    
    # Wait for services to be ready
    echo "Waiting for database..."
    for i in {1..30}; do
        if docker compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
            echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "PostgreSQL failed to start"
            exit 1
        fi
        sleep 1
    done
    
    # Start backend
    echo "Starting backend server..."
    cd server
    source venv/bin/activate
    # Export environment variables from .env file
    if [ -f .env ]; then
    set -a
    source .env
    set +a
else
        echo -e "${YELLOW}Error: .env file not found${NC}"
        exit 1
    fi
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    cd ..
    
    # Start frontend
    echo "Starting frontend server..."
    cd client
    npm run dev &
    FRONTEND_PID=$!
    cd ..
    
    echo ""
    echo -e "${GREEN}Services started successfully!${NC}"
    echo ""
    echo "  Backend:  http://localhost:8000"
    echo "  Frontend: http://localhost:3000"
    echo "  API Docs: http://localhost:8000/docs"
    echo ""
    echo "Press Ctrl+C to stop all services"
    
    # Wait for interrupt
    trap "echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; docker compose stop postgres redis; exit" INT
    wait
fi
