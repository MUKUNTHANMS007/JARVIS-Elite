# J.A.R.V.I.S. Neural Backend - Windows Control
# ---------------------------------------------
# Launch: Port 8000 (Neural Core) & 8001 (Intel Hub)

Write-Host "[JARVIS] Initializing Dual-Server Neuronal Core..."

# Resolve PIDs
$NC_PORT = 8000
$IH_PORT = 8001

# Cleanup stale processes
Write-Host "[JARVIS] Clearing stale neural links..."
$current_pids = (Get-NetTCPConnection -LocalPort $NC_PORT, $IH_PORT -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique
foreach ($stale_pid in $current_pids) {
    if ($stale_pid -ne 0 -and $stale_pid -ne $PID) {
        Write-Host "Killing stale process: $stale_pid"
        Stop-Process -Id $stale_pid -Force -ErrorAction SilentlyContinue
    }
}

# Start Neural Core (P8000)
Write-Host "[Neural Core] Starting on port 8000 (AI/Voice)..."
$NC_PROC = Start-Process -FilePath ".\backend\.venv\Scripts\python.exe" -ArgumentList "-u", "server1_neural.py" -WorkingDirectory ".\backend" -NoNewWindow -PassThru

# Start Intel Hub (P8001)
Write-Host "[Intel Hub] Starting on port 8001 (Data/Sync)..."
$IH_PROC = Start-Process -FilePath ".\backend\.venv\Scripts\python.exe" -ArgumentList "-u", "server2_hub.py" -WorkingDirectory ".\backend" -NoNewWindow -PassThru

Write-Host "[JARVIS] Systems Online. NC_PID: $($NC_PROC.Id) | IH_PID: $($IH_PROC.Id)"
Write-Host "[JARVIS] Neural Pulse active. Monitor logs for telemetry..."

# Maintenance Loop: Check every 30 seconds if servers are port-active
while ($true) {
    Start-Sleep -Seconds 30
    $nc_active = Get-NetTCPConnection -LocalPort $NC_PORT -ErrorAction SilentlyContinue
    $ih_active = Get-NetTCPConnection -LocalPort $IH_PORT -ErrorAction SilentlyContinue
    
    if (-not $nc_active) { Write-Host "[!!] Neural Core link lost."; break }
    if (-not $ih_active) { Write-Host "[!!] Intelligence Hub link lost."; break }
    
    Write-Host "[JARVIS] Neural Pulse check: Status Nominal."
}

Write-Host "[JARVIS] Powering down... Clearing stale processes."
$kill_pids = (Get-NetTCPConnection -LocalPort $NC_PORT, $IH_PORT -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique
foreach ($p in $kill_pids) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue }
