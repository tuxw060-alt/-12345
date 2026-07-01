$ErrorActionPreference = "Continue"

$cloudflared = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
$config = "C:\Users\PC\.cloudflared\config.yml"
$logDir = "C:\Users\PC\Documents\Codex\2026-06-28\ge\work\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

& $cloudflared tunnel --config $config run 0839825d-f0c3-4c21-a7e3-9b3297aff9eb *>> (Join-Path $logDir "tunnel.log")
