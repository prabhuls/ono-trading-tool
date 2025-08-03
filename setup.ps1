# Trading Tools Boilerplate Setup Script for Windows PowerShell
# This script sets up the development environment on Windows

Write-Host "Trading Tools Boilerplate Setup (Windows PowerShell)" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator (optional, but recommended)
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "Warning: Not running as Administrator. Some operations might fail." -ForegroundColor Yellow
    Write-Host ""
}

# Check execution policy
$executionPolicy = Get-ExecutionPolicy
if ($executionPolicy -eq "Restricted") {
    Write-Host "Error: PowerShell execution policy is set to Restricted." -ForegroundColor Red
    Write-Host "To run this script, execute the following command as Administrator:" -ForegroundColor Yellow
    Write-Host "  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Green
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Check Python
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Python detected: $pythonVersion" -ForegroundColor Green
    }
} catch {
    Write-Host "Error: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.9+ from https://www.python.org/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check Node.js
try {
    $nodeVersion = node --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Node.js detected: $nodeVersion" -ForegroundColor Green
    }
} catch {
    Write-Host "Error: Node.js is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Node.js 18+ from https://nodejs.org/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check Docker (optional)
try {
    $dockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Docker detected: $dockerVersion" -ForegroundColor Green
        
        # Check if Docker is running
        docker info 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "⚠ Docker is installed but not running" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "⚠ Docker not found (optional for containerized setup)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Running setup..." -ForegroundColor Blue

# Run the cross-platform Python setup script
python setup.py
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Error: Setup failed" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "✅ Setup completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "To activate the Python virtual environment, run:" -ForegroundColor Cyan
Write-Host "  server\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
Write-Host ""
Write-Host "If you get an error about execution policy, run:" -ForegroundColor Cyan
Write-Host "  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Yellow
Write-Host ""
Read-Host "Press Enter to exit"