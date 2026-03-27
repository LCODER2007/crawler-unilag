# URAAS Setup Script for Windows PowerShell

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "URAAS Setup Script" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python version
$pythonVersion = python --version 2>&1
Write-Host "✓ Python version: $pythonVersion" -ForegroundColor Green

# Create virtual environment
Write-Host ""
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
python -m venv venv

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"

# Install dependencies
Write-Host ""
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
Write-Host ""
Write-Host "Creating directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "storage\pdfs" | Out-Null
New-Item -ItemType Directory -Force -Path "data" | Out-Null
New-Item -ItemType Directory -Force -Path "logs" | Out-Null

# Initialize database
Write-Host ""
Write-Host "Initializing database..." -ForegroundColor Yellow
python init_db.py

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✓ Setup complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Activate virtual environment:"
Write-Host "   venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "2. Start the dashboard:"
Write-Host "   python uraas/dashboard/app.py"
Write-Host ""
Write-Host "3. Open browser to http://localhost:8080"
Write-Host ""
Write-Host "4. Click 'Start Mining' to begin harvesting"
Write-Host ""
