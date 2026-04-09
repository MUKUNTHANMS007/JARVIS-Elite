# JARVIS Distributed Neural Bridge Initialization Script (v3: Multi-Server Support)
# This script handles the tunneling for both the Neural Core and the Intelligence Hub.

Write-Host "--- JARVIS Distributed Neural Bridge ---" -ForegroundColor Cyan
Write-Host "Distributed Architecture detected: 2 Servers required." -ForegroundColor Yellow
Write-Host "[1/2] Neural Core Tunnel: High-latency AI (Port 8000)" -ForegroundColor Green
Write-Host "[2/2] Intelligence Hub Tunnel: Real-time Data (Port 8001)" -ForegroundColor Green

$Choice = Read-Host "Which tunnel would you like to launch? (1: Neural / 2: Hub / 3: Both - Background)"

if ($Choice -eq "1") {
    Write-Host "Launching Neural Tunnel (Port 8000)..." -ForegroundColor Cyan
    npx cloudflared tunnel --url http://127.0.0.1:8000
} elseif ($Choice -eq "2") {
    Write-Host "Launching Intelligence Hub Tunnel (Port 8001)..." -ForegroundColor Cyan
    npx cloudflared tunnel --url http://127.0.0.1:8001
} elseif ($Choice -eq "3") {
    Write-Host "Launching BOTH tunnels in background jobs..." -ForegroundColor Yellow
    Start-Job -ScriptBlock { npx cloudflared tunnel --url http://127.0.0.1:8000 }
    Start-Job -ScriptBlock { npx cloudflared tunnel --url http://127.0.0.1:8001 }
    Write-Host "Tunnels active as background jobs. Use Get-Job to monitor."
    Write-Host "WARNING: You will need to check job output for the '.trycloudflare.com' URLs."
} else {
    Write-Host "Invalid choice. Aborting."
}
