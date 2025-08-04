# Railway Deployment Guide

This guide provides step-by-step instructions for deploying the Trading Tools platform to Railway.

## Deployment Methods

Railway offers two ways to deploy your applications:

1. **Railway Dashboard (Recommended)** - Visual interface for easy deployment and configuration
2. **Railway CLI** - Command-line interface for automation and scripting

This guide covers both methods. Choose the one that best fits your workflow.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Project Setup](#project-setup)
- [Backend Deployment](#backend-deployment)
- [Frontend Deployment](#frontend-deployment)
- [Database & Redis Setup](#database--redis-setup)
- [Environment Variables](#environment-variables)
- [Custom Domains](#custom-domains)
- [Monitoring & Logs](#monitoring--logs)
- [Troubleshooting](#troubleshooting)

## Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **Railway CLI** (required):
   ```bash
   # Install via npm (recommended)
   npm install -g @railway/cli
   
   # Or install via Homebrew (macOS)
   brew install railway
   
   # Or install via curl (Linux/macOS)
   curl -sSL https://railway.app/install.sh | sh
   
   # Verify installation
   railway --version
   ```
3. **GitHub Account**: For automatic deployments
4. **Docker**: For local PostgreSQL development
5. **Sentry Account**: For error monitoring (optional)

### Railway CLI Setup

After installing the Railway CLI, authenticate and link your project:

```bash
# Login to Railway
railway login

# Create a new project or link to existing
railway link

# Verify connection
railway status
```

## Project Setup

### 1. Create New Railway Project

#### Option 1: Using Railway Dashboard (Recommended)

1. Go to [railway.app/new](https://railway.app/new)
2. Click **"Start a New Project"**
3. Choose **"Deploy from GitHub repo"** to connect your repository
4. Or choose **"Empty project"** to start fresh

#### Option 2: Using Railway CLI

```bash
# Login if not already authenticated
railway login

# Initialize a new project
railway init

# Or link to an existing project
railway link
```

### 2. Connect GitHub Repository

#### Option 1: Using Railway Dashboard (Recommended)

1. In your Railway project, click **"Connect GitHub"**
2. Authorize Railway to access your GitHub account
3. Select your repository
4. Choose the branch to deploy (usually `main`)

#### Option 2: Using Railway CLI

```bash
# Connect GitHub repository via CLI
railway github

# This will open your browser to connect your GitHub account
# and select the repository to deploy
```

## Backend Deployment

### 1. Create Backend Service

#### Option 1: Using Railway Dashboard (Recommended)

1. In your Railway project dashboard, click **"New Service"**
2. Select **"Deploy from GitHub repo"**
3. Choose your repository
4. Set **Service Name** to `backend`
5. Set **Root Directory** to `/server`
6. Railway will auto-detect Python/FastAPI and configure build settings

#### Option 2: Using Railway CLI

```bash
# Navigate to server directory
cd server

# Deploy the backend service
railway up --service backend

# Or create a new service first
railway service create backend
railway up
```

### 2. Configure Backend Environment Variables

#### Using Railway Dashboard:
1. Click on your **backend** service
2. Go to **"Variables"** tab
3. Add the following environment variables:

#### Using Railway CLI:
```bash
railway variables set KEY=value --service backend
```

Required environment variables:

```bash
# Environment
ENVIRONMENT=production
DEBUG=False

# Security
SECRET_KEY=<generate-secure-key>

# Database (Railway PostgreSQL)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Redis (will be set automatically when you add Redis)
REDIS_URL=${{Redis.REDIS_URL}}

# External APIs
POLYGON_API_KEY=<your-polygon-api-key>

# Sentry
SENTRY_DSN=<your-backend-sentry-dsn>
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1

# CORS (add your frontend URL)
ALLOWED_ORIGINS=["https://your-frontend.up.railway.app"]
```

### 3. Configure Build & Start Commands

Railway should auto-detect these, but you can override in settings:

```yaml
# Build Command
pip install -r requirements.txt

# Start Command (with migrations)
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Or use a `railway.json` file in your server directory:
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "releaseCommand": "alembic upgrade head",
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
  }
}
```

### 4. Deploy Backend

```bash
# Deploy using CLI
cd server
railway up --service backend

# View deployment logs
railway logs --service backend

# Or enable automatic deployment from GitHub
railway github:deploy --service backend
```

## Frontend Deployment

### 1. Create Frontend Service

#### Option 1: Using Railway Dashboard (Recommended)

1. In your Railway project, click **"New Service"**
2. Select **"Deploy from GitHub repo"**
3. Choose your repository again
4. Set **Service Name** to `frontend`
5. Set **Root Directory** to `/client`
6. Railway will detect Next.js and configure automatically

#### Option 2: Using Railway CLI

```bash
# Navigate to client directory
cd client

# Create and deploy frontend service
railway service create frontend
railway up --service frontend
```

### 2. Configure Frontend Environment Variables

#### Using Railway Dashboard:
1. Click on your **frontend** service
2. Go to **"Variables"** tab
3. Add the following variables:

#### Using Railway CLI:
```bash
railway variables set KEY=value --service frontend
```

Required environment variables:

```bash
# Backend API URL (use your backend service URL)
NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app

# App Config
NEXT_PUBLIC_APP_NAME=Trading Tools
NEXT_PUBLIC_ENVIRONMENT=production

# Sentry
NEXT_PUBLIC_SENTRY_DSN=<your-frontend-sentry-dsn>
SENTRY_DSN=<your-frontend-sentry-dsn>
SENTRY_ORG=<your-sentry-org>
SENTRY_PROJECT=<your-sentry-project>
SENTRY_AUTH_TOKEN=<your-sentry-auth-token>
```

### 3. Configure Build & Start Commands

```yaml
# Build Command
npm ci && npm run build

# Start Command
npm start
```

### 4. Deploy Frontend

```bash
# Deploy using CLI
cd client
railway up --service frontend

# View deployment logs
railway logs --service frontend

# Check deployment status
railway status --service frontend
```

## Database & Redis Setup

### 1. Add PostgreSQL Service

#### Option 1: Using Railway Dashboard (Recommended)

1. In your Railway project, click **"New Service"**
2. Select **"Database"** → **"Add PostgreSQL"**
3. PostgreSQL will be provisioned automatically
4. Railway provides the connection string as `DATABASE_URL`

#### Option 2: Using Railway CLI

```bash
# Add PostgreSQL database
railway add --plugin postgresql

# Or create a database service
railway service create postgres --image postgres:15

# Get the database URL
railway variables get DATABASE_URL --service postgres
```

### 2. Add Redis Service

#### Option 1: Using Railway Dashboard (Recommended)

1. In your Railway project, click **"New Service"**
2. Select **"Database"** → **"Add Redis"**
3. Redis will be provisioned automatically
4. Railway provides the connection URL as `REDIS_URL`

#### Option 2: Using Railway CLI

```bash
# Add Redis service
railway add --plugin redis

# Or create a Redis service
railway service create redis --image redis:7-alpine

# Get the Redis URL
railway variables get REDIS_URL --service redis
```

### 3. Connect Services

Railway automatically provides service URLs. In your backend environment variables:
```bash
# Database connection (automatically available)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Redis connection
REDIS_URL=${{Redis.REDIS_URL}}
```

### 4. Database Migrations

Railway will automatically run migrations on deploy if configured in your `railway.json`:
```json
{
  "build": {
    "builder": "DOCKERFILE"
  },
  "deploy": {
    "releaseCommand": "alembic upgrade head"
  }
}
```

## Environment Variables

### Using Railway CLI

```bash
# List all variables
railway variables

# Set a variable
railway variables set KEY=value

# Set multiple variables from .env file
railway variables set $(cat .env.production)
```

### Reference Other Services

Railway allows referencing variables from other services:

```bash
# Reference Redis URL in backend
REDIS_URL=${{Redis.REDIS_URL}}

# Reference backend URL in frontend
NEXT_PUBLIC_API_URL=${{Backend.RAILWAY_PUBLIC_DOMAIN}}
```

## Custom Domains

### 1. Add Custom Domain

1. Go to service settings
2. Click "Settings" → "Domains"
3. Click "Add Domain"
4. Enter your custom domain

### 2. Configure DNS

Add the provided CNAME record to your DNS provider:

```
Type: CNAME
Name: subdomain (or @ for root)
Value: <provided-by-railway>.up.railway.app
```

### 3. Update CORS Settings

Update backend environment variables:
```bash
ALLOWED_ORIGINS=["https://yourdomain.com", "https://www.yourdomain.com"]
```

## Monitoring & Logs

### 1. View Logs

```bash
# Using CLI
railway logs

# Follow logs
railway logs -f

# Filter by service
railway logs --service backend
```

### 2. Metrics

In Railway dashboard:
- CPU usage
- Memory usage
- Network traffic
- Response times

### 3. Health Checks

Railway automatically monitors the health endpoints configured in `railway.json`:

```json
{
  "healthcheckPath": "/health",
  "healthcheckTimeout": 10
}
```

### 4. Sentry Integration

Errors and performance data will be sent to Sentry automatically.

## Deployment Pipeline

### 1. Automatic Deployments

Railway automatically deploys when you push to the connected branch.

### 2. Preview Environments

Railway creates preview environments for pull requests:
1. Open a PR on GitHub
2. Railway creates a preview deployment
3. Test changes before merging

### 3. Rollbacks

In Railway dashboard:
1. Go to "Deployments"
2. Find previous successful deployment
3. Click "Redeploy"

## Production Checklist

### Security
- [ ] Set strong `SECRET_KEY`
- [ ] Enable HTTPS only
- [ ] Configure CORS properly
- [ ] Set `DEBUG=False`
- [ ] Use secure database credentials

### Performance
- [ ] Enable Redis caching
- [ ] Set appropriate Sentry sample rates
- [ ] Configure proper health checks
- [ ] Set up monitoring alerts

### Database
- [ ] Run production migrations (`alembic upgrade head`)
- [ ] Railway PostgreSQL includes automatic backups
- [ ] Configure connection pooling in SQLAlchemy
- [ ] Railway PostgreSQL connections are SSL-enabled by default

## Troubleshooting

### 1. Build Failures

Check build logs:
```bash
railway logs --service backend --deployment latest
```

Common issues:
- Missing dependencies in requirements.txt
- Python version mismatch
- Missing environment variables

### 2. Runtime Errors

#### Backend 500 errors
- Check Sentry for detailed errors
- Verify database connection
- Check Redis connection
- Review environment variables

#### Frontend build errors
- Clear build cache in Railway
- Check Node version compatibility
- Verify all dependencies are in package.json

### 3. Connection Issues

#### Frontend can't reach backend
- Verify `NEXT_PUBLIC_API_URL` is correct
- Check CORS configuration
- Ensure backend is running

#### Database connection failed
- Verify `DATABASE_URL` is properly referenced as `${{Postgres.DATABASE_URL}}`
- Check PostgreSQL service is running in Railway
- Review connection logs in Railway dashboard
- Test with connection pooling disabled

### 4. Performance Issues

- Check Railway metrics
- Review Sentry performance data
- Enable more aggressive caching
- Consider upgrading Railway plan

## Cost Optimization

### 1. Sleep Settings

For development/staging:
```json
{
  "deploy": {
    "sleepApplication": true
  }
}
```

### 2. Resource Limits

Set resource limits in railway.json:
```json
{
  "deploy": {
    "maxMemoryMb": 512,
    "maxCpuCores": 0.5
  }
}
```

### 3. Optimize Images

Use multi-stage Docker builds to reduce image size.

## Advanced Configuration

### 1. Multiple Environments

Create separate Railway projects for:
- Production
- Staging
- Development

For local development, use Docker:
```bash
# Start local PostgreSQL
docker-compose up -d postgres

# Connect to local database
DATABASE_URL=postgresql://postgres:password@localhost:5432/trading_tools
```

### 2. Secrets Management

Use Railway's secure variable storage:
- Never commit secrets
- Use variable references
- Rotate keys regularly
- Use `${{Postgres.DATABASE_URL}}` for database connections

### 3. CI/CD Integration

```yaml
# .github/workflows/deploy.yml
name: Deploy to Railway

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: railway/deploy-action@v1
        with:
          token: ${{ secrets.RAILWAY_TOKEN }}
```

### 4. Database Management

#### Production Migrations
```bash
# Run migrations via Railway CLI
railway run alembic upgrade head

# Or configure automatic migrations in railway.json
```

#### Database Backups
Railway PostgreSQL includes automatic daily backups. For manual backups:
```bash
# Export database
railway run pg_dump $DATABASE_URL > backup.sql

# Import database
railway run psql $DATABASE_URL < backup.sql
```

## Railway CLI Command Reference

### Authentication & Project Management
```bash
# Login to Railway
railway login

# Logout
railway logout

# Create new project
railway init [project-name]

# Link to existing project
railway link [project-id]

# Unlink project
railway unlink

# Show current project info
railway status
```

### Service Management
```bash
# List all services
railway service list

# Create new service
railway service create [service-name]

# Delete service
railway service delete [service-name]

# Switch between services
railway service [service-name]
```

### Deployment Commands
```bash
# Deploy current directory
railway up

# Deploy specific service
railway up --service [service-name]

# Deploy with environment
railway up --environment [env-name]

# View deployment logs
railway logs
railway logs --service [service-name]
railway logs -f  # Follow logs

# Rollback deployment
railway down
```

### Environment Variables
```bash
# List all variables
railway variables

# Set variable
railway variables set KEY=value

# Set multiple variables
railway variables set KEY1=value1 KEY2=value2

# Get specific variable
railway variables get KEY

# Delete variable
railway variables delete KEY

# Import from .env file
railway variables set $(cat .env.production)
```

### Database Operations
```bash
# Connect to database
railway connect [service-name]

# Run database command
railway run --service postgres psql

# Execute migration
railway run --service backend alembic upgrade head
```

### Monitoring & Debugging
```bash
# View logs
railway logs
railway logs -f  # Follow mode
railway logs -n 100  # Last 100 lines

# Open project in browser
railway open

# Get project/service URLs
railway domain

# SSH into service
railway shell
```

### Plugin Management
```bash
# List available plugins
railway plugins

# Add plugin
railway add --plugin [plugin-name]

# Remove plugin
railway remove --plugin [plugin-name]
```

## Support Resources

- [Railway Documentation](https://docs.railway.app)
- [Railway CLI Documentation](https://docs.railway.app/develop/cli)
- [Railway Discord](https://discord.gg/railway)
- [Status Page](https://status.railway.app)

## Next Steps

1. Set up monitoring alerts
2. Configure automatic backups
3. Implement CI/CD pipeline
4. Set up staging environment
5. Configure CDN for static assets