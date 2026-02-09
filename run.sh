#!/usr/bin/env bash
set -e

# OCR Arena - Frontend & Backend simultaneous launcher
# Usage: ./run.sh [--backend-port PORT] [--frontend-port PORT]
#   Default: backend=8000, frontend=3000

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT=8000
FRONTEND_PORT=3000

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --backend-port|-b)
      BACKEND_PORT="$2"
      shift 2
      ;;
    --frontend-port|-f)
      FRONTEND_PORT="$2"
      shift 2
      ;;
    --help|-h)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  -b, --backend-port PORT   Backend port (default: 8000)"
      echo "  -f, --frontend-port PORT  Frontend port (default: 3000)"
      echo "  -h, --help                Show this help"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

cleanup() {
  echo ""
  echo "Shutting down..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
  wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
  echo "Done."
}
trap cleanup EXIT INT TERM

# Kill existing processes on target ports (fuser is more reliable than lsof)
for PORT in $BACKEND_PORT $FRONTEND_PORT; do
  if fuser "$PORT/tcp" >/dev/null 2>&1; then
    echo "Killing existing process on port $PORT"
    fuser -k "$PORT/tcp" >/dev/null 2>&1 || true
    sleep 0.5
    # Force kill if still alive
    if fuser "$PORT/tcp" >/dev/null 2>&1; then
      fuser -k -9 "$PORT/tcp" >/dev/null 2>&1 || true
      sleep 0.5
    fi
  fi
done

echo "=== OCR Arena ==="
echo "Backend:  http://localhost:${BACKEND_PORT}"
echo "Frontend: http://localhost:${FRONTEND_PORT}"
echo "Press Ctrl+C to stop"
echo ""

# Backend
cd "$SCRIPT_DIR/backend"
uv run uvicorn app.main:app --reload --port "$BACKEND_PORT" &
BACKEND_PID=$!

# Frontend
cd "$SCRIPT_DIR/frontend"
NEXT_PUBLIC_API_URL="http://localhost:${BACKEND_PORT}" pnpm dev --port "$FRONTEND_PORT" &
FRONTEND_PID=$!

wait
