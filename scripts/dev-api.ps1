$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$conda = "C:\Users\Mehul-PC\anaconda3\Scripts\conda.exe"
$envName = "crewai-enterprise-pipeline"

Push-Location (Join-Path $projectRoot "apps\api")
& $conda run -n $envName uvicorn crewai_enterprise_pipeline_api.main:app --reload --host 0.0.0.0 --port 8000
Pop-Location
