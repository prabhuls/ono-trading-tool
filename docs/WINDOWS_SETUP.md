# Windows Setup Guide

This guide provides detailed instructions for setting up the Trading Tools Boilerplate on Windows systems.

## Prerequisites

Before starting, ensure you have the following installed:

1. **Python 3.9+**
   - Download from [python.org](https://www.python.org/downloads/)
   - During installation, check "Add Python to PATH"
   - Verify: `python --version`

2. **Node.js 18+**
   - Download from [nodejs.org](https://nodejs.org/)
   - Choose the LTS version
   - Verify: `node --version` and `npm --version`

3. **Git for Windows**
   - Download from [git-scm.com](https://git-scm.com/download/win)
   - Includes Git Bash for Unix-style commands

4. **PostgreSQL** (Choose one option):
   - **Option A: Docker Desktop** (Recommended)
     - Download from [docker.com](https://www.docker.com/products/docker-desktop/)
     - Requires WSL2 on Windows 10/11
   - **Option B: Native PostgreSQL**
     - Download from [postgresql.org](https://www.postgresql.org/download/windows/)
     - Remember the password you set during installation

## Quick Setup

### Using Command Prompt or PowerShell

1. **Clone the repository**
   ```cmd
   git clone <repository-url>
   cd trading-tools
   ```

2. **Run the setup script**
   
   Using Command Prompt:
   ```cmd
   setup.bat
   ```
   
   Using PowerShell:
   ```powershell
   # If you get an execution policy error, run this first:
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   
   # Then run the setup
   .\setup.ps1
   ```

3. **Follow the prompts**
   - The script will check all prerequisites
   - Choose your database setup method
   - Environment files will be created automatically

## Manual Setup (if scripts fail)

### 1. Python Environment

```cmd
# Navigate to server directory
cd server

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Command Prompt:
venv\Scripts\activate.bat
# PowerShell:
venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### 2. Node.js Environment

```cmd
# Navigate to client directory
cd ..\client

# Install dependencies
npm install
```

### 3. Environment Configuration

Copy the example environment files:

```cmd
# From root directory
copy .env.example .env
copy server\.env.example server\.env
copy client\.env.example client\.env.local
```

Edit these files with your configuration:
- `server\.env` - Backend configuration
- `client\.env.local` - Frontend configuration

### 4. Database Setup

#### Using Docker:
```cmd
# From root directory
docker-compose up -d postgres redis
```

#### Using Native PostgreSQL:
1. Create a database named `trading_tools`
2. Update `DATABASE_URL` in `server\.env`:
   ```
   DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/trading_tools
   ```

### 5. Run Database Migrations

```cmd
# Activate Python environment
cd server
venv\Scripts\activate

# Run migrations
alembic upgrade head
```

## Starting Development Servers

### Using Scripts

```cmd
# From root directory
start-dev.bat
```

This will open two new windows:
- Backend server at http://localhost:8000
- Frontend server at http://localhost:3000

To stop the servers:
```cmd
stop-dev.bat
```

### Manual Start

Backend:
```cmd
cd server
venv\Scripts\activate
uvicorn app.main:app --reload
```

Frontend (in a new terminal):
```cmd
cd client
npm run dev
```

## Common Issues and Solutions

### PowerShell Execution Policy

If you get an error about execution policy:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Python Not Found

If `python` command is not recognized:
1. Use `py` instead of `python`
2. Or add Python to PATH:
   - Open System Properties → Environment Variables
   - Add Python installation directory to PATH

### Virtual Environment Activation Fails

If you can't activate the virtual environment:
1. Make sure you're in the correct directory
2. Try using the full path: `C:\path\to\project\server\venv\Scripts\activate`

### Docker Desktop Issues

If Docker commands fail:
1. Ensure Docker Desktop is running
2. Check that WSL2 is properly installed
3. Try restarting Docker Desktop

### Port Already in Use

If you get port conflict errors:
1. Check if services are already running: `netstat -ano | findstr :8000`
2. Kill the process using the port or change the port in configuration

## Validation

After setup, validate your environment:

```cmd
python validate-setup.py
```

This will check:
- All dependencies are installed
- Environment files are configured
- Database connection works
- Services can start properly

## Using Docker for Everything

If you prefer a fully containerized setup:

```cmd
# Start all services
docker-compose up

# Start with development optimizations
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## IDE Setup

### Visual Studio Code
1. Install Python extension
2. Install ESLint extension
3. Select Python interpreter: `server\venv\Scripts\python.exe`

### PyCharm
1. Configure Project Interpreter to use `server\venv`
2. Mark `server` as Sources Root
3. Enable Django/FastAPI support

## Next Steps

1. Review the main [README.md](../README.md)
2. Check [LOCAL_DEVELOPMENT.md](./LOCAL_DEVELOPMENT.md) for development workflow
3. Read coding standards:
   - [BACKEND_CODING_STANDARDS.md](./BACKEND_CODING_STANDARDS.md)
   - [FRONTEND_CODING_STANDARDS.md](./FRONTEND_CODING_STANDARDS.md)

## Getting Help

If you encounter issues:
1. Check the error messages carefully
2. Run `validate-setup.py` to diagnose problems
3. Consult the troubleshooting section above
4. Check project issues/discussions