#!/bin/bash

echo "=========================================="
echo "URAAS Setup Script"
echo "=========================================="
echo ""

# Check Python version
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
if [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p storage/pdfs
mkdir -p data
mkdir -p logs

# Copy .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env file..."
    cp .env .env.backup 2>/dev/null || true
fi

# Initialize database
echo ""
echo "Initializing database..."
python init_db.py

echo ""
echo "=========================================="
echo "✓ Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Activate virtual environment:"
echo "   source venv/bin/activate  (Linux/Mac)"
echo "   venv\\Scripts\\activate     (Windows)"
echo ""
echo "2. Start the dashboard:"
echo "   python uraas/dashboard/app.py"
echo ""
echo "3. Open browser to http://localhost:8080"
echo ""
echo "4. Click 'Start Mining' to begin harvesting"
echo ""
