# Optional Components in Trading Tools Boilerplate

This document explains how to use the Trading Tools Boilerplate with optional database and caching components, allowing you to run lighter tools that don't need persistence or caching.

## Overview

The boilerplate now supports running without PostgreSQL database and/or Redis cache. This is useful for:
- Simple tools that don't need data persistence
- API integrations that only need to fetch and transform data
- Lightweight development environments
- Testing and prototyping

## Configuration

### Environment Variables

Two new environment variables control whether database and caching are enabled:

```bash
# Enable/disable database functionality (default: true)
ENABLE_DATABASE=true|false

# Enable/disable caching functionality (default: true)  
ENABLE_CACHING=true|false
```

When disabled:
- **Database disabled**: All database-dependent endpoints return 503 Service Unavailable
- **Cache disabled**: Cache operations become no-ops (always miss, but don't error)

### Required Configuration

When components are enabled, you must provide their connection URLs:
- If `ENABLE_DATABASE=true`, you must set `DATABASE_URL`
- If `ENABLE_CACHING=true`, you must set `REDIS_URL`

## Running the Application

### 1. Minimal Mode (No Database, No Cache)

Start only the backend and frontend without any external dependencies:

```bash
# Using the start script
./start-dev.sh --minimal

# Or specify individually
./start-dev.sh --no-database --no-cache

# Using Docker
docker-compose -f docker-compose.minimal.yml up
```

### 2. Database Only (No Cache)

Run with database but without Redis caching:

```bash
./start-dev.sh --no-cache
```

### 3. Cache Only (No Database)

Run with Redis but without PostgreSQL:

```bash
./start-dev.sh --no-database
```

### 4. Full Mode (Default)

Run with all components:

```bash
./start-dev.sh
# or
docker-compose up
```

## API Endpoint Behavior

### Database-Dependent Endpoints

Endpoints that require database access are decorated with `@require_database`. When the database is disabled, these endpoints return:

```json
{
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "This feature requires database access, but the database is not enabled."
  },
  "status": 503
}
```

### Cache Behavior

When caching is disabled:
- Cache decorators (`@cache`) still work but always miss
- Manual cache operations (get/set/delete) silently succeed without doing anything
- The application continues to function normally, just without caching benefits

## Health Check Endpoint

The `/health` endpoint reports the status of optional components:

```json
{
  "status": "healthy",
  "cache": {
    "enabled": false,
    "connected": null,
    "metrics": null
  },
  "database": {
    "enabled": false,
    "connected": null
  },
  "features": {
    "database": false,
    "caching": false,
    "enable_websockets": true,
    "enable_rate_limiting": true
  }
}
```

## Docker Compose Files

### docker-compose.yml
Full stack with PostgreSQL, Redis, Backend, and Frontend.

### docker-compose.minimal.yml
Only Backend and Frontend, no external dependencies:
```yaml
services:
  backend:
    environment:
      - ENABLE_DATABASE=false
      - ENABLE_CACHING=false
  
  frontend:
    # Frontend configuration
```

## Creating Database-Optional Endpoints

### Using Optional Database Dependency

For endpoints that can work with or without a database:

```python
from app.core.dependencies import OptionalDatabase

@router.get("/data")
async def get_data(db: Optional[AsyncSession] = Depends(OptionalDatabase())):
    if db:
        # Use database
        data = await db.execute(select(Model))
        return {"source": "database", "data": data}
    else:
        # Fallback logic
        return {"source": "computed", "data": compute_data()}
```

### Requiring Database

For endpoints that absolutely need database:

```python
from app.core.dependencies import require_database, get_db

@router.get("/users")
@require_database
async def get_users(db: AsyncSession = Depends(get_db)):
    # This endpoint will return 503 if database is disabled
    users = await db.execute(select(User))
    return users
```

## Best Practices

1. **Design for Optionality**: When creating new features, consider whether they truly need database/cache
2. **Graceful Degradation**: Provide fallback behavior when optional components are disabled
3. **Clear Error Messages**: Use the provided decorators to give users clear feedback
4. **Document Dependencies**: Clearly document which features require which components

## Example Use Cases

### 1. Market Data Fetcher
A tool that only fetches and formats market data from external APIs:
```bash
ENABLE_DATABASE=false
ENABLE_CACHING=true  # Cache API responses
```

### 2. Simple Calculator
A tool that performs calculations without storing results:
```bash
ENABLE_DATABASE=false
ENABLE_CACHING=false
```

### 3. Data Aggregator
A tool that fetches data and stores aggregated results:
```bash
ENABLE_DATABASE=true
ENABLE_CACHING=true  # Cache expensive computations
```

## Troubleshooting

### "Database is not enabled" errors
- Check that `ENABLE_DATABASE=true` in your `.env` file
- Ensure `DATABASE_URL` is set correctly
- Verify PostgreSQL is running (if using Docker)

### "Cache always misses"
- Check that `ENABLE_CACHING=true` in your `.env` file
- Ensure `REDIS_URL` is set correctly
- Verify Redis is running (if using Docker)

### Health check shows degraded status
- Check the specific component status in the health response
- Ensure all enabled components have valid connection strings
- Check Docker containers are running: `docker ps`