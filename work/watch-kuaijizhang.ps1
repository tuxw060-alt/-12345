$ErrorActionPreference = "Continue"

$workDir = "C:\Users\PC\Documents\Codex\2026-06-28\ge\work"
$logDir = Join-Path $workDir "logs"
$watchLog = Join-Path $logDir "watchdog.log"
$backendStarter = Join-Path $workDir "start-kuaijizhang-backend.ps1"
$tunnelStarter = Join-Path $workDir "start-kuaijizhang-tunnel.ps1"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Write-WatchLog($message) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $watchLog -Value "[$stamp] $message"
}

function Test-Backend {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/health" -UseBasicParsing -TimeoutSec 5
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Test-KuaijizhangTunnelProcess {
    $procs = Get-CimInstance Win32_Process -Filter "name='cloudflared.exe'" -ErrorAction SilentlyContinue
    foreach ($proc in $procs) {
        if ($proc.CommandLine -match "0839825d-f0c3-4c21-a7e3-9b3297aff9eb" -or $proc.CommandLine -match "config.yml") {
            return $true
        }
    }
    return $false
}

if (-not (Test-Backend)) {
    Write-WatchLog "Backend is down; starting it."
    Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$backendStarter`"" -WindowStyle Hidden
} else {
    Write-WatchLog "Backend is healthy."
}

Start-Sleep -Seconds 3

if (-not (Test-KuaijizhangTunnelProcess)) {
    Write-WatchLog "Kuaijizhang tunnel is down; starting it."
    Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$tunnelStarter`"" -WindowStyle Hidden
} else {
    Write-WatchLog "Kuaijizhang tunnel process is running."
}
