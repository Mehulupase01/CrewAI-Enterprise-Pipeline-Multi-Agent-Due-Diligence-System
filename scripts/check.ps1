$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$conda = "C:\Users\Mehul-PC\anaconda3\Scripts\conda.exe"
$envName = "crewai-enterprise-pipeline"

Push-Location (Join-Path $projectRoot "apps\api")
& $conda run -n $envName python -m ruff check src tests
& $conda run -n $envName python -m pytest
Pop-Location

Push-Location (Join-Path $projectRoot "apps\web")
npm run lint
Pop-Location
