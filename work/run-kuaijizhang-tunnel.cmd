@echo off
set "LOGDIR=C:\Users\PC\Documents\Codex\2026-06-28\ge\work\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --config "C:\Users\PC\.cloudflared\config.yml" run 0839825d-f0c3-4c21-a7e3-9b3297aff9eb >> "%LOGDIR%\tunnel.log" 2>&1
