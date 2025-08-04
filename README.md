# Trading Tools Boilerplate

Production-ready boilerplate for building trading tools with FastAPI backend and Next.js frontend. Get deployed in minutes.

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
- `DATABASE_URL` - Auto-configured by setup script

### 3. Install & Start Development

```bash
# Run the universal setup script
python setup.py  # or python3 setup.py

# This automatically:
# ✓ Installs all dependencies
# ✓ Sets up PostgreSQL & Redis via Docker
# ✓ Runs database migrations
# ✓ Creates development scripts

# Start development
./start-dev.sh    # Unix/macOS
start-dev.bat     # Windows
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
   - **Database**: New → Database → Add PostgreSQL
   - **Redis**: New → Database → Add Redis

3. **Configure Environment**
   - Click each service → Variables tab
   - Add required environment variables
   - Frontend needs: `NEXT_PUBLIC_API_URL` = your backend URL

4. **Connect Services**
   - Backend variables: 
     - `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`
     - `REDIS_URL` = `${{Redis.REDIS_URL}}`

That's it! Your app is live. 🎉

## 📚 Documentation

For detailed guides:

- **[Setup Guide](docs/README.md)** - Complete feature list and setup options
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
