param(
    [string]$Suite = "all"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$conda = "C:\Users\Mehul-PC\anaconda3\Scripts\conda.exe"
$envName = "crewai-enterprise-pipeline"
$outputDir = Join-Path $projectRoot "artifacts\evaluations"

Push-Location (Join-Path $projectRoot "apps\api")
& $conda run -n $envName python -m crewai_enterprise_pipeline_api.evaluation.runner --output-dir $outputDir --suite $Suite
$exitCode = $LASTEXITCODE
Pop-Location

if ($exitCode -ne 0) {
    exit $exitCode
}
