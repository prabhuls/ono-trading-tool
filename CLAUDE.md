# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Trading Tools Boilerplate project with:
- **Backend**: FastAPI (Python) with async PostgreSQL, Redis caching, and structured logging
- **Frontend**: Next.js 15 (TypeScript) with Tailwind CSS and simplified Sentry error monitoring
- **Infrastructure**: Docker Compose for local development, Railway-ready for deployment
- **Cross-platform**: Universal setup script (setup.py) supports Windows, macOS, and Linux

Detailed project requirements can be found at `/docs/PROJECT_REQUIREMENTS.md`

## Quick Start

```bash
# One-command setup (recommended)
./setup.sh

# Individual service startup
cd server && source venv/bin/activate && uvicorn app.main:app --reload  # Backend
cd client && npm run dev                                                # Frontend

# Full development environment
./start-dev.sh  # Starts all services
./stop-dev.sh   # Stops all services
```

## Architecture Overview

The project follows a **layered architecture** with clear separation of concerns:

### Backend (FastAPI)
- **API Layer**: Thin endpoints with request/response validation
- **Service Layer**: Business logic and external API integrations
- **Data Layer**: Async SQLAlchemy models with proper indexing
- **Core Utilities**: Logging, caching, configuration, and monitoring

### Frontend (Next.js)
- **App Router**: Next.js 15 with TypeScript strict mode
- **Component Architecture**: Reusable components with proper typing
- **State Management**: React hooks and context for state
- **API Integration**: Axios client with interceptors
- **Production Build**: Standalone output mode for optimized Docker deployment
- **Error Monitoring**: Simplified Sentry integration (error tracking only, no performance monitoring)

## Available Subagents

Claude Code has specialized subagents for different aspects of development:

### Backend Development
- **`backend-engineer`**: Implement backend features, APIs, database schemas, and business logic
- **`backend-code-reviewer`**: Review backend code against project standards

### Frontend Development
- **`frontend-nextjs-engineer`**: Implement frontend features with Next.js and TypeScript
- **`frontend-standards-reviewer`**: Review frontend code against project standards

### DevOps & Deployment
- **`railway-devops-engineer`**: Handle Railway deployments using the Railway CLI, manage infrastructure, and Docker configuration

Use these agents proactively when working on specific areas of the codebase.

## Environment Configuration

The project uses environment-based configuration:

- **Backend**: `server/.env` (see `server/.env.example`)
- **Frontend**: `client/.env.local` (see `client/.env.example`)
- **Docker**: `docker-compose.yml` for local services

Key environment variables:
- Database connections (PostgreSQL, Redis)
- API keys for external services
- Authentication secrets
- Monitoring services (Sentry)

## Documentation Structure

Detailed technical documentation is organized by topic:

- `/docs/BACKEND_CODING_STANDARDS.md`: Python/FastAPI coding standards
- `/docs/FRONTEND_CODING_STANDARDS.md`: TypeScript/Next.js coding standards
- `/docs/RAILWAY_DEPLOYMENT.md`: Deployment procedures and configuration
- `/docs/DATABASE_SETUP.md`: Database schema and migration guide
- `/docs/LOCAL_DEVELOPMENT.md`: Local development setup details

## General Development Principles

1. **Code Quality**: Follow the coding standards documents for your area
2. **Type Safety**: Use TypeScript/Python type hints throughout
3. **Testing**: Write tests for critical business logic
4. **Documentation**: Document complex logic and architectural decisions
5. **Security**: Never commit secrets, always validate inputs
6. **Performance**: Consider caching and query optimization
7. **Monitoring**: Use structured logging and error tracking

## Project Structure

```
trading-tools/
├── server/                 # FastAPI backend
│   ├── app/               # Application code
│   │   ├── api/          # API endpoints
│   │   ├── core/         # Core utilities
│   │   ├── models/       # Database models
│   │   └── services/     # Business logic
│   ├── alembic/          # Database migrations
│   └── tests/            # Backend tests
├── client/                # Next.js frontend
│   ├── app/              # App router pages
│   ├── components/       # React components
│   ├── lib/              # Utilities and API client
│   └── public/           # Static assets
├── docs/                  # Documentation
└── docker-compose.yml     # Local development services
```

## Working with This Codebase

1. **Always check existing patterns** before implementing new features
2. **Use the appropriate subagent** for specialized tasks
3. **Follow the coding standards** for your area of work
4. **Test your changes** before marking tasks complete
5. **Update documentation** when adding new features
6. **Use meaningful commit messages** that reference the feature/fix

For specific technical details and commands, refer to the documentation files or use the appropriate subagent.