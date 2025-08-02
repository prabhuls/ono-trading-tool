#!/bin/bash

# Start the backend server with proper environment

echo "Starting backend server..."

# Navigate to server directory
cd server

# Activate virtual environment
source venv/bin/activate

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000