$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$conda = "C:\Users\Mehul-PC\anaconda3\Scripts\conda.exe"
$envName = "crewai-enterprise-pipeline"

Push-Location (Join-Path $projectRoot "apps\api")
& $conda run -n $envName arq crewai_enterprise_pipeline_api.worker.WorkerSettings
Pop-Location
