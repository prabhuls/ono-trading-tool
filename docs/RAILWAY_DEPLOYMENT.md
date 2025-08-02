# Railway Deployment Guide

This guide provides step-by-step instructions for deploying the Trading Tools platform to Railway.

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
2. **Railway CLI** (optional but recommended):
   ```bash
   npm install -g @railway/cli
   ```
3. **GitHub Account**: For automatic deployments
4. **Docker**: For local PostgreSQL development
5. **Sentry Account**: For error monitoring (optional)

## Project Setup

### 1. Create New Railway Project

```bash
# Using CLI
railway login
railway init

# Or use the web dashboard
# Go to https://railway.app/new
```

### 2. Connect GitHub Repository

1. In Railway dashboard, click "New Project"
2. Select "Deploy from GitHub repo"
3. Connect your GitHub account
4. Select your repository

## Backend Deployment

### 1. Create Backend Service

In Railway dashboard:
1. Click "New" → "GitHub Repo"
2. Select your repository
3. Set **Root Directory** to `/server`
4. Railway will auto-detect Python/FastAPI

### 2. Configure Backend Environment Variables

Add these environment variables in the backend service settings:

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
# Using CLI from server directory
cd server
railway up

# Or push to GitHub for automatic deployment
git push origin main
```

## Frontend Deployment

### 1. Create Frontend Service

1. In Railway project, click "New" → "GitHub Repo"
2. Select repository again
3. Set **Root Directory** to `/client`
4. Railway will detect Next.js

### 2. Configure Frontend Environment Variables

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
# Using CLI from client directory
cd client
railway up

# Or push to GitHub
git push origin main
```

## Database & Redis Setup

### 1. Add PostgreSQL Service

1. In Railway project, click "New"
2. Select "Database" → "Add PostgreSQL"
3. PostgreSQL will be provisioned automatically
4. Railway provides the connection string automatically

### 2. Add Redis Service

1. In Railway project, click "New"
2. Select "Database" → "Add Redis"
3. Redis will be provisioned automatically

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

## Support Resources

- [Railway Documentation](https://docs.railway.app)
- [Railway Discord](https://discord.gg/railway)
- [Status Page](https://status.railway.app)

## Next Steps

1. Set up monitoring alerts
2. Configure automatic backups
3. Implement CI/CD pipeline
4. Set up staging environment
5. Configure CDN for static assets