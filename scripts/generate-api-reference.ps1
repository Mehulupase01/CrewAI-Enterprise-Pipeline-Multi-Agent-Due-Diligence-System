param(
    [string]$OutputPath = (Join-Path (Split-Path -Parent $PSScriptRoot) "docs\api-reference.md")
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$conda = "C:\Users\Mehul-PC\anaconda3\Scripts\conda.exe"
$envName = "crewai-enterprise-pipeline"

Push-Location $projectRoot
& $conda run --no-capture-output -n $envName python .\scripts\generate_api_reference.py --output $OutputPath
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    exit $LASTEXITCODE
}
Pop-Location
