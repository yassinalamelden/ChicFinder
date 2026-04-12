#!/bin/bash
# ChicFinder Development Server Startup Script
# Starts both the FastAPI backend and Next.js frontend on their configured ports

set -e

echo "================================================"
echo "ChicFinder Development Servers"
echo "================================================"
echo ""
echo "Backend (FastAPI):  http://localhost:8000"
echo "Frontend (Next.js): http://localhost:3000"
echo "API Docs:           http://localhost:8000/docs"
echo ""
echo "To stop the servers, press Ctrl+C"
echo "================================================"
echo ""

# Kill any existing processes on our ports
echo "Checking for existing processes..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
sleep 1

# Start FastAPI backend
echo "Starting FastAPI backend (port 8000)..."
cd "$(dirname "$0")"
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Start Next.js frontend
echo "Starting Next.js frontend (port 3000)..."
cd website_fullstack
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Both servers are starting..."
echo "Logs will appear below:"
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
