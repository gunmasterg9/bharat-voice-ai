# =============================================================================
# Bharat Voice AI - Inspect SQLite Database (PowerShell Script)
# Shows clean non-sensitive summary of stored user profiles in data/bharat_voice.db
# =============================================================================

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Set-Location "$repoRoot\backend\src"
& "..\.venv\Scripts\python.exe" -m memory.inspect_db
Set-Location $repoRoot
