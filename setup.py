#!/usr/bin/env python3
"""
Cross-platform setup script for Trading Tools Boilerplate
Handles setup for Windows, macOS, and Linux environments
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path
from typing import List, Tuple, Optional

# ANSI color codes for cross-platform colored output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_colored(message: str, color: str = Colors.END):
    """Print colored message, fallback to plain text on Windows if needed"""
    try:
        print(f"{color}{message}{Colors.END}")
    except:
        print(message)

def get_platform_info() -> dict:
    """Get platform-specific information"""
    system = platform.system()
    return {
        'system': system,
        'is_windows': system == 'Windows',
        'is_mac': system == 'Darwin',
        'is_linux': system == 'Linux',
        'python_version': sys.version_info,
        'architecture': platform.machine()
    }

def check_command(command: str) -> bool:
    """Check if a command is available in PATH"""
    return shutil.which(command) is not None

def run_command(command: List[str], shell: bool = False, check: bool = True) -> Tuple[int, str, str]:
    """Run a command and return exit code, stdout, and stderr"""
    try:
        if shell and isinstance(command, list):
            command = ' '.join(command)
        
        result = subprocess.run(
            command,
            shell=shell,
            capture_output=True,
            text=True,
            check=check
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return e.returncode, e.stdout or '', e.stderr or ''
    except Exception as e:
        return 1, '', str(e)

def check_python_version() -> bool:
    """Check if Python version is 3.9 or higher"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print_colored(f"Error: Python 3.9+ required, found {version.major}.{version.minor}", Colors.RED)
        return False
    print_colored(f"✓ Python {version.major}.{version.minor} detected", Colors.GREEN)
    return True

def check_node_version() -> bool:
    """Check if Node.js is installed and version 18+"""
    if not check_command('node'):
        print_colored("Error: Node.js not found", Colors.RED)
        return False
    
    code, stdout, _ = run_command(['node', '--version'])
    if code == 0:
        version_str = stdout.strip().lstrip('v')
        try:
            major_version = int(version_str.split('.')[0])
            if major_version >= 18:
                print_colored(f"✓ Node.js {version_str} detected", Colors.GREEN)
                return True
            else:
                print_colored(f"Error: Node.js 18+ required, found {version_str}", Colors.RED)
                return False
        except:
            print_colored("Error: Could not parse Node.js version", Colors.RED)
            return False
    return False

def check_docker() -> bool:
    """Check if Docker is installed and running"""
    platform_info = get_platform_info()
    
    if not check_command('docker'):
        print_colored("⚠ Docker not found (optional for containerized setup)", Colors.YELLOW)
        return False
    
    code, _, _ = run_command(['docker', 'info'], check=False)
    if code == 0:
        print_colored("✓ Docker is installed and running", Colors.GREEN)
        return True
    else:
        print_colored("⚠ Docker is installed but not running (optional)", Colors.YELLOW)
        if platform_info['is_windows']:
            print_colored("  On Windows, ensure Docker Desktop is running", Colors.YELLOW)
            print_colored("  You may need Administrator privileges", Colors.YELLOW)
        elif platform_info['is_linux']:
            print_colored("  On Linux, ensure Docker daemon is running", Colors.YELLOW)
            print_colored("  You may need to use 'sudo' or add your user to the docker group", Colors.YELLOW)
        elif platform_info['is_mac']:
            print_colored("  On macOS, ensure Docker Desktop is running", Colors.YELLOW)
        return False

def setup_python_venv(platform_info: dict) -> bool:
    """Setup Python virtual environment"""
    print_colored("\nSetting up Python virtual environment...", Colors.BLUE)
    
    server_dir = Path('server')
    venv_path = server_dir / 'venv'
    
    # Create virtual environment
    code, _, stderr = run_command([sys.executable, '-m', 'venv', str(venv_path)])
    if code != 0:
        print_colored(f"Error creating virtual environment: {stderr}", Colors.RED)
        return False
    
    # Get activation script path based on platform
    if platform_info['is_windows']:
        activate_path = venv_path / 'Scripts' / 'activate'
        pip_path = venv_path / 'Scripts' / 'pip'
        python_path = venv_path / 'Scripts' / 'python'
    else:
        activate_path = venv_path / 'bin' / 'activate'
        pip_path = venv_path / 'bin' / 'pip'
        python_path = venv_path / 'bin' / 'python'
    
    # Upgrade pip
    print_colored("Upgrading pip...", Colors.BLUE)
    code, _, _ = run_command([str(python_path), '-m', 'pip', 'install', '--upgrade', 'pip'])
    if code != 0:
        print_colored("Warning: Could not upgrade pip", Colors.YELLOW)
    
    # Install requirements
    requirements_path = server_dir / 'requirements.txt'
    if requirements_path.exists():
        print_colored("Installing Python dependencies...", Colors.BLUE)
        code, _, stderr = run_command([str(pip_path), 'install', '-r', str(requirements_path)])
        if code != 0:
            print_colored(f"Error installing requirements: {stderr}", Colors.RED)
            return False
    
    print_colored("✓ Python environment setup complete", Colors.GREEN)
    print_colored(f"  Activation command: {activate_path}", Colors.GREEN)
    return True

def setup_node_dependencies() -> bool:
    """Setup Node.js dependencies"""
    print_colored("\nSetting up Node.js dependencies...", Colors.BLUE)
    
    client_dir = Path('client')
    if not (client_dir / 'package.json').exists():
        print_colored("Error: package.json not found in client directory", Colors.RED)
        return False
    
    # Change to client directory
    original_dir = os.getcwd()
    os.chdir(client_dir)
    
    try:
        # Install dependencies
        print_colored("Installing Node.js dependencies...", Colors.BLUE)
        code, _, stderr = run_command(['npm', 'install'])
        if code != 0:
            print_colored(f"Error installing dependencies: {stderr}", Colors.RED)
            return False
        
        print_colored("✓ Node.js dependencies installed", Colors.GREEN)
        return True
    finally:
        os.chdir(original_dir)

def copy_env_files() -> None:
    """Copy .env.example files to .env"""
    print_colored("\nSetting up environment files...", Colors.BLUE)
    
    env_files = [
        ('server/.env.example', 'server/.env'),
        ('client/.env.example', 'client/.env.local'),
        ('.env.example', '.env')
    ]
    
    for src, dst in env_files:
        src_path = Path(src)
        dst_path = Path(dst)
        
        if src_path.exists() and not dst_path.exists():
            shutil.copy2(src_path, dst_path)
            print_colored(f"✓ Created {dst} from {src}", Colors.GREEN)
        elif dst_path.exists():
            print_colored(f"  {dst} already exists", Colors.YELLOW)

def setup_database_choice() -> str:
    """Ask user for database preference"""
    print_colored("\nDatabase Setup Options:", Colors.BLUE)
    print("1. PostgreSQL via Docker (recommended)")
    print("2. PostgreSQL native installation")
    
    while True:
        choice = input("\nSelect database option (1-2): ").strip()
        if choice in ['1', '2']:
            return choice
        print_colored("Invalid choice. Please enter 1 or 2.", Colors.RED)

def print_next_steps(platform_info: dict, docker_available: bool, db_choice: str):
    """Print next steps for the user"""
    print_colored("\n✅ Setup Complete!", Colors.GREEN + Colors.BOLD)
    print_colored("\nNext steps:", Colors.BLUE)
    
    # Platform-specific activation commands
    if platform_info['is_windows']:
        activate_cmd = "server\\venv\\Scripts\\activate"
        start_script = "start-dev.bat"
    else:
        activate_cmd = "source server/venv/bin/activate"
        start_script = "./start-dev.sh"
    
    print("\n1. Configure environment variables:")
    print("   - Edit server/.env")
    print("   - Edit client/.env.local")
    
    print("\n2. Run database migrations:")
    print(f"   {activate_cmd}")
    print("   cd server && alembic upgrade head")
    
    print_colored("\n3. Choose your development mode:", Colors.BLUE)
    
    if db_choice == '1' and docker_available:
        print("\n   Option A - Hybrid Mode (Recommended)")
        print("   Database/Redis in Docker, apps native with hot-reloading:")
        print(f"   {start_script}")
        
        print("\n   Option B - Full Docker Mode")
        print("   Everything runs in containers:")
        if platform_info['is_windows']:
            print_colored("   # Run as Administrator if you get permission errors", Colors.YELLOW)
        elif platform_info['is_linux'] or platform_info['is_mac']:
            print_colored("   # Use 'sudo docker-compose up' if you get permission errors", Colors.YELLOW)
        print("   docker-compose up")
        
    elif db_choice == '2':
        print("\n   Ensure PostgreSQL is running locally, then:")
        print(f"   {start_script}")
    
    print_colored("\n📝 Quick Reference:", Colors.BLUE)
    print("   Backend:  http://localhost:8000")
    print("   Frontend: http://localhost:3000")
    print("   API Docs: http://localhost:8000/docs")
    
    if platform_info['is_windows']:
        print("\n   Stop services: stop-dev.bat")
    else:
        print("\n   Stop services: ./stop-dev.sh")

def main():
    """Main setup function"""
    print_colored("Trading Tools Boilerplate Setup", Colors.HEADER + Colors.BOLD)
    print_colored("=" * 40, Colors.HEADER)
    
    # Get platform information
    platform_info = get_platform_info()
    print_colored(f"\nDetected platform: {platform_info['system']} ({platform_info['architecture']})", Colors.BLUE)
    
    # Check prerequisites
    print_colored("\nChecking prerequisites...", Colors.BLUE)
    
    if not check_python_version():
        sys.exit(1)
    
    if not check_node_version():
        print_colored("\nPlease install Node.js 18+ from https://nodejs.org/", Colors.YELLOW)
        sys.exit(1)
    
    docker_available = check_docker()
    
    # Setup Python environment
    if not setup_python_venv(platform_info):
        sys.exit(1)
    
    # Setup Node.js dependencies
    if not setup_node_dependencies():
        sys.exit(1)
    
    # Copy environment files
    copy_env_files()
    
    # Database setup choice
    db_choice = setup_database_choice()
    
    # Print next steps
    print_next_steps(platform_info, docker_available, db_choice)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_colored("\n\nSetup cancelled by user", Colors.YELLOW)
        sys.exit(0)
    except Exception as e:
        print_colored(f"\n\nError during setup: {e}", Colors.RED)
        sys.exit(1)