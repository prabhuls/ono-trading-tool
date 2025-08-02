# Trading Tools Boilerplate

A production-ready boilerplate for building trading and investment tools with FastAPI (Python) backend and Next.js (TypeScript) frontend.

## 🚀 Features

### Backend (FastAPI)
- **Enterprise-level architecture** with clear separation of concerns
- **Centralized logging system** with structured JSON logging
- **Standardized API responses** for consistent client handling
- **Advanced caching system** with Redis integration and decorators
- **Comprehensive error monitoring** with Sentry integration
- **External API service pattern** with retry logic and rate limiting
- **Async database support** with PostgreSQL and SQLAlchemy ORM
- **API versioning** and OpenAPI documentation
- **Health checks** and readiness probes
- **Rate limiting** and security middleware

### Frontend (Next.js)
- **TypeScript** with strict type checking
- **Tailwind CSS** for styling
- **Error boundaries** with Sentry integration
- **API client** with interceptors and error handling
- **Performance monitoring** and session replay
- **Responsive design** foundation
- **Environment-based configuration**

### DevOps & Deployment
- **Docker** containerization for all services
- **Railway-ready** deployment configurations
- **One-command setup** script
- **Environment management** with examples
- **CI/CD ready** structure

## 📋 Prerequisites

- Python 3.9+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL (included in Docker setup)
- Redis (included in Docker setup)

## 🛠️ Quick Start

### One-Command Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd tool-boilerplate

# Run the setup script
./setup.sh
```

This will:
1. Check all prerequisites
2. Create Python virtual environment
3. Install all dependencies
4. Set up environment files
5. Start Docker services
6. Create development scripts

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

## 🔧 Configuration

### Environment Variables

#### Backend (.env)
```env
# Environment
ENVIRONMENT=development
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/trading_tools

# Redis
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
│   └── Dockerfile
├── client/                 # Next.js frontend
│   ├── app/               # App router
│   ├── components/        # React components
│   ├── lib/               # Utilities
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── setup.sh               # One-command setup
└── README.md
```

## 🏗️ Architecture

### Backend Architecture

The backend follows a layered architecture:

1. **API Layer** (`app/api/`) - HTTP endpoints and request handling
2. **Service Layer** (`app/services/`) - Business logic
3. **Data Layer** (`app/models/`) - Database models
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

#### Caching
```python
from app.core.cache import cache

@cache(ttl=300, namespace="market_data")
async def get_stock_price(symbol: str):
    # This will be cached for 5 minutes
    return await fetch_price(symbol)
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
2. Add PostgreSQL database service
3. Add Redis service
4. Deploy backend:
   ```bash
   cd server
   railway up
   ```
5. Deploy frontend:
   ```bash
   cd client
   railway up
   ```

### Docker Deployment

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

## 📊 Monitoring

### Sentry Integration

Both frontend and backend are integrated with Sentry for error tracking:

- Automatic error capture
- Performance monitoring
- User context tracking
- Custom breadcrumbs
- Session replay (frontend)

### Health Checks

- Backend: `http://localhost:8000/health`
- Frontend: `http://localhost:3000/api/health`

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

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
- Check the [Issues](https://github.com/yourusername/tool-boilerplate/issues) page
- Review the documentation in the `docs/` directory
- Contact the maintainers

---

Built with ❤️ for the trading and investment community