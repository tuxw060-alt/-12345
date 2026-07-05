$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$hookSource = Join-Path $repoRoot "scripts\git-hooks\post-commit"
$hookTarget = Join-Path $repoRoot ".git\hooks\post-commit"

if (!(Test-Path $hookSource)) {
    throw "Hook source not found: $hookSource"
}

Copy-Item -LiteralPath $hookSource -Destination $hookTarget -Force
Write-Host "Installed post-commit hook: $hookTarget"
