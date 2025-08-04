# Trading Tools Boilerplate

Production-ready boilerplate for building trading tools with FastAPI backend and Next.js frontend. Get deployed in minutes.

**Now with optional database and caching!** Perfect for lightweight tools that don't need persistence.

## 🚀 Getting Started

### 1. Use This Boilerplate

```bash
# Clone the boilerplate into your new project
git clone https://github.com/FinMC/trading-tools-boilerplate my-trading-tool
cd my-trading-tool

# Set up git remotes
git remote add boilerplate https://github.com/FinMC/trading-tools-boilerplate
git remote set-url origin https://github.com/YourOrg/my-trading-tool

# Create your repository on GitHub, then push
git push -u origin main
```

> 💡 This setup lets you pull future boilerplate updates with `git pull boilerplate main`

### 2. Configure Environment

```bash
# Backend configuration
cp server/.env.example server/.env
# Edit server/.env with your API keys

# Frontend configuration  
cp client/.env.example client/.env.local
# Edit client/.env.local to point to your backend
```

Key configurations:
- `POLYGON_API_KEY` - Required for market data(or anything else)
- `SENTRY_DSN` - Optional error tracking
- `DATABASE_URL` - Auto-configured by setup script (if database enabled)
- `ENABLE_DATABASE` - Set to `false` for tools without persistence
- `ENABLE_CACHING` - Set to `false` for tools without caching

### 3. Install & Start Development

```bash
# Run the universal setup script
python setup.py  # or python3 setup.py

# The script will ask:
# - Do you want to use database functionality? (y/n)
# - Do you want to use caching functionality? (y/n)

# This automatically:
# ✓ Installs all dependencies
# ✓ Sets up only the services you need
# ✓ Configures your environment
# ✓ Creates development scripts

# Start development
./start-dev.sh    # Unix/macOS - Full mode
start-dev.bat     # Windows - Full mode

# Or start with specific configurations
./start-dev.sh --minimal    # No database or cache
./start-dev.sh --no-database  # Cache only
./start-dev.sh --no-cache     # Database only
```

Your app is now running:
- Backend API: http://localhost:8000
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

## 🚢 Deploy to Railway

### Quick Deploy via Dashboard

1. **Create Project**
   - Go to [railway.app](https://railway.app)
   - Click "Start a New Project"
   - Select "Deploy from GitHub repo"

2. **Deploy Services**
   - **Backend**: Select repo → Set root to `/server` → Deploy
   - **Frontend**: Select repo → Set root to `/client` → Deploy
   - **Database**: New → Database → Add PostgreSQL (if needed)
   - **Redis**: New → Database → Add Redis (if needed)

3. **Configure Environment**
   - Click each service → Variables tab
   - Add required environment variables
   - Frontend needs: `NEXT_PUBLIC_API_URL` = your backend URL
   - Backend needs:
     - `ENABLE_DATABASE` = true/false
     - `ENABLE_CACHING` = true/false

4. **Connect Services** (if using database/cache)
   - Backend variables: 
     - `DATABASE_URL` = `${{Postgres.DATABASE_URL}}` (if database enabled)
     - `REDIS_URL` = `${{Redis.REDIS_URL}}` (if cache enabled)

That's it! Your app is live. 🎉

## 🎯 Optional Components

This boilerplate supports running without database and/or cache, perfect for:
- Simple API integrations
- Calculation tools
- Data transformation services
- Lightweight microservices

### Minimal Mode Examples

```bash
# Tool that only needs API calls (no database/cache)
./start-dev.sh --minimal

# Tool with caching but no database
./start-dev.sh --no-database

# Tool with database but no cache
./start-dev.sh --no-cache
```

### Docker Minimal Mode

```bash
# Use minimal docker-compose (no PostgreSQL/Redis)
docker-compose -f docker-compose.minimal.yml up
```

## 📚 Documentation

For detailed guides:

- **[Setup Guide](docs/README.md)** - Complete feature list and setup options
- **[Optional Components](docs/OPTIONAL_COMPONENTS.md)** - Using without database/cache
- **[Local Development](docs/LOCAL_DEVELOPMENT.md)** - Development workflows
- **[Railway Deployment](docs/RAILWAY_DEPLOYMENT.md)** - Advanced deployment options
- **[Environment Variables](docs/ENVIRONMENT_VARIABLES.md)** - All configuration options
- **[Backend Standards](docs/BACKEND_CODING_STANDARDS.md)** - Python/FastAPI patterns
- **[Frontend Standards](docs/FRONTEND_CODING_STANDARDS.md)** - TypeScript/Next.js patterns

## 📁 Project Structure

```
my-trading-tool/
├── server/          # FastAPI backend
├── client/          # Next.js frontend  
├── docs/            # Documentation
├── setup.py         # Universal setup script
├── start-dev.sh/bat # Development scripts
└── docker-compose.yml
```

## 🛟 Need Help?

- Check the [full documentation](docs/README.md)
- Review [troubleshooting guide](docs/README.md#troubleshooting)
- Contact the maintainers

---
