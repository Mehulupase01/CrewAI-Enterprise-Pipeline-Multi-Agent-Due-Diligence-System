param(
    [string]$OutputDir = (Join-Path (Split-Path -Parent $PSScriptRoot) "artifacts\backups"),
    [int]$RetentionDays = 30,
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
$timestamp = Get-Date -Format "yyyyMMddTHHmmssZ"
$backupDir = [System.IO.Path]::GetFullPath($OutputDir)
$backupFile = Join-Path $backupDir "crewai-enterprise-pipeline-$timestamp.sql"

$postgresDb = Get-EnvValue "POSTGRES_DB" "crewai_pipeline"
$postgresUser = Get-EnvValue "POSTGRES_USER" "crewai"
$postgresPassword = Get-EnvValue "POSTGRES_PASSWORD" "crewai"
$postgresHost = Get-EnvValue "POSTGRES_HOST" "localhost"
$postgresPort = Get-EnvValue "POSTGRES_PORT" "5432"
$dockerComposeFile = Join-Path $projectRoot "docker-compose.prod.yml"

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
$pgDumpCommand = Get-Command pg_dump -ErrorAction SilentlyContinue

$uploadEnabled = (Get-EnvValue "BACKUP_S3_UPLOAD_ENABLED" "false").ToLowerInvariant() -eq "true"
$uploadBucket = Get-EnvValue "BACKUP_S3_BUCKET"
$uploadEndpoint = Get-EnvValue "BACKUP_S3_ENDPOINT"
$uploadPrefix = Get-EnvValue "BACKUP_S3_PREFIX" "db"

$plan = [pscustomobject]@{
    backup_file = $backupFile
    postgres_db = $postgresDb
    postgres_host = $postgresHost
    postgres_port = $postgresPort
    retention_days = $RetentionDays
    upload_enabled = $uploadEnabled
    upload_bucket = $uploadBucket
    upload_endpoint = $uploadEndpoint
}

if ($DryRun) {
    $plan | ConvertTo-Json -Depth 3
    exit 0
}

New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

if ($pgDumpCommand) {
    $env:PGPASSWORD = $postgresPassword
    & $pgDumpCommand.Source --clean --if-exists --no-owner --file $backupFile --host $postgresHost --port $postgresPort --username $postgresUser $postgresDb
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}
else {
    $dockerAvailable = $false
    try {
        docker version | Out-Null
        $dockerAvailable = $true
    }
    catch {
        $dockerAvailable = $false
    }

    if (-not $dockerAvailable) {
        throw "Neither pg_dump nor a reachable Docker daemon is available for backup."
    }

    $dockerTarget = "postgres"
    $command = @(
        "compose", "-f", $dockerComposeFile,
        "exec", "-T", $dockerTarget,
        "pg_dump", "--clean", "--if-exists", "--no-owner",
        "-U", $postgresUser, "-d", $postgresDb
    )

    $dumpContent = & docker @command
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose exec pg_dump failed."
    }
    Set-Content -LiteralPath $backupFile -Value $dumpContent -Encoding UTF8
}

Get-ChildItem -LiteralPath $backupDir -File |
    Where-Object { $_.LastWriteTimeUtc -lt (Get-Date).ToUniversalTime().AddDays(-$RetentionDays) } |
    Remove-Item -Force

if ($uploadEnabled) {
    if (-not $pythonCommand) {
        throw "BACKUP_S3_UPLOAD_ENABLED=true but python is not available for boto3 upload."
    }
    $env:BACKUP_UPLOAD_FILE = $backupFile
    $env:BACKUP_UPLOAD_BUCKET = $uploadBucket
    $env:BACKUP_UPLOAD_ENDPOINT = $uploadEndpoint
    $env:BACKUP_UPLOAD_PREFIX = $uploadPrefix
    @'
import os
from pathlib import Path

import boto3

file_path = Path(os.environ["BACKUP_UPLOAD_FILE"])
bucket = os.environ["BACKUP_UPLOAD_BUCKET"]
endpoint = os.environ.get("BACKUP_UPLOAD_ENDPOINT") or None
prefix = os.environ.get("BACKUP_UPLOAD_PREFIX", "db").strip("/")
region = os.environ.get("BACKUP_S3_REGION") or None
access_key = os.environ.get("BACKUP_S3_ACCESS_KEY")
secret_key = os.environ.get("BACKUP_S3_SECRET_KEY")

session = boto3.session.Session()
client = session.client(
    "s3",
    endpoint_url=endpoint,
    region_name=region,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
)
key = f"{prefix}/{file_path.name}" if prefix else file_path.name
client.upload_file(str(file_path), bucket, key)
print(f"uploaded:{bucket}/{key}")
'@ | python -
}

Write-Host "Database backup created at $backupFile"
