$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$conda = "C:\Users\Mehul-PC\anaconda3\Scripts\conda.exe"
$envName = "crewai-enterprise-pipeline"
$evaluationOutputDir = Join-Path $projectRoot "artifacts\evaluations"
$baselinePath = Join-Path $projectRoot "artifacts\baselines\all-supported-suites-baseline.json"
$condaRun = @("run", "--no-capture-output", "-n", $envName)

function Invoke-Step {
    param([scriptblock]$Command)

    & $Command
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Push-Location (Join-Path $projectRoot "apps\api")
Invoke-Step { & $conda @condaRun python -m ruff check src tests }
Invoke-Step { & $conda @condaRun python -m pytest }
Invoke-Step {
    & $conda @condaRun python -m crewai_enterprise_pipeline_api.evaluation.runner --output-dir $evaluationOutputDir
}
Invoke-Step {
    & $conda @condaRun python -m crewai_enterprise_pipeline_api.evaluation.performance --output-dir $evaluationOutputDir
}
Invoke-Step {
    & $conda @condaRun python -m crewai_enterprise_pipeline_api.evaluation.regression --report-dir $evaluationOutputDir --baseline $baselinePath
}
if ($env:PHASE17_ENABLE_LIVE_VALIDATION -eq "true" -or $env:PHASE17_REQUIRE_LIVE_VALIDATION -eq "true") {
    if ($env:PHASE17_REQUIRE_LIVE_VALIDATION -eq "true") {
        Invoke-Step {
            & $conda @condaRun python -m crewai_enterprise_pipeline_api.evaluation.live_validation --output-dir $evaluationOutputDir --require-live
        }
    }
    else {
        Invoke-Step {
            & $conda @condaRun python -m crewai_enterprise_pipeline_api.evaluation.live_validation --output-dir $evaluationOutputDir
        }
    }
}
Pop-Location

Push-Location (Join-Path $projectRoot "apps\web")
Invoke-Step { npm run lint }
Invoke-Step { npm run typecheck }
Invoke-Step { npm run build }
Pop-Location

Push-Location $projectRoot
Invoke-Step { & powershell -ExecutionPolicy Bypass -File (Join-Path $projectRoot "scripts\generate-api-reference.ps1") }
Invoke-Step { & powershell -ExecutionPolicy Bypass -File (Join-Path $projectRoot "scripts\backup-db.ps1") -DryRun }
Invoke-Step { docker compose -f (Join-Path $projectRoot "docker-compose.prod.yml") config | Out-Null }
if ($env:PHASE18_ENABLE_PROD_STACK_VALIDATION -eq "true" -or $env:PHASE18_REQUIRE_PROD_STACK_VALIDATION -eq "true") {
    if ($env:PHASE18_REQUIRE_PROD_STACK_VALIDATION -eq "true") {
        Invoke-Step {
            & powershell -ExecutionPolicy Bypass -File (Join-Path $projectRoot "scripts\validate-prod-stack.ps1") -RequireLive
        }
    }
    else {
        Invoke-Step {
            & powershell -ExecutionPolicy Bypass -File (Join-Path $projectRoot "scripts\validate-prod-stack.ps1")
        }
    }
}
Pop-Location
