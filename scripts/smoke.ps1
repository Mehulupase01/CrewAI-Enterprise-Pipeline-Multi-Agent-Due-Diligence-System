param(
    [string]$BaseUrl = "http://localhost:8000/api/v1",
    [string]$UserId = "smoke-user",
    [string]$UserName = "Smoke Tester",
    [string]$UserEmail = "smoke@example.com",
    [string]$UserRole = "admin",
    [switch]$UseJwt,
    [string]$ClientId = "",
    [string]$ClientSecret = "",
    [string]$OrgId = ""
)

$ErrorActionPreference = "Stop"

if ($UseJwt) {
    if ([string]::IsNullOrWhiteSpace($ClientId)) {
        $ClientId = if ($env:DEFAULT_API_CLIENT_ID) { $env:DEFAULT_API_CLIENT_ID } else { "local-admin-client" }
    }
    if ([string]::IsNullOrWhiteSpace($ClientSecret)) {
        $ClientSecret = if ($env:DEFAULT_API_CLIENT_SECRET) { $env:DEFAULT_API_CLIENT_SECRET } else { "local-admin-secret" }
    }
    if ([string]::IsNullOrWhiteSpace($OrgId)) {
        $OrgId = if ($env:DEFAULT_ORG_ID) { $env:DEFAULT_ORG_ID } else { "00000000-0000-0000-0000-000000000001" }
    }

    $tokenResponse = Invoke-RestMethod -Uri "$BaseUrl/auth/token" -Method Post -ContentType "application/json" -Body (@{
        client_id = $ClientId
        client_secret = $ClientSecret
        org_id = $OrgId
    } | ConvertTo-Json)

    $headers = @{
        "Authorization" = "Bearer $($tokenResponse.access_token)"
    }
}
else {
    $headers = @{
        "X-CEP-User-Id" = $UserId
        "X-CEP-User-Name" = $UserName
        "X-CEP-User-Email" = $UserEmail
        "X-CEP-User-Role" = $UserRole
    }
}

$checks = @(
    @{ Name = "health"; Url = "$BaseUrl/system/health"; UseHeaders = $false },
    @{ Name = "readiness"; Url = "$BaseUrl/system/readiness"; UseHeaders = $false },
    @{ Name = "overview"; Url = "$BaseUrl/system/overview"; UseHeaders = $false },
    @{ Name = "liveness"; Url = "$BaseUrl/health/liveness"; UseHeaders = $false },
    @{ Name = "readiness_v2"; Url = "$BaseUrl/health/readiness"; UseHeaders = $false },
    @{ Name = "source_adapters"; Url = "$BaseUrl/source-adapters"; UseHeaders = $true },
    @{ Name = "cases"; Url = "$BaseUrl/cases"; UseHeaders = $true }
)

$results = @()
foreach ($check in $checks) {
    $invokeParams = @{
        Uri = $check.Url
        Method = "Get"
        Headers = $(if ($check.UseHeaders) { $headers } else { @{} })
    }

    $response = Invoke-WebRequest @invokeParams
    $results += [pscustomobject]@{
        name = $check.Name
        status_code = $response.StatusCode
        request_id = $response.Headers["X-Request-ID"]
    }
}

$results | Format-Table -AutoSize
