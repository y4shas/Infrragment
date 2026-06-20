#!/bin/bash
# Infrragment — One-command startup script
# Starts both the FastAPI backend and the Vite frontend dev server

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

echo "╔══════════════════════════════════════════════╗"
echo "║   Infrragment — PDF Document Structuring     ║"
echo "╚══════════════════════════════════════════════╝"

# Check Python venv
if [ ! -d "$BACKEND_DIR/.venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$BACKEND_DIR/.venv"
    echo "Installing Python dependencies..."
    "$BACKEND_DIR/.venv/bin/pip" install -r "$BACKEND_DIR/requirements.txt"
fi

# Check frontend node_modules
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd "$FRONTEND_DIR" && npm install
fi

# Start backend
echo ""
echo "Starting backend on http://localhost:8000..."
cd "$BACKEND_DIR" && .venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend on http://localhost:5173..."
cd "$FRONTEND_DIR" && npm run dev &
FRONTEND_PID=$!

echo ""
echo "═══════════════════════════════════════════════"
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo "  API Docs: http://localhost:8000/docs"
echo "═══════════════════════════════════════════════"
echo ""
echo "Press Ctrl+C to stop both servers."

# Handle Ctrl+C
trap "echo 'Shutting down...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

# Wait for either process to exit
wait
