#!/bin/bash
# Environment setup for ScanX development
# Source this file with: source environment.sh

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Virtual environment not found. Run: python3 -m venv venv"
    return 1
fi

# Load .env file if it exists
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
    echo "✅ Loaded environment variables from .env"
else
    echo "⚠️  No .env file found. Create one with your API keys."
fi

# Set default environment variables (non-sensitive)
export DEBUG=True
export SECRET_KEY="your-secret-key-here"
export DATABASE_URL="sqlite:///db.sqlite3"
export CLINICALTRIALS_API_URL="https://clinicaltrials.gov/api/v2"
export ALLOWED_HOSTS="localhost,127.0.0.1"

echo "✅ Environment variables loaded for ScanX development"
echo "🚀 Ready to run: python manage.py runserver" 