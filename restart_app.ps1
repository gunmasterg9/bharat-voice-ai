# =============================================================================
# Bharat Voice AI - Restart App & Verify Persistent Memory (PowerShell Script)
# Terminates running processes, inspects SQLite database, and restarts app.
# =============================================================================

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Bharat Voice AI - Restarting Application & Re-Connecting Session" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Terminate running processes
$terminateScript = Join-Path $repoRoot "terminate_app.ps1"
if (Test-Path $terminateScript) {
    & powershell -ExecutionPolicy Bypass -File $terminateScript
}

Start-Sleep -Seconds 1

# 2. Inspect SQLite database before restarting
Write-Host "------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host "Inspecting Persistent SQLite Memory Database (data/bharat_voice.db)..." -ForegroundColor DarkCyan
Write-Host "------------------------------------------------------------" -ForegroundColor DarkCyan

Set-Location "$repoRoot\backend\src"
& "..\.venv\Scripts\python.exe" -m memory.inspect_db
Set-Location $repoRoot

Start-Sleep -Seconds 1

# 3. Restart application services
Write-Host "Starting Bharat Voice AI application..." -ForegroundColor Yellow
$startScript = Join-Path $repoRoot "start_app.ps1"
if (Test-Path $startScript) {
    & powershell -ExecutionPolicy Bypass -File $startScript
}

Write-Host "Restart complete! Test Call #2 with persistent memory identity." -ForegroundColor Green
