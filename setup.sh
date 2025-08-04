#!/bin/bash

# Trading Tools Boilerplate - One Command Setup Script
# This script sets up the entire development environment

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ASCII Art Banner
print_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════╗"
    echo "║     Trading Tools Boilerplate Setup      ║"
    echo "╚══════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    local missing_deps=()
    
    # Check Python
    if ! command_exists python3; then
        missing_deps+=("Python 3.9+")
    else
        python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        print_success "Python $python_version found"
    fi
    
    # Check Node.js
    if ! command_exists node; then
        missing_deps+=("Node.js 18+")
    else
        node_version=$(node -v)
        print_success "Node.js $node_version found"
    fi
    
    # Check npm
    if ! command_exists npm; then
        missing_deps+=("npm")
    else
        npm_version=$(npm -v)
        print_success "npm $npm_version found"
    fi
    
    # Check Docker
    if ! command_exists docker; then
        missing_deps+=("Docker")
    else
        docker_version=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
        print_success "Docker $docker_version found"
    fi
    
    # Check Docker Compose
    if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
        missing_deps+=("Docker Compose")
    else
        print_success "Docker Compose found"
    fi
    
    # If missing dependencies, print and exit
    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "Missing required dependencies:"
        for dep in "${missing_deps[@]}"; do
            echo "  - $dep"
        done
        echo ""
        echo "Please install the missing dependencies and run this script again."
        exit 1
    fi
    
    print_success "All prerequisites met!"
}

# Ask about optional components
setup_optional_components() {
    print_info "Configuring optional components..."
    
    # Ask about database
    while true; do
        echo -n "Do you want to use database functionality? (y/n): "
        read -r use_database
        case $use_database in
            [Yy]* ) USE_DATABASE=true; break;;
            [Nn]* ) USE_DATABASE=false; break;;
            * ) echo "Please answer y or n.";;
        esac
    done
    
    # Ask about cache
    while true; do
        echo -n "Do you want to use caching functionality? (y/n): "
        read -r use_cache
        case $use_cache in
            [Yy]* ) USE_CACHE=true; break;;
            [Nn]* ) USE_CACHE=false; break;;
            * ) echo "Please answer y or n.";;
        esac
    done
    
    print_success "Optional components configured!"
}

# Create root .env file for Docker Compose
setup_root_env() {
    print_info "Setting up root environment file..."
    
    if [ ! -f .env ]; then
        print_info "Creating root .env file..."
        cat > .env << 'EOF'
# Docker Compose Environment Variables
ENVIRONMENT=development
SECRET_KEY=your-secret-key-here
SENTRY_DSN=
POLYGON_API_KEY=
NEXT_PUBLIC_SENTRY_DSN=
EOF
        print_warning "Please update .env with your actual configuration"
    else
        print_info "Root .env file already exists"
    fi
    
    print_success "Root environment setup complete!"
}

# Setup backend
setup_backend() {
    print_info "Setting up backend..."
    
    cd server
    
    # Remove existing virtual environment if it exists with permission issues
    if [ -d "venv" ]; then
        print_warning "Removing existing virtual environment..."
        rm -rf venv 2>/dev/null || {
            print_warning "Need elevated permissions to remove existing venv"
            print_info "Please enter your password to remove the existing virtual environment"
            sudo rm -rf venv
        }
    fi
    
    # Create Python virtual environment
    print_info "Creating Python virtual environment..."
    python3 -m venv venv
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    print_info "Upgrading pip..."
    pip install --upgrade pip
    
    # Install dependencies
    print_info "Installing Python dependencies..."
    pip install -r requirements.txt
    
    # Copy environment file
    if [ ! -f .env ]; then
        print_info "Creating .env file from example..."
        cp .env.example .env
        
        # Update ENABLE_DATABASE and ENABLE_CACHING based on user choices
        if [ "$USE_DATABASE" = false ]; then
            sed -i.bak 's/^ENABLE_DATABASE=.*/ENABLE_DATABASE=false/' .env
        fi
        if [ "$USE_CACHE" = false ]; then
            sed -i.bak 's/^ENABLE_CACHING=.*/ENABLE_CACHING=false/' .env
        fi
        rm -f .env.bak
        
        print_warning "Please update .env with your API keys and configuration"
    else
        print_info ".env file already exists"
    fi
    
    # Create logs directory
    mkdir -p logs
    
    cd ..
    print_success "Backend setup complete!"
}

# Setup frontend
setup_frontend() {
    print_info "Setting up frontend..."
    
    cd client
    
    # Install dependencies
    print_info "Installing npm dependencies..."
    npm install
    
    # Copy environment file
    if [ ! -f .env.local ]; then
        print_info "Creating .env.local file from example..."
        cp .env.local.example .env.local
        print_warning "Please update .env.local with your configuration"
    else
        print_info ".env.local file already exists"
    fi
    
    cd ..
    print_success "Frontend setup complete!"
}

# Start Docker services
start_docker_services() {
    # Only start services if needed
    if [ "$USE_DATABASE" = false ] && [ "$USE_CACHE" = false ]; then
        print_info "Skipping Docker services (not needed for minimal setup)"
        return
    fi
    
    print_info "Starting Docker services..."
    
    # Check if Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker daemon is not running. Please start Docker Desktop."
        exit 1
    fi
    
    # Check Docker credentials
    print_info "Checking Docker configuration..."
    
    # Try to pull images first to catch credential issues early
    print_info "Pulling required Docker images..."
    if ! docker pull postgres:15-alpine >/dev/null 2>&1; then
        print_warning "Failed to pull postgres image. Trying without authentication..."
        # Reset Docker credentials helper if there's an issue
        docker logout >/dev/null 2>&1 || true
    fi
    
    if ! docker pull redis:7-alpine >/dev/null 2>&1; then
        print_warning "Failed to pull redis image. Trying without authentication..."
    fi
    
    # Determine which services to start
    SERVICES_TO_START=""
    if [ "$USE_DATABASE" = true ]; then
        SERVICES_TO_START="postgres"
    fi
    if [ "$USE_CACHE" = true ]; then
        if [ -n "$SERVICES_TO_START" ]; then
            SERVICES_TO_START="$SERVICES_TO_START redis"
        else
            SERVICES_TO_START="redis"
        fi
    fi
    
    # Start required services
    print_info "Starting Docker containers: $SERVICES_TO_START"
    if ! docker compose up -d $SERVICES_TO_START; then
        print_error "Failed to start Docker containers"
        print_info "Trying alternative approach..."
        
        # Try with explicit pull
        docker compose pull postgres redis || true
        docker compose up -d postgres redis || {
            print_error "Failed to start Docker services"
            print_info "Please check your Docker installation and try again"
            exit 1
        }
    fi
    
    # Wait for PostgreSQL to be ready (if enabled)
    if [ "$USE_DATABASE" = true ]; then
        print_info "Waiting for PostgreSQL to be ready..."
        for i in {1..30}; do
            if docker compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
                print_success "PostgreSQL is ready!"
                break
            fi
            if [ $i -eq 30 ]; then
                print_error "PostgreSQL failed to start"
                exit 1
            fi
            sleep 1
        done
    fi
    
    # Wait for Redis to be ready (if enabled)
    if [ "$USE_CACHE" = true ]; then
        print_info "Waiting for Redis to be ready..."
        for i in {1..30}; do
            if docker compose exec -T redis redis-cli ping >/dev/null 2>&1; then
                print_success "Redis is ready!"
                break
            fi
            if [ $i -eq 30 ]; then
                print_error "Redis failed to start"
                exit 1
            fi
            sleep 1
        done
    fi
}

# Run database migrations
run_migrations() {
    # Skip if database is not enabled
    if [ "$USE_DATABASE" = false ]; then
        print_info "Skipping database migrations (database not enabled)"
        return
    fi
    
    print_info "Running database migrations..."
    
    cd server
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Ensure we're in the correct directory for .env file
    print_info "Current directory: $(pwd)"
    
    # Check if .env file exists
    if [ ! -f .env ]; then
        print_error ".env file not found in server directory"
        exit 1
    fi
    
    # Export environment variables from .env file
    set -a  # automatically export all variables
    source .env
    set +a  # turn off automatic export
    
    # Run Alembic migrations
    print_info "Applying database migrations..."
    alembic upgrade head
    
    if [ $? -eq 0 ]; then
        print_success "Database migrations completed successfully!"
    else
        print_error "Database migrations failed"
        print_info "Checking database connection..."
        
        # Test database connection
        python -c "
import os
from sqlalchemy import create_engine
try:
    engine = create_engine(os.getenv('DATABASE_URL'))
    with engine.connect() as conn:
        print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
        "
        exit 1
    fi
    
    cd ..
}

# Create start scripts
create_start_scripts() {
    print_info "Creating start scripts..."
    
    # Copy the actual start-dev.sh content that supports optional components
    cat > start-dev.sh << 'START_DEV_CONTENT'
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
START_DEV_CONTENT

    # Create stop-dev.sh
    cat > stop-dev.sh << 'EOF'
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

# Stop Docker services
if docker compose ps --quiet postgres redis 2>/dev/null | grep -q .; then
    echo "Stopping Docker services..."
    docker compose stop postgres redis
fi

echo "All services stopped"
EOF

    # Make scripts executable
    chmod +x start-dev.sh stop-dev.sh
    
    print_success "Start scripts created!"
}

# Print next steps
print_next_steps() {
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Setup Complete!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Your configuration:"
    echo "  Database: $([ "$USE_DATABASE" = true ] && echo "Enabled" || echo "Disabled")"
    echo "  Cache:    $([ "$USE_CACHE" = true ] && echo "Enabled" || echo "Disabled")"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Update environment files with your API keys:"
    echo "   - server/.env"
    echo "   - client/.env.local"
    echo ""
    
    if [ "$USE_DATABASE" = true ] || [ "$USE_CACHE" = true ]; then
        echo "2. Choose your development mode:"
        echo ""
        echo "   ${BLUE}Option A - Hybrid Mode (Recommended)${NC}"
        echo "   Database/Redis in Docker, apps run natively with hot-reloading:"
        echo "   ./start-dev.sh"
        echo ""
        echo "   ${BLUE}Option B - Full Docker Mode${NC}"
        echo "   Everything runs in containers:"
        echo "   docker-compose up"
        echo ""
        echo "   ${BLUE}Option C - Minimal Mode${NC}"
        echo "   Run without selected components:"
        if [ "$USE_DATABASE" = false ]; then
            echo "   ./start-dev.sh --no-database"
        fi
        if [ "$USE_CACHE" = false ]; then
            echo "   ./start-dev.sh --no-cache"
        fi
        if [ "$USE_DATABASE" = false ] && [ "$USE_CACHE" = false ]; then
            echo "   ./start-dev.sh --minimal"
        fi
    else
        echo "2. Start your development environment:"
        echo ""
        echo "   ${BLUE}Minimal Mode${NC}"
        echo "   No external services needed:"
        echo "   ./start-dev.sh --minimal"
        echo ""
        echo "   Or use Docker:"
        echo "   docker-compose -f docker-compose.minimal.yml up"
    fi
    
    echo ""
    echo "3. Access the applications:"
    echo "   - Frontend: http://localhost:3000"
    echo "   - Backend API: http://localhost:8000"
    echo "   - API Documentation: http://localhost:8000/api/v1/docs"
    echo ""
    echo "4. To stop all services:"
    echo "   ./stop-dev.sh  (for hybrid mode)"
    echo "   Ctrl+C then 'docker-compose down' (for Docker mode)"
    echo ""
    echo -e "${YELLOW}Remember to configure your API keys before starting!${NC}"
    echo ""
}

# Main execution
main() {
    print_banner
    
    # Check if we're in the right directory
    if [ ! -d "server" ] || [ ! -d "client" ]; then
        print_error "This script must be run from the tool-boilerplate root directory"
        exit 1
    fi
    
    # Run setup steps
    check_prerequisites
    setup_optional_components
    setup_root_env
    setup_backend
    setup_frontend
    start_docker_services
    run_migrations
    create_start_scripts
    
    # Verify everything is working
    verify_setup
    
    # Print completion message
    print_next_steps
}

# Verify setup
verify_setup() {
    print_info "Verifying setup..."
    
    # Check if backend can start
    cd server
    source venv/bin/activate
    if [ -f .env ]; then
    set -a
    source .env
    set +a
else
    print_error ".env file not found"
    exit 1
fi
    
    print_info "Testing backend startup..."
    python -c "
import sys
sys.path.append('.')
try:
    from app.core.config import settings
    print(f'✓ Configuration loaded successfully')
    print(f'  Environment: {settings.environment}')
    print(f'  Database enabled: {settings.enable_database}')
    if settings.enable_database and settings.database_url:
        print(f'  Database URL: {settings.database_url.split(\"@\")[1] if \"@\" in settings.database_url else settings.database_url}')
    print(f'  Cache enabled: {settings.enable_caching}')
    if settings.enable_caching and settings.redis_url:
        print(f'  Redis URL: {settings.redis_url}')
except Exception as e:
    print(f'✗ Configuration error: {e}')
    sys.exit(1)
    "
    
    if [ $? -eq 0 ]; then
        print_success "Backend configuration verified!"
    else
        print_error "Backend configuration failed - check your .env file"
        exit 1
    fi
    
    cd ..
}

# Run main function
main
