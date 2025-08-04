# Trading Tools Boilerplate

A production-ready boilerplate for building trading and investment tools with FastAPI (Python) backend and Next.js (TypeScript) frontend.

## 🚀 Features

### Backend (FastAPI)
- **Enterprise-level architecture** with clear separation of concerns
- **Optional database and caching** - Use only what you need
- **Centralized logging system** with structured JSON logging
- **Standardized API responses** for consistent client handling
- **Advanced caching system** with Redis integration and decorators (optional)
- **Comprehensive error monitoring** with Sentry integration
- **External API service pattern** with retry logic and rate limiting
- **Async database support** with PostgreSQL and SQLAlchemy ORM (optional)
- **API versioning** and OpenAPI documentation
- **Health checks** and readiness probes
- **Rate limiting** and security middleware

### Frontend (Next.js)
- **TypeScript** with strict type checking
- **Tailwind CSS** for styling
- **Error boundaries** with Sentry integration
- **API client** with interceptors and error handling
- **Simplified error monitoring** (performance monitoring disabled)
- **Responsive design** foundation
- **Environment-based configuration**
- **Standalone production builds** for optimized Docker deployment

### DevOps & Deployment
- **Docker** containerization for all services
- **Railway-ready** deployment configurations
- **Cross-platform setup** scripts (Windows, macOS, Linux)
- **Environment management** with examples
- **CI/CD ready** structure
- **Multi-architecture** Docker support (x86_64, ARM64)

## 📋 Prerequisites

- Python 3.9+ (3.11 recommended)
- Node.js 18+ (LTS recommended)
- Git

Optional:
- Docker & Docker Compose (only if using database/cache)
- PostgreSQL (if using database without Docker)
- Redis (if using cache without Docker)

## 🛠️ Quick Start

### Cross-Platform Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd tool-boilerplate

# Unix/Linux/macOS
./setup.sh

# Windows
setup.bat  # or setup.ps1 for PowerShell

# Universal (Python-based)
python setup.py  # or python3 setup.py
```

The setup script will ask:
- Do you want to use database functionality? (y/n)
- Do you want to use caching functionality? (y/n)

This will:
1. Check all prerequisites
2. Create Python virtual environment
3. Install all dependencies
4. Set up environment files
5. Start Docker services (only if needed)
6. Run database migrations (only if database enabled)
7. Create development scripts

### Development Modes

After setup, you can choose from several development modes:

#### 1. Hybrid Mode (Recommended for full features)
Database/Redis in Docker, applications run natively for hot-reloading:
```bash
./start-dev.sh    # Unix/macOS
start-dev.bat     # Windows
```

#### 2. Minimal Mode (No database/cache)
Perfect for lightweight tools:
```bash
./start-dev.sh --minimal    # Unix/macOS
start-dev.bat --minimal     # Windows
```

#### 3. Partial Modes
Use only what you need:
```bash
# Database only (no cache)
./start-dev.sh --no-cache
start-dev.bat --no-cache

# Cache only (no database)
./start-dev.sh --no-database
start-dev.bat --no-database
```

#### 4. Full Docker Mode
Everything runs in containers:
```bash
# With all services
docker-compose up

# Minimal (no database/cache)
docker-compose -f docker-compose.minimal.yml up
```

#### 5. Full Native Mode
Everything runs locally (requires local PostgreSQL/Redis):
```bash
# Configure local services in server/.env
./start-dev.sh    # Will use local services
```

### Manual Setup

If you prefer manual setup:

#### Backend Setup
```bash
cd server
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration
```

#### Frontend Setup
```bash
cd client
npm install
cp .env.local.example .env.local
# Edit .env.local with your configuration
```

#### Start Services
```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Run database migrations (in server directory)
alembic upgrade head

# Start backend (in server directory)
uvicorn app.main:app --reload

# Start frontend (in client directory)
npm run dev
```

## 👥 Team Development

### Local Development Overrides

When working in a team, developers can customize their local environment without affecting others:

```bash
# Create local override scripts (gitignored)
cp start-dev.sh start-dev.local.sh    # Unix/macOS
copy start-dev.bat start-dev.local.bat # Windows

# Local environment overrides
server/.env.local     # Backend overrides
client/.env.local.dev # Frontend overrides
```

The scripts automatically check for local versions first, allowing you to:
- Use different ports
- Connect to local databases
- Add debugging configurations
- Customize for your OS/setup

See [docs/LOCAL_OVERRIDES.md](docs/LOCAL_OVERRIDES.md) for detailed examples.

### Working with the Boilerplate

For new trading tools:
1. **Fork or use as template** - Don't clone directly
2. **Customize for your tool** - Update configs and branding
3. **Keep boilerplate updates** - Merge upstream changes when needed

```bash
# Set up for a new tool
git clone https://github.com/FinMC/trading-tools-boilerplate my-scanner
cd my-scanner
git remote add boilerplate https://github.com/MyTeam/trading-tools-boilerplate
git remote set-url origin https://github.com/MyTeam/my-scanner

# Get boilerplate updates later
git fetch boilerplate
git merge boilerplate/main
```

## 🔧 Configuration

### Environment Variables

#### Backend (.env)
```env
# Environment
ENVIRONMENT=development
SECRET_KEY=your-secret-key

# Optional Components
ENABLE_DATABASE=true  # Set to false for tools without persistence
ENABLE_CACHING=true   # Set to false for tools without caching

# Database (required if ENABLE_DATABASE=true)
DATABASE_URL=postgresql://postgres:password@localhost:5432/trading_tools

# Redis (required if ENABLE_CACHING=true)
REDIS_URL=redis://localhost:6379

# External APIs
POLYGON_API_KEY=your-polygon-key

# Sentry
SENTRY_DSN=your-sentry-dsn
```

#### Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SENTRY_DSN=your-frontend-sentry-dsn
```

## 📁 Project Structure

```
tool-boilerplate/
├── server/                 # FastAPI backend
│   ├── app/
│   │   ├── api/           # API endpoints
│   │   ├── core/          # Core functionality
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   ├── utils/         # Database utilities
│   │   └── main.py        # FastAPI app
│   ├── alembic/           # Database migrations
│   ├── requirements.txt
│   ├── Dockerfile
│   └── railway.json       # Railway deployment config
├── client/                 # Next.js frontend
│   ├── app/               # App router
│   ├── components/        # React components
│   ├── lib/               # Utilities
│   ├── package.json
│   ├── Dockerfile
│   └── railway.json       # Railway deployment config
├── docs/                   # Documentation
│   ├── BACKEND_CODING_STANDARDS.md
│   ├── FRONTEND_CODING_STANDARDS.md
│   ├── LOCAL_DEVELOPMENT.md
│   ├── LOCAL_OVERRIDES.md
│   ├── RAILWAY_DEPLOYMENT.md
│   ├── WINDOWS_SETUP.md
│   └── CROSS_PLATFORM_SETUP.md
├── docker-compose.yml      # Development services
├── docker-compose.dev.yml  # Development overrides
├── setup.sh               # Unix/macOS setup
├── setup.bat             # Windows setup
├── setup.ps1             # PowerShell setup
├── setup.py              # Universal Python setup
├── start-dev.sh          # Unix/macOS dev starter
├── start-dev.bat         # Windows dev starter
├── stop-dev.sh           # Unix/macOS dev stopper
├── stop-dev.bat          # Windows dev stopper
├── validate-setup.py     # Setup validation
├── .python-version       # Python version lock
├── CLAUDE.md            # AI assistant instructions
└── README.md
```

## 🎯 Optional Components

The boilerplate supports running without database and/or cache, making it perfect for:
- API gateway services
- Calculation tools
- Data transformation services
- Lightweight microservices

### When to Use Optional Components

| Tool Type | Database | Cache | Example |
|-----------|----------|-------|------|
| Data Scanner | ✓ | ✓ | Store scan results, cache API calls |
| API Gateway | ✗ | ✓ | Transform requests, cache responses |
| Calculator | ✗ | ✗ | Simple calculations, no storage |
| Report Generator | ✓ | ✗ | Store reports, no caching needed |

### Configuring Optional Components

```bash
# During setup
python setup.py
# Answer: n to "Do you want to use database functionality?"
# Answer: n to "Do you want to use caching functionality?"

# Or configure manually in server/.env
ENABLE_DATABASE=false
ENABLE_CACHING=false

# Then start with
./start-dev.sh --minimal
```

### API Behavior with Disabled Components

- **Database disabled**: Database-dependent endpoints return 503 Service Unavailable
- **Cache disabled**: Cache operations become no-ops (always miss, no errors)

See [Optional Components Guide](OPTIONAL_COMPONENTS.md) for detailed information.

## 🏗️ Architecture

### Backend Architecture

The backend follows a layered architecture:

1. **API Layer** (`app/api/`) - HTTP endpoints and request handling
2. **Service Layer** (`app/services/`) - Business logic
3. **Data Layer** (`app/models/`) - Database models (optional)
4. **Core Layer** (`app/core/`) - Shared utilities and configuration

### Key Components

#### Centralized Logging
```python
from app.core.logging import get_logger

logger = get_logger(__name__)
logger.log_api_request(endpoint="/api/data", method="GET")
logger.log_error(exception, context={"user_id": 123})
```

#### Standardized Responses
```python
from app.core.responses import create_success_response, create_error_response

# Success response
return create_success_response(
    data={"result": "success"},
    message="Operation completed"
)

# Error response
return create_error_response(
    error_code="VALIDATION_ERROR",
    message="Invalid input",
    status_code=400
)
```

#### Caching (Optional)
```python
from app.core.cache import cache

# Works even if caching is disabled (becomes no-op)
@cache(ttl=300, namespace="market_data")
async def get_stock_price(symbol: str):
    # This will be cached for 5 minutes if cache enabled
    return await fetch_price(symbol)
```

#### Database Dependencies (Optional)
```python
from app.core.dependencies import require_database, get_db

# This endpoint requires database
@router.get("/users")
@require_database
async def get_users(db: AsyncSession = Depends(get_db)):
    # Returns 503 if database is disabled
    return await db.execute(select(User)).scalars().all()

# This endpoint works with or without database
from app.core.dependencies import OptionalDatabase

@router.get("/status")
async def get_status(db: Optional[AsyncSession] = Depends(OptionalDatabase())):
    if db:
        user_count = await db.execute(select(func.count(User.id)))
        return {"users": user_count}
    return {"users": "database disabled"}
```

#### External API Services
```python
from app.services.external.base import ExternalAPIService

class PolygonService(ExternalAPIService):
    def __init__(self):
        super().__init__(
            service_name="polygon",
            base_url="https://api.polygon.io",
            rate_limit=12.0  # requests per second
        )
```

## 🚀 Deployment

### Railway Deployment

1. Create new project on Railway
2. Add services based on your needs:
   - PostgreSQL database (if ENABLE_DATABASE=true)
   - Redis (if ENABLE_CACHING=true)
3. Deploy backend:
   ```bash
   cd server
   railway up
   ```
4. Deploy frontend:
   ```bash
   cd client
   railway up
   ```
5. Set environment variables:
   - `ENABLE_DATABASE=true/false`
   - `ENABLE_CACHING=true/false`
   - Only add DATABASE_URL/REDIS_URL if enabled

### Docker Deployment

```bash
# Full deployment (with database and cache)
docker-compose up -d

# Minimal deployment (no database/cache)
docker-compose -f docker-compose.minimal.yml up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

## 📊 Monitoring

### Sentry Integration

Both frontend and backend are integrated with Sentry for error tracking only:

- Automatic error capture
- User context tracking
- Custom breadcrumbs
- Production-only error reporting
- Simplified configuration (no performance monitoring)

### Health Checks

- Backend: `http://localhost:8000/health`
- Frontend: `http://localhost:3000/api/health`

Health endpoint shows status of optional components:
```json
{
  "status": "healthy",
  "database": {
    "enabled": false,
    "connected": null
  },
  "cache": {
    "enabled": false,
    "connected": null
  }
}
```

## 🛡️ Security

- Environment-based configuration
- Secret key rotation support
- CORS configuration
- Rate limiting
- Request ID tracking
- Secure headers

## 📚 API Documentation

When running in development, API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🧪 Testing

```bash
# Backend tests
cd server
pytest

# Frontend tests
cd client
npm test
```

## 🔍 Validation & Troubleshooting

### Validate Your Setup

```bash
# Run validation script
python validate-setup.py  # or python3 validate-setup.py
```

This checks:
- All dependencies installed correctly
- Environment files configured
- Database connections working
- Services can start properly

### Common Issues

#### Port Conflicts
```bash
# Check what's using ports
lsof -i :3000  # macOS/Linux
netstat -ano | findstr :3000  # Windows

# Use different ports via local overrides
# See docs/LOCAL_OVERRIDES.md
```

#### Module Not Found (Frontend)
```bash
# Reinstall dependencies
cd client
rm -rf node_modules package-lock.json
npm install
```

#### Database Connection Failed
- Ensure Docker is running
- Check `DATABASE_URL` in `server/.env`
- Verify PostgreSQL container is healthy: `docker-compose ps`

### Platform-Specific Guides
- [Windows Setup Guide](docs/WINDOWS_SETUP.md)
- [Cross-Platform Setup](docs/CROSS_PLATFORM_SETUP.md)
- [Local Development](docs/LOCAL_DEVELOPMENT.md)

## 🆘 Support

For issues and questions:
- Contact the maintainers (Wares)

---
