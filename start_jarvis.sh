#!/bin/bash
# J.A.R.V.I.S. Neural Backend - Unified Control
# ---------------------------------------------
# Combined Launch: Port 8000 (Neural Core) & 8001 (Intel Hub)

set -e

echo "[JARVIS] Initializing Dual-Server Neuronal Core..."

# Activate virtual environment
if [ -d ".venv" ]; then
    echo "[JARVIS] Activating neural environment (.venv)..."
    source .venv/bin/activate
elif [ -d "backend/.venv" ]; then
    echo "[JARVIS] Activating neural environment (backend/.venv)..."
    source backend/.venv/bin/activate
else
    echo "[JARVIS] Warning: No .venv located. Using system python."
fi

# Kill any existing processes on ports 8000/8001
echo "[JARVIS] Clearing stale neural links..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:8001 | xargs kill -9 2>/dev/null || true

# Launch Neural Core (P8000)
# This core handles heavy AI, Voice, and Agent logic.
echo "[Neural Core] Starting FastAPI on port 8000..."
python -u backend/main.py &
API_PID=$!

# Launch Neural Worker (Celery) (Only if Redis is active)
if nc -z localhost 6379 2>/dev/null; then
    echo "[Neural Worker] Starting Celery Worker..."
    cd backend && celery -A celery_app worker --loglevel=info --pool=solo & 
    CELERY_PID=$!
    cd ..
else
    echo "[Neural Worker] Redis is offline. Celery worker startup bypassed (Eager mode active)."
    CELERY_PID=""
fi

# Launch Frontend (P3001)
echo "[Frontend] Starting Vite server on port 3001..."
npm run dev &
FE_PID=$!

if [ -n "$CELERY_PID" ]; then
    echo "[JARVIS] Systems Online. API_PID: $API_PID | CELERY_PID: $CELERY_PID | FE_PID: $FE_PID"
else
    echo "[JARVIS] Systems Online. API_PID: $API_PID | FE_PID: $FE_PID (Celery: Bypass)"
fi
echo "[JARVIS] Neural Pulse active. Press Ctrl+C to terminate all processes."

# Trap exit signals to ensure clean shutdown
trap "echo '[JARVIS] Powering down...'; kill \$API_PID \$FE_PID \$CELERY_PID 2>/dev/null || true; exit" SIGINT SIGTERM

# Stay active while servers run
wait
