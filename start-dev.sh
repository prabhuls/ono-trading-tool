#!/bin/bash

# Start all services for development

echo "Starting Trading Tools development environment..."

# Start Docker services
docker compose up -d postgres redis

# Start backend
cd server
source venv/bin/activate
# Export environment variables from .env file
export $(grep -v '^#' .env | xargs)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Start frontend
cd client
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "Services started:"
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:3000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "kill $BACKEND_PID $FRONTEND_PID; docker compose down; exit" INT
wait
