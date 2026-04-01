param(
    [switch]$RequireLive
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $projectRoot "docker-compose.prod.yml"
$apiPort = [Environment]::GetEnvironmentVariable("API_PORT")
if ([string]::IsNullOrWhiteSpace($apiPort)) {
    $apiPort = "8000"
}
$baseUrl = "http://localhost:$apiPort/api/v1"

try {
    & docker version *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "docker-unavailable"
    }
}
catch {
    if ($RequireLive) {
        throw "Docker daemon is unavailable; cannot run production stack validation."
    }
    Write-Host "Skipping live production stack validation because Docker daemon is unavailable."
    exit 0
}

function Invoke-Compose {
    param([string[]]$Args)
    & docker compose -f $composeFile @Args
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose $($Args -join ' ') failed."
    }
}

$stackStarted = $false

try {
    Invoke-Compose -Args @("build")
    Invoke-Compose -Args @("up", "-d")
    $stackStarted = $true
    Start-Sleep -Seconds 20
    & powershell -ExecutionPolicy Bypass -File (Join-Path $projectRoot "scripts\smoke.ps1") -BaseUrl $baseUrl -UseJwt
    if ($LASTEXITCODE -ne 0) {
        throw "Production smoke test failed."
    }
}
finally {
    if ($stackStarted) {
        & docker compose -f $composeFile down -v
    }
}
