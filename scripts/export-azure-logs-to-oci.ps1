param(
    [string] $WorkspaceId = '6f4e5048-fa5d-4917-9ad3-a86edf6bf44a',
    [string] $Bucket = 'ninjasec-grafana-azure-logs'
)

$ErrorActionPreference = 'Stop'
$source = Get-AutomationVariable -Name 'OciAuditReader' | ConvertFrom-Json
$namespace = Get-AutomationVariable -Name 'OciGrafanaLogsNamespace'
$tokenUri = $env:IDENTITY_ENDPOINT + '?resource=' + [uri]::EscapeDataString('https://api.loganalytics.io')
$token = (Invoke-RestMethod -Uri $tokenUri -Headers @{
    Metadata = 'true'
    'X-IDENTITY-HEADER' = $env:IDENTITY_HEADER
} -TimeoutSec 30).access_token

$query = @'
NINJASECOCIAudit_CL
| where TimeGenerated > ago(48h) and isnotempty(EventId)
| summarize arg_max(TimeGenerated, EventName, Region, ResponseStatus) by EventId
| project TimeGenerated, EventId, EventName, Region, ResponseStatus
| top 100 by TimeGenerated desc
'@
$result = Invoke-RestMethod -Method Post -Uri "https://api.loganalytics.azure.com/v1/workspaces/$WorkspaceId/query" -Headers @{
    Authorization = "Bearer $token"
} -ContentType 'application/json' -Body (@{ query = $query } | ConvertTo-Json -Compress) -TimeoutSec 60
if ($result.error -or $result.tables.Count -ne 1) { throw 'Log Analytics query did not return a complete result.' }

$table = $result.tables[0]
$events = @(foreach ($row in $table.rows) {
    $event = [ordered]@{}
    for ($i = 0; $i -lt $table.columns.Count; $i++) {
        $event[$table.columns[$i].name] = $row[$i]
    }
    [pscustomobject]$event
})
$snapshot = [ordered]@{
    workspaceId = $WorkspaceId
    table = 'NINJASECOCIAudit_CL'
    exportedAt = [datetime]::UtcNow.ToString('o')
    events = $events
}
$bytes = [Text.Encoding]::UTF8.GetBytes((ConvertTo-Json -InputObject $snapshot -Depth 6 -Compress))
$digest = [Security.Cryptography.SHA256]::HashData($bytes)
$checksum = [Convert]::ToBase64String($digest)
$objectHost = "objectstorage.$($source.region).oraclecloud.com"
$path = "/n/$namespace/b/$Bucket/o/latest.json"
$date = [datetime]::UtcNow.ToString('R', [cultureinfo]::InvariantCulture)
$contentType = 'application/json'
$signed = "(request-target): put $path`nhost: $objectHost`ndate: $date`nx-content-sha256: $checksum`ncontent-type: $contentType`ncontent-length: $($bytes.Length)"
$keyId = "$($source.tenancy)/$($source.user)/$($source.fingerprint)"
$rsa = [Security.Cryptography.RSA]::Create()
try {
    $rsa.ImportFromPem([string]$source.privateKey)
    $signature = [Convert]::ToBase64String($rsa.SignData(
        [Text.Encoding]::UTF8.GetBytes($signed),
        [Security.Cryptography.HashAlgorithmName]::SHA256,
        [Security.Cryptography.RSASignaturePadding]::Pkcs1
    ))
} finally { $rsa.Dispose() }

$authorization = 'Signature version="1",keyId="{0}",algorithm="rsa-sha256",headers="(request-target) host date x-content-sha256 content-type content-length",signature="{1}"' -f $keyId, $signature
$response = Invoke-WebRequest -Method Put -Uri "https://$objectHost$path" -Headers @{
    Authorization = $authorization
    Date = $date
    'x-content-sha256' = $checksum
} -ContentType $contentType -Body $bytes -TimeoutSec 60
Write-Output "AZURE_LOG_EXPORT count=$($events.Count) object=latest.json http=$($response.StatusCode) sha256=$([Convert]::ToHexString($digest).ToLowerInvariant())"
