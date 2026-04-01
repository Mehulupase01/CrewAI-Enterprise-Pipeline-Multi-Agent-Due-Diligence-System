param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Get-EnvValue {
    param([string]$Name, [string]$DefaultValue = "")

    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($value)) {
        return $DefaultValue
    }
    return $value
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$backupPath = [System.IO.Path]::GetFullPath($BackupFile)
$postgresDb = Get-EnvValue "POSTGRES_DB" "crewai_pipeline"
$postgresUser = Get-EnvValue "POSTGRES_USER" "crewai"
$postgresPassword = Get-EnvValue "POSTGRES_PASSWORD" "crewai"
$postgresHost = Get-EnvValue "POSTGRES_HOST" "localhost"
$postgresPort = Get-EnvValue "POSTGRES_PORT" "5432"
$dockerComposeFile = Join-Path $projectRoot "docker-compose.prod.yml"

if (-not (Test-Path -LiteralPath $backupPath)) {
    throw "Backup file not found: $backupPath"
}

$plan = [pscustomobject]@{
    backup_file = $backupPath
    postgres_db = $postgresDb
    postgres_host = $postgresHost
    postgres_port = $postgresPort
}

if ($DryRun) {
    $plan | ConvertTo-Json -Depth 3
    exit 0
}

$psqlCommand = Get-Command psql -ErrorAction SilentlyContinue
if ($psqlCommand) {
    $env:PGPASSWORD = $postgresPassword
    Get-Content -LiteralPath $backupPath | & $psqlCommand.Source --host $postgresHost --port $postgresPort --username $postgresUser --dbname $postgresDb
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    exit $LASTEXITCODE
}

$dockerAvailable = $false
try {
    docker version | Out-Null
    $dockerAvailable = $true
}
catch {
    $dockerAvailable = $false
}

if (-not $dockerAvailable) {
    throw "Neither psql nor a reachable Docker daemon is available for restore."
}

Get-Content -LiteralPath $backupPath | docker compose -f $dockerComposeFile exec -T postgres psql -U $postgresUser -d $postgresDb
if ($LASTEXITCODE -ne 0) {
    throw "docker compose restore failed."
}
