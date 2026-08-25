#!/bin/bash
# Bootstrap script for AI CMS on Linux/macOS
# Sets up the project from scratch

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "==================================="
echo "AI CMS Bootstrap Setup"
echo "==================================="
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
source .venv/bin/activate
echo "✓ Virtual environment activated"

# Upgrade pip
echo "Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
echo "✓ Pip upgraded"

# Install dependencies
echo "Installing dependencies (this may take a few minutes)..."
pip install -r requirements/development.txt > /dev/null 2>&1
echo "✓ Dependencies installed"

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "✓ .env file created (remember to configure API keys)"
else
    echo "✓ .env file already exists"
fi

# Run migrations
echo "Running database migrations..."
python manage.py migrate > /dev/null 2>&1
echo "✓ Database migrations completed"

# Setup AI CMS
echo "Setting up AI CMS..."
python manage.py setup_ai_cms > /dev/null 2>&1
echo "✓ AI CMS setup completed"

# Collect static files for development
echo "Collecting static files..."
python manage.py collectstatic --noinput > /dev/null 2>&1
echo "✓ Static files collected"

echo ""
echo "==================================="
echo "✓ Setup Complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "1. Create a superuser:"
echo "   python manage.py createsuperuser"
echo ""
echo "2. Start the development server:"
echo "   python manage.py runserver"
echo ""
echo "3. Access Wagtail admin at:"
echo "   http://localhost:8000/admin"
echo ""
echo "Optional: Start background services"
echo "  - Celery worker:  celery -A config worker --loglevel=info"
echo "  - Celery beat:    celery -A config beat --loglevel=info"
echo "  - Redis:          docker run -p 6379:6379 redis:latest"
echo "  - Qdrant:         docker run -p 6333:6333 qdrant/qdrant"
echo ""
echo "Documentation: See README.md for more information"
echo ""
