#!/bin/bash

# Start the backend server
echo "Starting backend server..."
cd server
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start the frontend
echo "Starting frontend..."
cd ../client
npm run dev &
FRONTEND_PID=$!

# Function to handle cleanup
cleanup() {
    echo "Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit
}

# Set up trap for cleanup on script exit
trap cleanup EXIT INT TERM

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID