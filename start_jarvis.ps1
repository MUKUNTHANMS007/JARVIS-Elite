# J.A.R.V.I.S. Neural Backend & Frontend - Windows Control
# ---------------------------------------------
# Launch: FastAPI (8000), Celery Worker, Vite Frontend (3001)

Write-Host "[JARVIS] Initializing JARVIS Architecture..."

# Resolve PIDs
$API_PORT = 8000
$FRONTEND_PORT = 3001

# Cleanup stale processes (Aggressive Neural Reset)
Write-Host "[JARVIS] Clearing stale links..."
$current_pids = (Get-NetTCPConnection -LocalPort $API_PORT, $FRONTEND_PORT -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique
foreach ($stale_pid in $current_pids) {
    if ($stale_pid -and $stale_pid -ne $PID) {
        Write-Host "Resetting Neural Channel: $stale_pid"
        Stop-Process -Id $stale_pid -Force -ErrorAction SilentlyContinue
    }
}

# Cleanup Celery
Stop-Process -Name "celery" -Force -ErrorAction SilentlyContinue
# Do not kill all Python processes globally; it can terminate unrelated work.
# Port-based cleanup above + Celery cleanup is sufficient.

# Start Neural Core API (P8000)
Write-Host "[Neural Core] Starting FastAPI on port 8000..."
$API_PROC = Start-Process -FilePath ".\backend\.venv\Scripts\python.exe" -ArgumentList "-u", "main.py" -WorkingDirectory ".\backend" -WindowStyle Normal -PassThru

# Start Celery Worker
Write-Host "[Neural Worker] Starting Celery Worker..."
$CELERY_PROC = Start-Process -FilePath ".\backend\.venv\Scripts\celery.exe" -ArgumentList "-A", "celery_app", "worker", "--loglevel=info", "--pool=solo" -WorkingDirectory ".\backend" -WindowStyle Normal -PassThru

# Start Frontend (P3001)
Write-Host "[Frontend] Starting Vite server on port 3001..."
$FE_PROC = Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" -WorkingDirectory ".\" -WindowStyle Normal -PassThru

Write-Host "[JARVIS] Systems Online."
Write-Host "API_PID: $($API_PROC.Id) | CELERY_PID: $($CELERY_PROC.Id) | FE_PID: $($FE_PROC.Id)"
Write-Host "[JARVIS] Neural Pulse active. Keep this window open."

# Wait for exit
Wait-Process -Id $API_PROC.Id, $CELERY_PROC.Id, $FE_PROC.Id -ErrorAction SilentlyContinue

Write-Host "[JARVIS] Powering down... Clearing processes."
Stop-Process -Id $API_PROC.Id, $CELERY_PROC.Id, $FE_PROC.Id -Force -ErrorAction SilentlyContinue

