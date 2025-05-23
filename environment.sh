#!/bin/bash
# Environment variables for ScanX development
# Source this file with: source environment.sh

export DEBUG=True
export SECRET_KEY="your-secret-key-here"
export DATABASE_URL="sqlite:///db.sqlite3"
export OPENAI_API_KEY="your-openai-api-key-here"
export CLINICALTRIALS_API_URL="https://clinicaltrials.gov/api/v2"
export ALLOWED_HOSTS="localhost,127.0.0.1"

echo "Environment variables loaded for ScanX development" 