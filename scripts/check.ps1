$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$conda = "C:\Users\Mehul-PC\anaconda3\Scripts\conda.exe"
$envName = "crewai-enterprise-pipeline"

function Invoke-Step {
    param([scriptblock]$Command)

    & $Command
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Push-Location (Join-Path $projectRoot "apps\api")
Invoke-Step { & $conda run -n $envName python -m ruff check src tests }
Invoke-Step { & $conda run -n $envName python -m pytest }
Pop-Location

Push-Location (Join-Path $projectRoot "apps\web")
Invoke-Step { npm run lint }
Pop-Location
