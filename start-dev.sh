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
RED='\033[0;31m'
NC='\033[0m'

# Parse command line arguments
USE_DOCKER=false
NO_DATABASE=false
NO_CACHE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --docker)
            USE_DOCKER=true
            shift
            ;;
        --no-database)
            NO_DATABASE=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --minimal)
            NO_DATABASE=true
            NO_CACHE=true
            shift
            ;;
        --help)
            echo "Usage: ./start-dev.sh [options]"
            echo ""
            echo "Options:"
            echo "  --docker        Use full Docker mode (all services in containers)"
            echo "  --no-database   Start without PostgreSQL (sets ENABLE_DATABASE=false)"
            echo "  --no-cache      Start without Redis (sets ENABLE_CACHING=false)"
            echo "  --minimal       Start without database and cache (same as --no-database --no-cache)"
            echo "  --help          Show this help message"
            echo ""
            echo "Default: Hybrid mode (PostgreSQL/Redis in Docker, apps run natively)"
            echo ""
            echo "Examples:"
            echo "  ./start-dev.sh                    # Start with all services"
            echo "  ./start-dev.sh --minimal          # Start only backend and frontend"
            echo "  ./start-dev.sh --no-cache         # Start without Redis"
            echo "  ./start-dev.sh --docker --minimal # Use minimal docker-compose"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Function to update .env file
update_env_var() {
    local var_name=$1
    local var_value=$2
    local env_file=$3
    
    if grep -q "^${var_name}=" "$env_file"; then
        # Update existing variable
        sed -i.bak "s/^${var_name}=.*/${var_name}=${var_value}/" "$env_file"
    else
        # Add new variable
        echo "${var_name}=${var_value}" >> "$env_file"
    fi
}

if [ "$USE_DOCKER" = true ]; then
    if [ "$NO_DATABASE" = true ] && [ "$NO_CACHE" = true ]; then
        echo -e "${BLUE}Starting in Minimal Docker mode...${NC}"
        echo "Only backend and frontend will run in containers"
        echo ""
        
        # Start services with minimal docker-compose
        docker-compose -f docker-compose.minimal.yml up
    else
        echo -e "${BLUE}Starting in Full Docker mode...${NC}"
        echo "All services will run in containers"
        echo ""
        
        # Start all services with Docker Compose
        docker-compose up
    fi
else
    echo -e "${BLUE}Starting in Hybrid mode...${NC}"
    
    # Determine which services to start
    SERVICES_TO_START=""
    if [ "$NO_DATABASE" = false ]; then
        SERVICES_TO_START="$SERVICES_TO_START postgres"
    fi
    if [ "$NO_CACHE" = false ]; then
        SERVICES_TO_START="$SERVICES_TO_START redis"
    fi
    
    if [ -n "$SERVICES_TO_START" ]; then
        echo "Services to start in Docker:$SERVICES_TO_START"
    else
        echo "No Docker services needed (minimal mode)"
    fi
    echo ""
    
    # Check if Docker is running (only if we need it)
    if [ -n "$SERVICES_TO_START" ]; then
        if ! docker info >/dev/null 2>&1; then
            echo -e "${YELLOW}Docker is not running. Please start Docker Desktop first.${NC}"
            exit 1
        fi
        
        # Start Docker services
        echo "Starting Docker services..."
        docker compose up -d $SERVICES_TO_START
        
        # Wait for services to be ready
        if [ "$NO_DATABASE" = false ]; then
            echo "Waiting for database..."
            for i in {1..30}; do
                if docker compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
                    echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
                    break
                fi
                if [ $i -eq 30 ]; then
                    echo -e "${RED}PostgreSQL failed to start${NC}"
                    exit 1
                fi
                sleep 1
            done
        fi
        
        if [ "$NO_CACHE" = false ]; then
            echo "Waiting for Redis..."
            for i in {1..30}; do
                if docker compose exec -T redis redis-cli ping >/dev/null 2>&1; then
                    echo -e "${GREEN}✓ Redis is ready${NC}"
                    break
                fi
                if [ $i -eq 30 ]; then
                    echo -e "${RED}Redis failed to start${NC}"
                    exit 1
                fi
                sleep 1
            done
        fi
    fi
    
    # Update backend .env file based on flags
    cd server
    if [ -f .env ]; then
        # Update feature flags
        update_env_var "ENABLE_DATABASE" $([ "$NO_DATABASE" = true ] && echo "false" || echo "true") .env
        update_env_var "ENABLE_CACHING" $([ "$NO_CACHE" = true ] && echo "false" || echo "true") .env
        
        # Remove backup file
        rm -f .env.bak
    else
        echo -e "${YELLOW}Warning: server/.env file not found${NC}"
        echo "Creating minimal .env file..."
        cat > .env << EOF
ENVIRONMENT=development
DEBUG=True
SECRET_KEY=dev-secret-key-$(openssl rand -hex 16)
ENABLE_DATABASE=$( [ "$NO_DATABASE" = true ] && echo "false" || echo "true" )
ENABLE_CACHING=$( [ "$NO_CACHE" = true ] && echo "false" || echo "true" )
EOF
        if [ "$NO_DATABASE" = false ]; then
            echo "DATABASE_URL=postgresql://postgres:password@localhost:5432/trading_tools" >> .env
        fi
        if [ "$NO_CACHE" = false ]; then
            echo "REDIS_URL=redis://localhost:6379" >> .env
        fi
    fi
    
    # Start backend
    echo "Starting backend server..."
    source venv/bin/activate
    # Export environment variables from .env file
    set -a
    source .env
    set +a
    
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    cd ..
    
    # Start frontend
    echo "Starting frontend..."
    cd client
    npm run dev &
    FRONTEND_PID=$!
    cd ..
    
    # Function to cleanup on exit
    cleanup() {
        echo -e "\n${YELLOW}Shutting down services...${NC}"
        
        # Kill native processes
        if [ ! -z "$BACKEND_PID" ]; then
            kill $BACKEND_PID 2>/dev/null || true
        fi
        if [ ! -z "$FRONTEND_PID" ]; then
            kill $FRONTEND_PID 2>/dev/null || true
        fi
        
        # Stop Docker services if they were started
        if [ -n "$SERVICES_TO_START" ]; then
            echo "Stopping Docker services..."
            docker compose down
        fi
        
        echo -e "${GREEN}✓ All services stopped${NC}"
        exit 0
    }
    
    # Set up signal handlers
    trap cleanup INT TERM
    
    # Show access information
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════${NC}"
    echo -e "${GREEN}✓ Development environment is ready!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════${NC}"
    echo ""
    echo "Access your application at:"
    echo "  Frontend: http://localhost:3000"
    echo "  Backend:  http://localhost:8000"
    echo "  API Docs: http://localhost:8000/api/v1/docs"
    echo ""
    echo "Service Status:"
    echo -e "  Backend:  ${GREEN}Running${NC} (with hot-reload)"
    echo -e "  Frontend: ${GREEN}Running${NC} (with hot-reload)"
    echo -e "  Database: $([ "$NO_DATABASE" = true ] && echo "${YELLOW}Disabled${NC}" || echo "${GREEN}Running${NC}")"
    echo -e "  Cache:    $([ "$NO_CACHE" = true ] && echo "${YELLOW}Disabled${NC}" || echo "${GREEN}Running${NC}")"
    echo ""
    echo "Press Ctrl+C to stop all services"
    echo ""
    
    # Wait for interrupt
    wait
fi