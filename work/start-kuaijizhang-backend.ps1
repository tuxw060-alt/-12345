$ErrorActionPreference = "Continue"

$projectRoot = "C:\Users\PC\Documents\Codex\2026-06-28\ge\backend"
$logDir = "C:\Users\PC\Documents\Codex\2026-06-28\ge\work\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

Set-Location $projectRoot
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 *>> (Join-Path $logDir "backend.log")
