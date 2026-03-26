$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$conda = "C:\Users\Mehul-PC\anaconda3\Scripts\conda.exe"
$envName = "crewai-enterprise-pipeline"
$evaluationOutputDir = Join-Path $projectRoot "artifacts\evaluations"

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
Invoke-Step {
    & $conda run -n $envName python -m crewai_enterprise_pipeline_api.evaluation.runner --output-dir $evaluationOutputDir
}
Pop-Location

Push-Location (Join-Path $projectRoot "apps\web")
Invoke-Step { npm run lint }
Invoke-Step { npm run typecheck }
Pop-Location
