# Cross-Platform Setup Guide

This guide explains how the Trading Tools Boilerplate achieves cross-platform compatibility and provides setup instructions for all supported platforms.

## Supported Platforms

- **Windows** (10/11)
  - Native development
  - WSL2 (Windows Subsystem for Linux)
  - Docker Desktop
- **macOS** (Intel and Apple Silicon)
  - Native development
  - Docker Desktop
- **Linux** (Ubuntu, Debian, Fedora, etc.)
  - Native development
  - Docker

## Universal Setup Script

We provide a Python-based setup script that works across all platforms:

```bash
# Unix/Linux/macOS
python3 setup.py  # or ./setup.sh
# Note: May need 'sudo' for Docker operations

# Windows
python setup.py  # Run as Administrator if using Docker
```

This script automatically:
- Detects your operating system
- Checks prerequisites
- Sets up Python virtual environment
- Installs Node.js dependencies
- Configures environment files
- Provides platform-specific instructions

## Platform-Specific Setup Methods

### Windows

Three setup options available:

1. **Batch Script** (Command Prompt)
   ```cmd
   setup.bat
   ```

2. **PowerShell Script**
   ```powershell
   .\setup.ps1
   ```

3. **Python Script** (Universal)
   ```cmd
   python setup.py
   ```

See [WINDOWS_SETUP.md](./WINDOWS_SETUP.md) for detailed Windows instructions.

### macOS

```bash
# Make scripts executable (first time only)
chmod +x setup.sh setup.py

# Run setup
./setup.sh
# or
python3 setup.py
```

### Linux

```bash
# Make scripts executable (first time only)
chmod +x setup.sh setup.py

# Run setup
./setup.sh
# or
python3 setup.py
```

## Key Compatibility Features

### 1. Cross-Platform Scripts

| Purpose | Windows | Unix/macOS/Linux |
|---------|---------|------------------|
| Setup | `setup.bat`, `setup.ps1` | `setup.sh` |
| Start Dev | `start-dev.bat` | `start-dev.sh` |
| Stop Dev | `stop-dev.bat` | `stop-dev.sh` |
| Universal | `setup.py` | `setup.py` |

### 2. Path Handling

The Python setup script handles path differences automatically:

```python
# Windows
venv_path = server_dir / 'venv'
activate_path = venv_path / 'Scripts' / 'activate'

# Unix/macOS/Linux
venv_path = server_dir / 'venv'
activate_path = venv_path / 'bin' / 'activate'
```

### 3. Environment Activation

Platform-specific activation commands:

**Windows (Command Prompt):**
```cmd
server\venv\Scripts\activate.bat
```

**Windows (PowerShell):**
```powershell
server\venv\Scripts\Activate.ps1
```

**Unix/macOS/Linux:**
```bash
source server/venv/bin/activate
```

### 4. Process Management

**Windows:**
- Uses `start` command to launch new windows
- `taskkill` for stopping processes

**Unix/macOS/Linux:**
- Uses `&` for background processes
- `pkill` or `kill` for stopping processes

## Docker Support

Docker provides the most consistent cross-platform experience:

### Multi-Architecture Support

Our Dockerfiles support multiple architectures:
```dockerfile
FROM --platform=$TARGETPLATFORM python:3.11-slim
```

This enables:
- x86_64 (Intel/AMD)
- arm64 (Apple Silicon, AWS Graviton)
- armv7 (Raspberry Pi)

### Development with Docker

```bash
# Standard setup
docker-compose up

# Development mode with hot-reloading
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## Database Options

### 1. PostgreSQL via Docker (Recommended)
Works identically across all platforms:
```bash
docker-compose up -d postgres
```

### 2. Native PostgreSQL
Platform-specific installation:
- **Windows**: PostgreSQL installer or `choco install postgresql`
- **macOS**: `brew install postgresql@15`
- **Linux**: `apt-get install postgresql` or `yum install postgresql`

## Validation Script

Run the validation script to check your setup:

```bash
# All platforms
python validate-setup.py
```

This checks:
- Python version and packages
- Node.js version and packages
- Docker availability
- Database connection
- Service health
- Configuration files

## Common Cross-Platform Issues

### Line Endings

Git may change line endings between platforms. Configure:
```bash
git config --global core.autocrlf input  # macOS/Linux
git config --global core.autocrlf true   # Windows
```

### File Permissions

Windows doesn't have Unix-style permissions:
- Scripts may not be executable by default
- Use appropriate script extension (.bat, .ps1, .sh)

### Path Separators

- Windows uses backslash: `server\venv\Scripts`
- Unix uses forward slash: `server/venv/bin`
- Our Python scripts handle this automatically

### Shell Differences

- Windows: Command Prompt, PowerShell
- Unix: Bash, Zsh, Fish
- Use Python scripts for maximum compatibility

## Environment Variables

### Loading .env Files

**Cross-platform Python approach:**
```python
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path('.env'))
```

**Platform-specific in shells:**
```bash
# Unix/macOS/Linux
export $(grep -v '^#' .env | xargs)

# Windows (PowerShell)
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^#].+?)=(.+)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2])
    }
}
```

## IDE Configuration

### Visual Studio Code
Works identically across platforms with these extensions:
- Python
- ESLint
- Prettier
- Docker

### Platform-Specific IDEs
- **Windows**: Visual Studio, PyCharm
- **macOS**: Xcode (for iOS preview), PyCharm
- **Linux**: PyCharm, Vim/Neovim with plugins

## Troubleshooting

### Script Execution Issues

**Windows PowerShell:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Unix/macOS/Linux:**
```bash
chmod +x script-name.sh
```

### Python Command Variations

- **Windows**: `python` or `py`
- **macOS/Linux**: `python3` (usually)
- Check with: `python --version` or `python3 --version`

### Port Conflicts

Check port usage:
```bash
# Windows
netstat -ano | findstr :8000

# macOS/Linux
lsof -i :8000
```

## Best Practices

1. **Use the Python setup script** for maximum compatibility
2. **Prefer Docker** for consistent environments
3. **Test on multiple platforms** if targeting cross-platform deployment
4. **Document platform-specific quirks** in your code
5. **Use pathlib** for file path handling in Python
6. **Avoid shell-specific features** in scripts

## Getting Help

1. Run `python validate-setup.py` to diagnose issues
2. Check platform-specific guides:
   - [WINDOWS_SETUP.md](./WINDOWS_SETUP.md)
   - Platform sections in [LOCAL_DEVELOPMENT.md](./LOCAL_DEVELOPMENT.md)
3. Use Docker for a consistent experience across platforms
