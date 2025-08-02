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

## Initial Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd tool-boilerplate
```

### 2. Run the Setup Script

The easiest way to get started:

```bash
./setup.sh
```

This script will:
- Check prerequisites
- Set up Python virtual environment
- Install all dependencies
- Create environment files
- Start Docker services
- Create helper scripts

### 3. Configure Environment Variables

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

## Backend Development

### Starting the Backend

```bash
cd server
source venv/bin/activate  # On Windows: venv\Scripts\activate
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

1. Start PostgreSQL with Docker:
```bash
docker-compose up -d postgres
```

2. Run migrations:
```bash
cd server
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

1. Create a new migration:
```bash
alembic revision --autogenerate -m "Add new table"
```

2. Review the generated migration in `alembic/versions/`

3. Apply the migration:
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

### 1. Use the Makefile (if available)

```bash
cd server
make install     # Install dependencies
make run        # Run development server
make test       # Run tests
make lint       # Run linters
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

1. Review the [API Documentation](./API_DOCUMENTATION.md)
2. Check the [Architecture Guide](./ARCHITECTURE.md)
3. Read about [Deployment](./DEPLOYMENT.md)
4. Learn about [Security Best Practices](./SECURITY.md)