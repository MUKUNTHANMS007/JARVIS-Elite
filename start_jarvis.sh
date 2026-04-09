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
echo "[Neural Core] Starting on port 8000 (AI/Voice)..."
python -u backend/server1_neural.py &
NC_PID=$!

# Launch Intelligence Hub (P8001)
# This hub handles sync, telemetry, and frontend pulse.
echo "[Intel Hub] Starting on port 8001 (Data/Sync)..."
python -u backend/server2_hub.py &
IH_PID=$!

echo "[JARVIS] Systems Online. NC_PID: $NC_PID | IH_PID: $IH_PID"
echo "[JARVIS] Neural Pulse active. Press Ctrl+C to terminate both servers."

# Trap exit signals to ensure clean shutdown
trap "echo '[JARVIS] Powering down...'; kill $NC_PID $IH_PID 2>/dev/null || true; exit" SIGINT SIGTERM

# Stay active while servers run
wait
