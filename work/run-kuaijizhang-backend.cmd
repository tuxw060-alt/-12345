@echo off
set "PROJECT=C:\Users\PC\Documents\Codex\2026-06-28\ge\backend"
set "LOGDIR=C:\Users\PC\Documents\Codex\2026-06-28\ge\work\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
cd /d "%PROJECT%"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >> "%LOGDIR%\backend.log" 2>&1
