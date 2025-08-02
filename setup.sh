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
    
    # Start PostgreSQL and Redis
    print_info "Starting PostgreSQL and Redis containers..."
    if ! docker compose up -d postgres redis; then
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
    
    # Wait for PostgreSQL to be ready
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
    
    # Wait for Redis to be ready
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
}

# Run database migrations
run_migrations() {
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
    
    # Create start-dev.sh
    cat > start-dev.sh << 'EOF'
#!/bin/bash

# Start all services for development

echo "Starting Trading Tools development environment..."

# Start Docker services
docker compose up -d postgres redis

# Start backend
cd server
source venv/bin/activate
# Export environment variables from .env file
export $(grep -v '^#' .env | xargs)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Start frontend
cd client
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "Services started:"
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:3000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "kill $BACKEND_PID $FRONTEND_PID; docker compose down; exit" INT
wait
EOF

    # Create stop-dev.sh
    cat > stop-dev.sh << 'EOF'
#!/bin/bash

# Stop all services

echo "Stopping all services..."

# Stop backend
pkill -f "uvicorn app.main:app"

# Stop frontend
pkill -f "next dev"

# Stop Docker services
docker compose down

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
    echo "Next steps:"
    echo ""
    echo "1. Update environment files with your API keys:"
    echo "   - server/.env"
    echo "   - client/.env.local"
    echo ""
    echo "2. Start the development environment:"
    echo "   ./start-dev.sh"
    echo ""
    echo "3. Access the applications:"
    echo "   - Frontend: http://localhost:3000"
    echo "   - Backend API: http://localhost:8000"
    echo "   - API Documentation: http://localhost:8000/docs"
    echo ""
    echo "4. To stop all services:"
    echo "   ./stop-dev.sh"
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
    export $(grep -v '^#' .env | xargs)
    
    print_info "Testing backend startup..."
    python -c "
import sys
sys.path.append('.')
try:
    from app.core.config import settings
    print(f'✓ Configuration loaded successfully')
    print(f'  Environment: {settings.environment}')
    print(f'  Database URL: {settings.database_url.split(\"@\")[1] if \"@\" in settings.database_url else settings.database_url}')
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
