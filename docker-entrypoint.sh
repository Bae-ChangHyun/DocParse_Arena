#!/bin/sh
set -e

# Graceful shutdown handler
cleanup() {
    echo "Shutting down..."
    if [ -n "$BACKEND_PID" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
    fi
    exit 0
}

trap cleanup TERM INT

# Start backend (uvicorn) in background
echo "Starting backend..."
cd /app/backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Wait for backend to be healthy (max 30 seconds)
echo "Waiting for backend..."
TRIES=0
MAX_TRIES=30
until curl -sf http://127.0.0.1:8000/api/health > /dev/null 2>&1; do
    TRIES=$((TRIES + 1))
    if [ "$TRIES" -ge "$MAX_TRIES" ]; then
        echo "Backend failed to start within ${MAX_TRIES}s"
        exit 1
    fi
    sleep 1
done
echo "Backend ready."

# Start frontend (Next.js standalone)
echo "Starting frontend..."
cd /app/frontend
HOSTNAME=0.0.0.0 PORT=3000 exec node server.js
