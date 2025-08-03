# Local Development Guide

This guide provides detailed instructions for setting up and running the Trading Tools platform locally.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Backend Development](#backend-development)
- [Frontend Development](#frontend-development)
- [Database Setup](#database-setup)
- [External API Integration](#external-api-integration)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

1. **Python 3.9+**
   ```bash
   python3 --version
   ```

2. **Node.js 18+ and npm**
   ```bash
   node --version
   npm --version
   ```

3. **Docker and Docker Compose**
   ```bash
   docker --version
   docker-compose --version
   ```

4. **Git**
   ```bash
   git --version
   ```

### Optional Software

- **PostgreSQL Client** (for database debugging)
  ```bash
  # macOS
  brew install postgresql
  
  # Ubuntu/Debian
  sudo apt-get install postgresql-client
  ```

- **Redis CLI** (for cache debugging)
  ```bash
  # macOS
  brew install redis
  
  # Ubuntu/Debian
  sudo apt-get install redis-tools
  ```

## Quick Start

```bash
# 1. Clone and setup
git clone <repository-url>
cd tool-boilerplate
python3 setup.py  # or ./setup.sh on Unix/macOS

# 2. Configure environment variables
# Edit server/.env and client/.env.local with your API keys

# 3. Start development environment
./start-dev.sh    # Unix/macOS
start-dev.bat     # Windows

# 4. Validate everything is working
python3 validate-setup.py
```

## Initial Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd tool-boilerplate
```

### 2. Run the Setup Script

The project includes a cross-platform setup script:

```bash
# Unix/macOS
./setup.sh

# Windows
setup.bat

# Python (cross-platform)
python3 setup.py
```

This script will:
- Check prerequisites (Python 3.9+, Node.js 18+, Docker)
- Set up Python virtual environment
- Install all dependencies
- Create environment files from templates
- Prompt for database setup preference

### 3. Configure Environment Variables

The setup script creates environment files from templates. There are three different `.env` files:

- **`.env`** (root) - Only for Docker Compose
- **`server/.env`** - Backend configuration 
- **`client/.env.local`** - Frontend configuration

See [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md) for detailed documentation.

#### Backend Configuration (server/.env)

```env
# Environment
ENVIRONMENT=development
DEBUG=True

# Security
SECRET_KEY=dev-secret-key-change-in-production

# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/trading_tools

# Redis
REDIS_URL=redis://localhost:6379

# External APIs
POLYGON_API_KEY=your-polygon-api-key

# Sentry (optional for local dev)
SENTRY_DSN=
SENTRY_ENVIRONMENT=development
```

#### Frontend Configuration (client/.env.local)

```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=Trading Tools Dev
NEXT_PUBLIC_ENVIRONMENT=development

# Sentry (optional for local dev)
NEXT_PUBLIC_SENTRY_DSN=
```

### 4. Development Modes

#### Hybrid Mode (Recommended)
Database and Redis run in Docker, applications run natively with hot-reloading:

```bash
# Start services
./start-dev.sh        # Unix/macOS
start-dev.bat         # Windows

# Stop services
./stop-dev.sh         # Unix/macOS
stop-dev.bat          # Windows
```

**Advantages:**
- Fast hot-reloading for code changes
- Easy debugging with native tools
- Lower resource usage

#### Full Docker Mode
Everything runs in containers:

```bash
# Start all services
docker-compose up

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**Advantages:**
- Consistent environment
- Closer to production setup
- No need to install Python/Node locally

#### Native Mode
Run everything locally without Docker:

```bash
# Requires local PostgreSQL and Redis installation
# Update DATABASE_URL and REDIS_URL in server/.env to point to local instances

# Backend
cd server && source venv/bin/activate && uvicorn app.main:app --reload

# Frontend (in another terminal)
cd client && npm run dev
```

### 5. Validate Your Setup

After starting your development environment, validate that everything is working:

```bash
python3 validate-setup.py
```

This checks:
- Configuration files exist
- Environment variables are set
- Python packages installed (in virtual environment)
- Node.js dependencies installed
- Docker availability
- Database connections
- **Running services** (Backend API, Frontend, Redis)

**Note:** Run this AFTER starting your development environment with `./start-dev.sh` or `docker-compose up`, as it checks if services are actually running.

## Backend Development

### Starting the Backend

#### Option 1: Using start-dev.sh (Recommended)
The `start-dev.sh` script starts PostgreSQL/Redis in Docker and runs the backend natively.

#### Option 2: Manual Start
```bash
cd server
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Load environment variables
export $(grep -v '^#' .env | xargs)  # Unix/macOS
# On Windows, manually set variables or use python-dotenv

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### API Documentation

Once running, access:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Backend File Structure

```
server/
├── app/
│   ├── api/           # API endpoints
│   │   └── v1/        # API version 1
│   ├── core/          # Core functionality
│   │   ├── config.py  # Settings management
│   │   ├── database.py # Database connection
│   │   ├── logging.py # Centralized logging
│   │   ├── cache.py   # Cache utilities
│   │   └── responses.py # Response formatting
│   ├── models/        # SQLAlchemy models
│   ├── schemas/       # Pydantic schemas
│   ├── services/      # Business logic
│   │   └── external/  # External API integrations
│   ├── utils/         # Database utilities
│   └── main.py        # FastAPI application
├── alembic/           # Database migrations
│   └── versions/      # Migration files
```

### Adding a New Endpoint

1. Create schema in `app/schemas/`:
```python
# app/schemas/trading.py
from pydantic import BaseModel

class TradeRequest(BaseModel):
    symbol: str
    quantity: int
    price: float
```

2. Create endpoint in `app/api/v1/endpoints/`:
```python
# app/api/v1/endpoints/trading.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.trading import TradeRequest
from app.core.responses import create_success_response
from app.core.database import get_db

router = APIRouter()

@router.post("/trade")
async def create_trade(
    trade: TradeRequest,
    db: AsyncSession = Depends(get_db)
):
    # Implementation with database
    return create_success_response(
        data={"trade_id": "12345"},
        message="Trade created successfully"
    )
```

3. Register router in `app/api/v1/__init__.py`:
```python
from .endpoints import trading
api_router.include_router(trading.router, prefix="/trading", tags=["trading"])
```

### Working with Database

Using the DatabaseCRUD utilities:
```python
from app.utils.database import DatabaseCRUD
from app.models.user import User

# Create CRUD instance
user_crud = DatabaseCRUD[User](User)

# Get user by ID
user = await user_crud.get(db, user_id)

# Get multiple users with filtering
users = await user_crud.get_multi(
    db,
    filters={"is_active": True},
    order_by="-created_at",
    limit=10
)

# Create a new user
new_user = await user_crud.create(
    db,
    obj_in={"email": "test@example.com", "username": "testuser"}
)
```

### Using the Logging System

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

# Different log levels
logger.debug("Debug message")
logger.info("Info message", extra_field="value")
logger.warning("Warning message")
logger.error("Error message", error=exception)

# Specialized logging
logger.log_api_request("/api/trade", "POST")
logger.log_api_response(200, 0.123)
logger.log_business_event("trade_executed", {"symbol": "AAPL"})
```

### Using the Cache System

```python
from app.core.cache import cache, cache_manager

# Using decorator
@cache(ttl=300, namespace="market_data")
async def get_price(symbol: str):
    return await fetch_price(symbol)

# Manual caching
await cache_manager.set("key", "value", ttl=600)
value = await cache_manager.get("key")
```

## Frontend Development

### Starting the Frontend

```bash
cd client
npm run dev
```

Access at: http://localhost:3000

### Frontend File Structure

```
client/
├── app/               # Next.js app router
│   ├── layout.tsx     # Root layout
│   └── page.tsx       # Home page
├── components/        # React components
├── lib/              # Utilities
│   ├── api.ts        # API client
│   └── monitoring.ts # Error monitoring
├── hooks/            # Custom React hooks
├── contexts/         # React contexts
└── types/            # TypeScript types
```

### Using the API Client

```typescript
import { api, ApiClient } from '@/lib/api';

// Using predefined endpoints
const health = await api.health.check();

// Using generic methods
const response = await ApiClient.get('/api/v1/custom-endpoint');
const created = await ApiClient.post('/api/v1/items', { name: 'Test' });
```

### Error Handling

```typescript
import { ErrorMonitoring, handleApiError } from '@/lib/monitoring';

try {
  const data = await api.example.get('123');
} catch (error) {
  const errorInfo = handleApiError(error);
  // Show error to user
  console.error(errorInfo.message);
}
```

## Database Setup

### Using PostgreSQL Locally

1. Start PostgreSQL with Docker (if not using start-dev.sh):
```bash
docker-compose up -d postgres redis
```

2. Run migrations:
```bash
cd server
source venv/bin/activate  # On Windows: venv\Scripts\activate
alembic upgrade head
```

3. Access PostgreSQL:
```bash
# Using psql
psql postgresql://postgres:password@localhost:5432/trading_tools

# Or using docker
docker-compose exec postgres psql -U postgres -d trading_tools
```

### Creating Migrations

1. Activate virtual environment:
```bash
cd server
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Create a new migration:
```bash
alembic revision --autogenerate -m "Add new table"
```

3. Review the generated migration in `alembic/versions/`

4. Apply the migration:
```bash
alembic upgrade head
```

### Working with Models

Example of creating a new model:
```python
# app/models/portfolio.py
from sqlalchemy import String, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id: Mapped[str] = mapped_column(UUID, primary_key=True)
    user_id: Mapped[str] = mapped_column(UUID, ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255))
    total_value: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="portfolios")
```

## External API Integration

### Adding a New External Service

1. Create service class:
```python
# app/services/external/alpaca_service.py
from .base import ExternalAPIService

class AlpacaService(ExternalAPIService):
    def __init__(self):
        super().__init__(
            service_name="alpaca",
            base_url="https://api.alpaca.markets",
            api_key=settings.alpaca_api_key,
            rate_limit=200.0  # 200 requests per minute
        )
    
    async def get_account(self):
        return await self.get("/v2/account")
```

2. Add configuration:
```python
# app/core/config.py
alpaca_api_key: Optional[str] = Field(None, env="ALPACA_API_KEY")
```

## Testing

### Backend Testing

```bash
cd server
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/test_api.py::test_health_check
```

### Frontend Testing

```bash
cd client
# Run tests
npm test

# Run with coverage
npm run test:coverage
```

### Integration Testing

```bash
# Start all services
docker-compose up -d

# Run integration tests
cd tests/integration
pytest
```

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

```bash
# Find process using port 8000
lsof -ti:8000

# Kill process
kill -9 $(lsof -ti:8000)
```

#### 2. Redis Connection Failed

```bash
# Check if Redis is running
docker ps | grep redis

# Restart Redis
docker-compose restart redis

# Check Redis logs
docker-compose logs redis
```

#### 3. Database Connection Issues

```bash
# Check PostgreSQL status
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Reset database
cd server
alembic downgrade base
alembic upgrade head

# Test connection
psql $DATABASE_URL -c "SELECT 1"
```

#### 4. Frontend Build Errors

```bash
# Clear Next.js cache
rm -rf .next

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

### Debug Mode

#### Backend Debug Mode
```python
# Enable debug logging
ENVIRONMENT=development
DEBUG=True

# Run with debug
uvicorn app.main:app --reload --log-level debug
```

#### Frontend Debug Mode
```bash
# Enable debug mode
NODE_ENV=development

# Run with verbose logging
npm run dev -- --verbose
```

### Monitoring Logs

```bash
# Backend logs
tail -f server/logs/app.log

# Docker logs
docker-compose logs -f

# Redis monitor
redis-cli monitor
```

## Development Tips

### 1. Quick Commands

```bash
# Validate setup
python3 validate-setup.py

# Start everything
./start-dev.sh

# Run backend only
cd server && source venv/bin/activate && uvicorn app.main:app --reload

# Run frontend only  
cd client && npm run dev

# Format Python code
cd server && source venv/bin/activate && black . && ruff check --fix

# Type check
cd server && source venv/bin/activate && mypy .
```

### 2. Hot Reloading

- Backend: Automatically reloads with `--reload` flag
- Frontend: Automatically reloads with Next.js

### 3. Database GUI Tools

- **TablePlus**: Universal database tool
- **pgAdmin**: PostgreSQL specific
- **DBeaver**: Free universal database tool
- **DataGrip**: JetBrains database IDE

### 4. API Testing Tools

- **Postman**: Full-featured API testing
- **Insomnia**: Lightweight alternative
- **HTTPie**: Command-line tool
- **Thunder Client**: VS Code extension

### 5. VS Code Extensions

Recommended extensions:
- Python
- Pylance
- ESLint
- Prettier
- Thunder Client
- Docker
- GitLens

## Next Steps

1. Review the [Environment Variables Guide](./ENVIRONMENT_VARIABLES.md)
2. Check the [Backend Coding Standards](./BACKEND_CODING_STANDARDS.md)
3. Review the [Frontend Coding Standards](./FRONTEND_CODING_STANDARDS.md)
4. Read about [Railway Deployment](./RAILWAY_DEPLOYMENT.md)
5. Understand the [Database Setup](./DATABASE_SETUP.md)