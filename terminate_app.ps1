# =============================================================================
# Bharat Voice AI - Terminate All Processes (PowerShell Script)
# Terminates Python agent processes, Node/Next.js frontend, and LiveKit server.
# =============================================================================

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Bharat Voice AI - Terminating All Active Local Processes" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Terminate Python processes running src/agent.py
$pythonProcs = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*agent.py*" -or $_.CommandLine -like "*livekit*"
}

if ($pythonProcs) {
    Write-Host "Stopping Python Voice Agent process..." -ForegroundColor Yellow
    foreach ($proc in $pythonProcs) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        Write-Host "Terminated Python Process PID" $proc.Id -ForegroundColor Green
    }
} else {
    Write-Host "No active Python Voice Agent processes found." -ForegroundColor Gray
}

# Terminate Node / pnpm dev frontend processes
$nodeProcs = Get-Process node -ErrorAction SilentlyContinue
if ($nodeProcs) {
    Write-Host "Stopping Node/Next.js Frontend process..." -ForegroundColor Yellow
    foreach ($proc in $nodeProcs) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        Write-Host "Terminated Node Process PID" $proc.Id -ForegroundColor Green
    }
} else {
    Write-Host "No active Node/Next.js frontend processes found." -ForegroundColor Gray
}

# Terminate livekit-server executable
$livekitProcs = Get-Process "livekit-server" -ErrorAction SilentlyContinue
if ($livekitProcs) {
    Write-Host "Stopping livekit-server process..." -ForegroundColor Yellow
    foreach ($proc in $livekitProcs) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        Write-Host "Terminated LiveKit Server PID" $proc.Id -ForegroundColor Green
    }
} else {
    Write-Host "No active livekit-server processes found." -ForegroundColor Gray
}

Write-Host "All local Bharat Voice AI processes have been terminated cleanly." -ForegroundColor Green
