$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot

Push-Location $projectRoot
docker compose up -d postgres redis minio prometheus grafana tempo
Pop-Location
