#!/usr/bin/env python3
"""
Setup validation script for Trading Tools Boilerplate
Checks that all components are properly configured and running
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import urllib.request
import urllib.error
import time

# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_colored(message: str, color: str = Colors.END):
    """Print colored message"""
    print(f"{color}{message}{Colors.END}")

def print_section(title: str):
    """Print section header"""
    print_colored(f"\n{title}", Colors.BLUE + Colors.BOLD)
    print_colored("=" * len(title), Colors.BLUE)

def check_file_exists(path: Path, description: str) -> bool:
    """Check if a file exists"""
    if path.exists():
        print_colored(f"✓ {description} found: {path}", Colors.GREEN)
        return True
    else:
        print_colored(f"✗ {description} not found: {path}", Colors.RED)
        return False

def check_env_var(var_name: str, required: bool = True) -> Tuple[bool, Optional[str]]:
    """Check if environment variable is set"""
    value = os.environ.get(var_name)
    if value:
        # Don't print sensitive values
        if any(sensitive in var_name.lower() for sensitive in ['key', 'secret', 'password', 'token']):
            print_colored(f"✓ {var_name} is set", Colors.GREEN)
        else:
            print_colored(f"✓ {var_name} = {value}", Colors.GREEN)
        return True, value
    elif required:
        print_colored(f"✗ {var_name} is not set", Colors.RED)
        return False, None
    else:
        print_colored(f"⚠ {var_name} is not set (optional)", Colors.YELLOW)
        return True, None

def load_env_file(env_path: Path) -> Dict[str, str]:
    """Load environment variables from .env file"""
    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"\'')
    return env_vars

def check_python_setup() -> bool:
    """Validate Python environment setup"""
    print_section("Python Environment")
    
    all_good = True
    
    # Check Python version
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        print_colored(f"✓ Python {version.major}.{version.minor}.{version.micro}", Colors.GREEN)
    else:
        print_colored(f"✗ Python 3.9+ required, found {version.major}.{version.minor}", Colors.RED)
        all_good = False
    
    # Check virtual environment
    venv_path = Path('server/venv')
    if venv_path.exists():
        print_colored(f"✓ Virtual environment exists: {venv_path}", Colors.GREEN)
        
        # Check if we're in the virtual environment
        if hasattr(sys, 'prefix') and str(venv_path.absolute()) in sys.prefix:
            print_colored("✓ Virtual environment is activated", Colors.GREEN)
        else:
            print_colored("⚠ Virtual environment exists but not activated", Colors.YELLOW)
    else:
        print_colored("✗ Virtual environment not found", Colors.RED)
        all_good = False
    
    # Check key Python packages
    packages = ['fastapi', 'uvicorn', 'sqlalchemy', 'alembic', 'redis', 'httpx']
    
    # If virtual environment exists, check packages using its pip
    if venv_path.exists():
        if os.name == 'nt':  # Windows
            pip_path = venv_path / 'Scripts' / 'pip.exe'
        else:  # Unix/MacOS
            pip_path = venv_path / 'bin' / 'pip'
        
        if pip_path.exists():
            try:
                # Use pip list to check installed packages
                result = subprocess.run([str(pip_path), 'list', '--format=json'], 
                                      capture_output=True, text=True, check=True)
                installed_packages = {pkg['name'].lower() for pkg in json.loads(result.stdout)}
                
                for package in packages:
                    if package.lower() in installed_packages:
                        print_colored(f"✓ {package} installed", Colors.GREEN)
                    else:
                        print_colored(f"✗ {package} not installed", Colors.RED)
                        all_good = False
            except Exception as e:
                print_colored(f"⚠ Could not check packages via pip: {e}", Colors.YELLOW)
                # Fallback to import method
                try:
                    import importlib
                    for package in packages:
                        try:
                            importlib.import_module(package)
                            print_colored(f"✓ {package} installed", Colors.GREEN)
                        except ImportError:
                            print_colored(f"✗ {package} not installed", Colors.RED)
                            all_good = False
                except Exception as e2:
                    print_colored(f"⚠ Could not check packages: {e2}", Colors.YELLOW)
        else:
            print_colored("⚠ pip not found in virtual environment", Colors.YELLOW)
    else:
        # No venv, try system imports
        try:
            import importlib
            for package in packages:
                try:
                    importlib.import_module(package)
                    print_colored(f"✓ {package} installed", Colors.GREEN)
                except ImportError:
                    print_colored(f"✗ {package} not installed", Colors.RED)
                    all_good = False
        except Exception as e:
            print_colored(f"⚠ Could not check packages: {e}", Colors.YELLOW)
    
    return all_good

def check_node_setup() -> bool:
    """Validate Node.js environment setup"""
    print_section("Node.js Environment")
    
    all_good = True
    
    # Check Node version
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print_colored(f"✓ Node.js {version}", Colors.GREEN)
        else:
            print_colored("✗ Node.js not found", Colors.RED)
            all_good = False
    except FileNotFoundError:
        print_colored("✗ Node.js not found", Colors.RED)
        all_good = False
    
    # Check npm
    try:
        result = subprocess.run(['npm', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print_colored(f"✓ npm {version}", Colors.GREEN)
    except FileNotFoundError:
        print_colored("✗ npm not found", Colors.RED)
        all_good = False
    
    # Check node_modules
    node_modules = Path('client/node_modules')
    if node_modules.exists():
        print_colored("✓ Node modules installed", Colors.GREEN)
    else:
        print_colored("✗ Node modules not installed (run npm install in client/)", Colors.RED)
        all_good = False
    
    # Check package.json
    package_json = Path('client/package.json')
    if package_json.exists():
        with open(package_json, 'r') as f:
            data = json.load(f)
            if 'engines' in data:
                print_colored(f"✓ Node.js version locked: {data['engines'].get('node', 'not specified')}", Colors.GREEN)
            else:
                print_colored("⚠ No Node.js version specified in package.json", Colors.YELLOW)
    
    return all_good

def check_docker_setup() -> bool:
    """Validate Docker setup"""
    print_section("Docker Environment")
    
    # Check Docker
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print_colored(f"✓ Docker {version}", Colors.GREEN)
            
            # Check if Docker daemon is running
            result = subprocess.run(['docker', 'info'], capture_output=True, text=True)
            if result.returncode == 0:
                print_colored("✓ Docker daemon is running", Colors.GREEN)
                return True
            else:
                print_colored("✗ Docker daemon is not running", Colors.RED)
                return False
        else:
            print_colored("✗ Docker not found", Colors.RED)
            return False
    except FileNotFoundError:
        print_colored("✗ Docker not found", Colors.RED)
        return False

def check_database_connection() -> bool:
    """Check database connectivity"""
    print_section("Database Connection")
    
    # Load environment variables
    server_env = load_env_file(Path('server/.env'))
    database_url = server_env.get('DATABASE_URL', '')
    
    if not database_url:
        print_colored("✗ DATABASE_URL not set in server/.env", Colors.RED)
        return False
    
    # Parse database URL (basic check)
    if database_url.startswith('postgresql://'):
        print_colored("✓ PostgreSQL database URL configured", Colors.GREEN)
        
        # Try to connect using psycopg2 if available
        try:
            import psycopg2
            from urllib.parse import urlparse
            
            parsed = urlparse(database_url)
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip('/')
            )
            conn.close()
            print_colored("✓ Successfully connected to PostgreSQL", Colors.GREEN)
            return True
        except ImportError:
            print_colored("⚠ psycopg2 not installed, cannot test connection", Colors.YELLOW)
            return True  # Assume it's OK if we can't test
        except Exception as e:
            print_colored(f"✗ Failed to connect to PostgreSQL: {e}", Colors.RED)
            return False
    else:
        print_colored("✗ Invalid DATABASE_URL format", Colors.RED)
        return False

def check_services_health() -> bool:
    """Check if services are running and healthy"""
    print_section("Service Health Checks")
    
    all_healthy = True
    
    # Check backend health
    try:
        response = urllib.request.urlopen('http://localhost:8000/health', timeout=5)
        if response.status == 200:
            print_colored("✓ Backend API is healthy (http://localhost:8000)", Colors.GREEN)
        else:
            print_colored(f"⚠ Backend API returned status {response.status}", Colors.YELLOW)
            all_healthy = False
    except urllib.error.URLError as e:
        print_colored("✗ Backend API is not responding (http://localhost:8000)", Colors.RED)
        print_colored(f"  Error: {e}", Colors.RED)
        all_healthy = False
    except Exception as e:
        print_colored(f"✗ Backend health check failed: {e}", Colors.RED)
        all_healthy = False
    
    # Check frontend health
    try:
        response = urllib.request.urlopen('http://localhost:3000', timeout=5)
        if response.status == 200:
            print_colored("✓ Frontend is running (http://localhost:3000)", Colors.GREEN)
        else:
            print_colored(f"⚠ Frontend returned status {response.status}", Colors.YELLOW)
            all_healthy = False
    except urllib.error.URLError:
        print_colored("✗ Frontend is not responding (http://localhost:3000)", Colors.RED)
        all_healthy = False
    except Exception as e:
        print_colored(f"✗ Frontend health check failed: {e}", Colors.RED)
        all_healthy = False
    
    # Check Redis if configured
    server_env = load_env_file(Path('server/.env'))
    redis_url = server_env.get('REDIS_URL', '')
    if redis_url:
        try:
            import redis
            r = redis.from_url(redis_url)
            r.ping()
            print_colored("✓ Redis is connected", Colors.GREEN)
        except ImportError:
            print_colored("⚠ Redis package not installed, cannot test connection", Colors.YELLOW)
        except Exception as e:
            print_colored(f"✗ Redis connection failed: {e}", Colors.RED)
            all_healthy = False
    
    return all_healthy

def check_configuration_files() -> bool:
    """Check all configuration files"""
    print_section("Configuration Files")
    
    all_good = True
    
    files_to_check = [
        (Path('.env'), 'Root environment file'),
        (Path('server/.env'), 'Backend environment file'),
        (Path('client/.env.local'), 'Frontend environment file'),
        (Path('server/alembic.ini'), 'Alembic configuration'),
        (Path('docker-compose.yml'), 'Docker Compose configuration'),
        (Path('.python-version'), 'Python version file'),
    ]
    
    for file_path, description in files_to_check:
        if not check_file_exists(file_path, description):
            all_good = False
    
    # Check critical environment variables
    print_colored("\nChecking environment variables...", Colors.BLUE)
    
    # Backend environment
    backend_env = load_env_file(Path('server/.env'))
    os.environ.update(backend_env)  # Load for checking
    
    critical_vars = [
        'DATABASE_URL',
        'SECRET_KEY',
        'ENVIRONMENT',
    ]
    
    optional_vars = [
        'REDIS_URL',
        'SENTRY_DSN',
        'POLYGON_API_KEY',
    ]
    
    for var in critical_vars:
        success, _ = check_env_var(var, required=True)
        if not success:
            all_good = False
    
    for var in optional_vars:
        check_env_var(var, required=False)
    
    return all_good

def main():
    """Main validation function"""
    print_colored("Trading Tools Boilerplate - Setup Validation", Colors.BOLD)
    print_colored("=" * 45, Colors.BOLD)
    
    all_checks_passed = True
    
    # Run all checks
    checks = [
        check_configuration_files,
        check_python_setup,
        check_node_setup,
        check_docker_setup,
        check_database_connection,
        check_services_health,
    ]
    
    for check in checks:
        try:
            if not check():
                all_checks_passed = False
        except Exception as e:
            print_colored(f"\n✗ Check failed with error: {e}", Colors.RED)
            all_checks_passed = False
    
    # Summary
    print_section("Summary")
    
    if all_checks_passed:
        print_colored("✅ All checks passed! Your environment is properly configured.", Colors.GREEN + Colors.BOLD)
        print_colored("\nYou can start development with:", Colors.BLUE)
        print("  ./start-dev.sh         # Unix/Mac")
        print("  start-dev.bat          # Windows")
        print("\nOr with Docker:")
        print("  docker-compose up")
    else:
        print_colored("❌ Some checks failed. Please fix the issues above.", Colors.RED + Colors.BOLD)
        print_colored("\nFor help, refer to:", Colors.YELLOW)
        print("  - README.md")
        print("  - docs/LOCAL_DEVELOPMENT.md")
        print("  - docs/TROUBLESHOOTING.md (if available)")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_colored("\n\nValidation cancelled by user", Colors.YELLOW)
        sys.exit(0)