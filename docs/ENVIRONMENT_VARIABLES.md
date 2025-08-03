# Environment Variables Guide

This project uses three separate `.env` files for different purposes. Understanding when to use each one is crucial for proper configuration.

## Overview

| File | Purpose | When Used |
|------|---------|-----------|
| `.env` (root) | Docker Compose configuration | Only when running `docker-compose up` |
| `server/.env` | Backend API configuration | Native development with `uvicorn` or `./start-dev.sh` |
| `client/.env.local` | Frontend configuration | Native development with `npm run dev` or `./start-dev.sh` |

## Root `.env` - Docker Compose Only

**Location**: `/.env`  
**Template**: `/.env.example`  
**Used by**: Docker Compose when building and running containers

This file provides environment variables that Docker Compose interpolates into the `docker-compose.yml` file. It's **NOT** used when running services natively.

### Required Variables:
```bash
# General
ENVIRONMENT=development

# Security
SECRET_KEY=your-secret-key-here

# External APIs (if used)
POLYGON_API_KEY=your-polygon-api-key

# Monitoring (optional)
SENTRY_DSN=
NEXT_PUBLIC_SENTRY_DSN=
```

## Server `.env` - Backend Configuration

**Location**: `/server/.env`  
**Template**: `/server/.env.example`  
**Used by**: FastAPI backend when running natively

This file contains all backend configuration including database connections, API keys, and feature flags.

### Key Variables:
```bash
# Environment
ENVIRONMENT=development
DEBUG=True

# Database (localhost for native development)
DATABASE_URL=postgresql://postgres:password@localhost:5432/trading_tools

# Redis (localhost for native development)
REDIS_URL=redis://localhost:6379

# External APIs
POLYGON_API_KEY=your-polygon-api-key

# Security
SECRET_KEY=your-secret-key-here
```

### Optional Variables:
- API rate limiting configuration
- Feature flags
- CORS settings
- Additional API integrations

## Client `.env.local` - Frontend Configuration

**Location**: `/client/.env.local`  
**Template**: `/client/.env.example`  
**Used by**: Next.js frontend

All frontend environment variables must be prefixed with `NEXT_PUBLIC_` to be accessible in the browser.

### Key Variables:
```bash
# Application
NEXT_PUBLIC_APP_NAME="Trading Tools"
NEXT_PUBLIC_ENVIRONMENT=development

# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Monitoring (optional)
NEXT_PUBLIC_SENTRY_DSN=

# Feature Flags
NEXT_PUBLIC_ENABLE_ANALYTICS=false
NEXT_PUBLIC_ENABLE_SENTRY=false
```

## Development Workflows

### Native Development (Recommended)
When using `./start-dev.sh` or running services manually:
- ✅ Use `server/.env` for backend configuration
- ✅ Use `client/.env.local` for frontend configuration
- ❌ Root `.env` is NOT used

### Docker Compose Development
When using `docker-compose up`:
- ✅ Use root `.env` for Docker Compose variables
- ❌ Individual service `.env` files are NOT used (configuration comes from docker-compose.yml)

### Hybrid Mode (Default with ./start-dev.sh)
Database/Redis in Docker, apps running natively:
- ✅ Use `server/.env` for backend configuration
- ✅ Use `client/.env.local` for frontend configuration
- ❌ Root `.env` is NOT used (only PostgreSQL and Redis run in Docker)

## Security Best Practices

1. **Never commit `.env` files** - They contain sensitive data
2. **Always use `.env.example` files** as templates
3. **Generate secure keys** - Use `openssl rand -hex 32` for SECRET_KEY
4. **Use environment-specific values** - Different keys for development/production
5. **Validate required variables** - The app should fail fast if critical variables are missing

## Common Issues

### "Environment variable not found"
- Check you're using the correct `.env` file for your development mode
- Ensure the variable is properly exported (some shells require `export` command)
- Restart your development server after changing `.env` files

### Docker Compose variable interpolation errors
- Ensure root `.env` exists and contains all variables referenced in `docker-compose.yml`
- Check for typos in variable names
- Use `docker-compose config` to debug interpolation

### Frontend variables not accessible
- Ensure all frontend variables start with `NEXT_PUBLIC_`
- Rebuild the Next.js app after adding new variables
- Check that variables are added to `.env.local`, not `.env`