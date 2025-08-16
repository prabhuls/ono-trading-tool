# Railway Deployment Guide for CashFlowAgent VIP

This guide will walk you through deploying the CashFlowAgent VIP application to Railway.

## Prerequisites

1. Railway account (https://railway.app)
2. Railway CLI installed (optional but recommended)
3. GitHub repository with this code
4. PostgreSQL database (Railway provides this)
5. Redis instance (Railway provides this)

## Deployment Steps

### 1. Create New Railway Project

1. Login to Railway Dashboard
2. Click "New Project"
3. Choose "Deploy from GitHub repo"
4. Select your repository
5. Railway will detect the monorepo structure

### 2. Configure Services

Railway should automatically detect two services from our configuration:
- **Backend** (FastAPI Python service)
- **Frontend** (Next.js service)

### 3. Add Database Services

#### PostgreSQL Database
1. Click "New" → "Database" → "Add PostgreSQL"
2. Railway will automatically inject `DATABASE_URL` into your backend

#### Redis Cache
1. Click "New" → "Database" → "Add Redis"
2. Railway will automatically inject `REDIS_URL` into your backend

### 4. Configure Environment Variables

#### Backend Environment Variables

Go to Backend service → Variables → RAW Editor and add:

```bash
# Core Configuration
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=<generate-with-openssl-rand-hex-32>
ENABLE_AUTH=true
ENABLE_DATABASE=true
ENABLE_CACHING=true

# Frontend URL (update after frontend deploys)
FRONTEND_URL=https://<your-frontend>.railway.app
ALLOWED_ORIGINS=["https://<your-frontend>.railway.app"]

# TheTradeList API
TRADELIST_API_KEY=5b4960fc-2cd5-4bda-bae1-e84c1db1f3f5
TRADELIST_OPTIONS_API_KEY=5b4960fc-2cd5-4bda-bae1-e84c1db1f3f5
TRADELIST_BASE_URL=https://api.thetradelist.com/v1

# OCT Authentication
OCT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEApdGxoIW4z1yXVMp7Lr5G
RJHs8U7fRmu9M/JJMReo5hAVqGvJm5BxmM7I6LpUc7nOTkYcxyhQRczx8ISHuXwo
HBTjPHMuNaOy4bQVLoWYjPqVL6tOEDKRUelLirKEqMJkOaEt/V3zI3EvQcBA2vNi
OG0ZE3C+aaXKCMj8tnCMVxUvpGj9cZQWWjUesZJgfvzGOPavJveLtev3ms48C+ja
bhqYvJLWLn9JRvPU7TqMHQfwKfCJ8XlCfEJLIprC7xMcWPALBgk4ImSQXnp0K4yQ
u2RI3KV0gGZ2wXPQvPBx5VzL5roVH6dsJ4lV3pYGmDdFsWv8sYx9sOThVXQAy5yj
bQIDAQAB
-----END PUBLIC KEY-----"

# API Configuration
API_RATE_LIMIT_REQUESTS=100
API_RATE_LIMIT_PERIOD=60
LOG_LEVEL=INFO
```

#### Frontend Environment Variables

Go to Frontend service → Variables → RAW Editor and add:

```bash
# API Configuration (update with your backend URL)
NEXT_PUBLIC_API_URL=https://<your-backend>.railway.app
NEXT_PUBLIC_ENV=production
NEXT_PUBLIC_AUTH_ENABLED=true
NODE_ENV=production
STANDALONE=true
```

### 5. Run Database Migrations

After backend deploys, run migrations:

#### Using Railway CLI:
```bash
railway run --service=backend python -m alembic upgrade head
```

#### Or using Railway Dashboard:
1. Go to Backend service
2. Click "Settings" → "Deploy" → "Run Command"
3. Enter: `python -m alembic upgrade head`
4. Click "Run"

### 6. Set Up CRON Jobs

Railway will automatically detect and schedule CRON jobs from `railway.cron.toml`:

- **Earnings Checker**: Daily at 2 AM UTC
- **Credit Spreads Scanner**: Every 4 hours
- **Market Scanner**: Every 30 minutes during market hours

To verify CRON jobs:
1. Go to your project settings
2. Click on "Crons" tab
3. Verify all scheduled jobs are listed

### 7. Configure Custom Domains (Optional)

#### Backend Domain:
1. Go to Backend service → Settings → Networking
2. Add custom domain: `api.yourdomain.com`
3. Configure DNS CNAME to Railway's provided URL

#### Frontend Domain:
1. Go to Frontend service → Settings → Networking
2. Add custom domain: `app.yourdomain.com`
3. Configure DNS CNAME to Railway's provided URL

### 8. Verify Deployment

#### Check Backend:
```bash
curl https://<your-backend>.railway.app/health
```

Expected response:
```json
{"status": "healthy", "timestamp": "..."}
```

#### Check Frontend:
Navigate to `https://<your-frontend>.railway.app`

#### Check Authentication:
Visit the app with JWT token:
```
https://<your-frontend>.railway.app/?token=<JWT_TOKEN>
```

## Monitoring & Logs

### View Logs:
- Click on any service → "Logs" tab
- Filter by time range or search keywords

### Monitor Resources:
- Click on any service → "Metrics" tab
- View CPU, Memory, and Network usage

### Set Up Alerts (Optional):
1. Go to Project Settings → Integrations
2. Add Slack/Discord webhook for deployment notifications

## Troubleshooting

### Common Issues:

#### 1. Database Connection Error
- Verify `DATABASE_URL` is set in backend environment
- Check PostgreSQL service is running
- Run migrations: `alembic upgrade head`

#### 2. Redis Connection Error
- Verify `REDIS_URL` is set in backend environment
- Check Redis service is running

#### 3. CORS Errors
- Update `FRONTEND_URL` in backend environment
- Update `ALLOWED_ORIGINS` to include frontend URL

#### 4. Authentication Issues
- Verify `OCT_PUBLIC_KEY` is correctly set
- Check JWT token format and expiration

#### 5. CRON Jobs Not Running
- Check railway.cron.toml syntax
- Verify Python path in CRON commands
- Check logs for CRON execution errors

### Debug Commands:

```bash
# Check backend environment
railway run --service=backend python -c "import os; print(os.environ)"

# Test database connection
railway run --service=backend python -c "from app.core.database import engine; print('DB Connected')"

# Run earnings checker manually
railway run --service=backend python run_commands/run_earnings_check.py

# Check installed packages
railway run --service=backend pip list
```

## Production Checklist

- [ ] Environment variables configured for both services
- [ ] Database migrations completed
- [ ] Redis connected and working
- [ ] CORS configured correctly
- [ ] Authentication working with OCT tokens
- [ ] CRON jobs scheduled and running
- [ ] Health checks passing
- [ ] Logs being collected properly
- [ ] Custom domains configured (if applicable)
- [ ] SSL certificates active
- [ ] Rate limiting enabled
- [ ] Error monitoring configured (Sentry optional)

## Scaling

To scale your services:

1. Go to Service → Settings → Deploy
2. Adjust "Replicas" count
3. Configure autoscaling rules (if available)

## Backup & Recovery

### Database Backups:
1. Go to PostgreSQL service
2. Click "Backups" tab
3. Configure automatic backups

### Manual Backup:
```bash
railway run --service=backend pg_dump $DATABASE_URL > backup.sql
```

## Support

- Railway Documentation: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- Project Issues: GitHub Issues

## Important Notes

1. **API Keys**: Never commit API keys to Git. Always use environment variables.
2. **Secrets**: Generate new SECRET_KEY for production.
3. **Monitoring**: Consider adding Sentry for error tracking.
4. **Rate Limiting**: Adjust based on your usage patterns.
5. **CRON Timing**: All times are in UTC.

## Cost Optimization

- Use sleep mode for staging environments
- Monitor resource usage and adjust replica count
- Use caching effectively to reduce database queries
- Optimize Docker images for smaller size

---

**Last Updated**: December 2024
**Version**: 1.0.0