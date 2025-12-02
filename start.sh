#!/bin/bash

# Simple script to launch frontend and backend

echo "Starting TX Application..."

# Start backend in background
echo "Starting backend on port 8000..."
cd backend && python main.py &
BACKEND_PID=$!

# Give backend a moment to start
sleep 2

# Start frontend
echo "Starting frontend on port 3000..."
cd frontend && npm run dev &
FRONTEND_PID=$!

echo ""
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both services"

# Handle cleanup on exit
cleanup() {
    echo ""
    echo "Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for both processes
wait
