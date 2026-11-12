param([string] $UtcDay = [datetime]::UtcNow.AddDays(-1).ToString('yyyy-MM-dd'))

$ErrorActionPreference = 'Stop'
$day = [datetime]::ParseExact($UtcDay, 'yyyy-MM-dd', [cultureinfo]::InvariantCulture)
$start = $day.ToString('yyyy-MM-ddT00:00:00Z')
$end = $day.AddDays(1).ToString('yyyy-MM-ddT00:00:00Z')
$source = Get-AutomationVariable -Name 'OciAuditReader' | ConvertFrom-Json
$target = Get-AutomationVariable -Name 'OciAuditDestination' | ConvertFrom-Json

function Get-ManagedIdentityToken([string] $Resource) {
    $uri = $env:IDENTITY_ENDPOINT + '?resource=' + [uri]::EscapeDataString($Resource)
    (Invoke-RestMethod -Uri $uri -Headers @{
        Metadata = 'true'
        'X-IDENTITY-HEADER' = $env:IDENTITY_HEADER
    } -TimeoutSec 30).access_token
}

$auditHost = "audit.$($source.region).oraclecloud.com"
$keyId = "$($source.tenancy)/$($source.user)/$($source.fingerprint)"
$compartment = [uri]::EscapeDataString($source.tenancy)
$basePath = "/20190901/auditEvents?compartmentId=$compartment&startTime=$([uri]::EscapeDataString($start))&endTime=$([uri]::EscapeDataString($end))"
$records = [Collections.Generic.Dictionary[string,object]]::new()
$page = $null
$rsa = [Security.Cryptography.RSA]::Create()
try {
    $rsa.ImportFromPem([string]$source.privateKey)
    do {
        $path = $basePath
        if ($page) { $path += '&page=' + [uri]::EscapeDataString($page) }
        $date = [datetime]::UtcNow.ToString('R', [cultureinfo]::InvariantCulture)
        $signed = "(request-target): get $path`nhost: $auditHost`ndate: $date"
        $signature = [Convert]::ToBase64String($rsa.SignData(
            [Text.Encoding]::UTF8.GetBytes($signed),
            [Security.Cryptography.HashAlgorithmName]::SHA256,
            [Security.Cryptography.RSASignaturePadding]::Pkcs1
        ))
        $authorization = 'Signature version="1",keyId="{0}",algorithm="rsa-sha256",headers="(request-target) host date",signature="{1}"' -f $keyId, $signature
        $response = Invoke-WebRequest -Uri "https://$auditHost$path" -Headers @{
            Authorization = $authorization
            Date = $date
        } -TimeoutSec 60
        foreach ($event in ($response.Content | ConvertFrom-Json)) {
            if (!$event.eventId) { throw 'OCI returned an audit event without an event ID.' }
            $records[[string]$event.eventId] = [ordered]@{
                TimeGenerated = $event.eventTime
                EventId = [string]$event.eventId
                EventName = [string]$event.data.eventName
                Region = [string]$source.region
                ResourceId = [string]$event.data.resourceId
                ResponseStatus = [string]$event.data.response.status
            }
        }
        $page = [string]($response.Headers['opc-next-page'] | Select-Object -First 1)
    } while ($page)
} finally { $rsa.Dispose() }

$events = @($records.Values | Sort-Object EventId)
$json = ConvertTo-Json -InputObject $events -Depth 8 -Compress
$bytes = [Text.Encoding]::UTF8.GetBytes($json)
$sha = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()
$name = "oci-audit-$UtcDay-$sha.json"
$storageToken = Get-ManagedIdentityToken 'https://storage.azure.com/'
$archive = Invoke-WebRequest -Method Put -Uri "$($target.container)/$name" -Headers @{
    Authorization = "Bearer $storageToken"
    'x-ms-version' = '2023-11-03'
    'x-ms-blob-type' = 'BlockBlob'
    'If-None-Match' = '*'
} -ContentType 'application/json' -Body $bytes -TimeoutSec 60 -SkipHttpErrorCheck
$archiveCode = [string]($archive.Headers['x-ms-error-code'] | Select-Object -First 1)
if ($archive.StatusCode -ne 201 -and $archiveCode -notin @('BlobAlreadyExists', 'ConditionNotMet')) {
    throw "Blob archive failed with HTTP $($archive.StatusCode), $archiveCode."
}

if ($events.Count -gt 0) {
    $monitorToken = Get-ManagedIdentityToken 'https://monitor.azure.com/'
    for ($offset = 0; $offset -lt $events.Count; $offset += 250) {
        $last = [Math]::Min($events.Count - 1, $offset + 249)
        $batch = ConvertTo-Json -InputObject @($events[$offset..$last]) -Depth 8 -Compress
        $result = Invoke-WebRequest -Uri $target.ingestion -Method Post -Headers @{
            Authorization = "Bearer $monitorToken"
        } -ContentType 'application/json' -Body ([Text.Encoding]::UTF8.GetBytes($batch)) -TimeoutSec 60
        if ($result.StatusCode -ne 204) { throw "Log ingestion returned HTTP $($result.StatusCode)." }
    }
}

Write-Output "OCI_AUDIT day=$UtcDay count=$($events.Count) blob=$name sha256=$sha storageHttp=$($archive.StatusCode)"
