#!/bin/bash

# Stop all services

echo "Stopping all services..."

# Stop backend
pkill -f "uvicorn app.main:app"

# Stop frontend
pkill -f "next dev"

# Stop Docker services
docker compose down

echo "All services stopped"
