$ErrorActionPreference = "Stop"

function Test-CommandExists {
  param([string]$CommandName)

  return $null -ne (Get-Command $CommandName -ErrorAction SilentlyContinue)
}

if (-not (Test-CommandExists "uv")) {
  Write-Error "Missing required command: uv"
}

$frontendCmd = "pnpm dev"
if (-not (Test-CommandExists "pnpm")) {
  if (Test-CommandExists "npm") {
    $frontendCmd = "npm run dev"
  } else {
    Write-Error "Missing required command: pnpm or npm"
  }
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Check if using LiveKit Cloud or Local LiveKit server
$backendEnvPath = Join-Path $repoRoot "backend\.env.local"
$isCloudLiveKit = $false
if (Test-Path $backendEnvPath) {
  $envContent = Get-Content $backendEnvPath -Raw
  if ($envContent -like "*livekit.cloud*") {
    $isCloudLiveKit = $true
  }
}

$localExe = Join-Path $repoRoot "livekit-server.exe"
if ($isCloudLiveKit) {
  Write-Host "Using configured LiveKit Cloud server from .env.local" -ForegroundColor Cyan
} elseif (Test-Path $localExe) {
  Write-Host "Found local livekit-server.exe in root directory. Starting local LiveKit server..." -ForegroundColor Yellow
  Start-Process powershell -ArgumentList "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", "Set-Location '$repoRoot'; .\livekit-server.exe --dev --keys 'devkey: secret'"
} elseif (Test-CommandExists "livekit-server") {
  Write-Host "Found livekit-server in system PATH. Starting local LiveKit server..." -ForegroundColor Yellow
  Start-Process powershell -ArgumentList "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", "Set-Location '$repoRoot'; livekit-server --dev --keys 'devkey: secret'"
} else {
  Write-Warning "livekit-server was not found. Using configured LIVEKIT_URL."
}

# Start backend and frontend
Start-Process powershell -ArgumentList "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", "Set-Location '$repoRoot\backend'; uv run python src/agent.py dev"
Start-Process powershell -ArgumentList "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", "Set-Location '$repoRoot\frontend'; $frontendCmd"

Write-Host "Started all services in separate PowerShell windows."
