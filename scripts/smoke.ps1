param(
    [string]$BaseUrl = "http://localhost:8000/api/v1",
    [string]$UserId = "smoke-user",
    [string]$UserName = "Smoke Tester",
    [string]$UserEmail = "smoke@example.com",
    [string]$UserRole = "admin"
)

$ErrorActionPreference = "Stop"

$headers = @{
    "X-CEP-User-Id" = $UserId
    "X-CEP-User-Name" = $UserName
    "X-CEP-User-Email" = $UserEmail
    "X-CEP-User-Role" = $UserRole
}

$checks = @(
    @{ Name = "health"; Url = "$BaseUrl/system/health"; UseHeaders = $false },
    @{ Name = "readiness"; Url = "$BaseUrl/system/readiness"; UseHeaders = $false },
    @{ Name = "overview"; Url = "$BaseUrl/system/overview"; UseHeaders = $false },
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
