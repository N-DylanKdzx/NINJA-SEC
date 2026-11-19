param([string] $TriggerProof = '')
$ErrorActionPreference = 'Stop'
$source = Get-AutomationVariable -Name 'OciAuditReader'
if ($source -is [string]) { $source = $source | ConvertFrom-Json }
$config = Get-AutomationVariable -Name 'MysqlBackupDestination'
if ($config -is [string]) { $config = $config | ConvertFrom-Json }
$rsa = [Security.Cryptography.RSA]::Create()
$temporary = Join-Path ([IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString())
[IO.Directory]::CreateDirectory($temporary) | Out-Null
try {
    $rsa.ImportFromPem([string]$source.privateKey)
    function Read-OciObject([string] $ObjectName, [string] $FileName) {
        $objectHost = "objectstorage.$($source.region).oraclecloud.com"
        $path = "/n/$($config.namespace)/b/$($config.bucket)/o/$([uri]::EscapeDataString($ObjectName))"
        $date = [datetime]::UtcNow.ToString('R', [cultureinfo]::InvariantCulture)
        $signed = "(request-target): get $path`nhost: $objectHost`ndate: $date"
        $signature = [Convert]::ToBase64String($rsa.SignData([Text.Encoding]::UTF8.GetBytes($signed),[Security.Cryptography.HashAlgorithmName]::SHA256,[Security.Cryptography.RSASignaturePadding]::Pkcs1))
        $keyId = "$($source.tenancy)/$($source.user)/$($source.fingerprint)"
        $authorization = 'Signature version="1",keyId="{0}",algorithm="rsa-sha256",headers="(request-target) host date",signature="{1}"' -f $keyId,$signature
        Invoke-WebRequest -Uri "https://$objectHost$path" -Headers @{Authorization=$authorization;Date=$date} -OutFile $FileName -TimeoutSec 90
    }
    $manifestPath = Join-Path $temporary 'manifest.json'
    Read-OciObject 'mysql/latest.json' $manifestPath
    $manifest = Get-Content -Raw $manifestPath | ConvertFrom-Json
    if ($manifest.schemaVersion -ne 1 -or $manifest.objectName -notmatch '^mysql/ninjasec-[0-9TZ]+-[a-f0-9]+\.sql\.gz$' -or $manifest.sha256 -notmatch '^[a-f0-9]{64}$') { throw 'Invalid backup manifest.' }
    if (([datetimeoffset]::UtcNow - [datetimeoffset]$manifest.createdAt).TotalHours -gt 26) { throw 'Backup manifest is stale.' }
    if ([long]$manifest.bytes -gt 100MB -or [long]$manifest.bytes -lt 1) { throw 'Backup size outside the project limit.' }
    $dumpPath = Join-Path $temporary 'backup.sql.gz'
    Read-OciObject $manifest.objectName $dumpPath
    $bytes = [IO.File]::ReadAllBytes($dumpPath)
    $sha = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()
    if ($sha -ne $manifest.sha256 -or $bytes.Length -ne [long]$manifest.bytes) { throw 'OCI backup integrity mismatch.' }
    $uri = $env:IDENTITY_ENDPOINT + '?resource=' + [uri]::EscapeDataString('https://storage.azure.com/')
    $token = (Invoke-RestMethod -Uri $uri -Headers @{Metadata='true';'X-IDENTITY-HEADER'=$env:IDENTITY_HEADER} -TimeoutSec 30).access_token
    $destination = "$($config.container)/$($manifest.objectName)"
    $response = Invoke-WebRequest -Method Put -Uri $destination -Headers @{
        Authorization="Bearer $token";'x-ms-version'='2023-11-03';'x-ms-blob-type'='BlockBlob';'If-None-Match'='*';'x-ms-meta-sha256'=$sha
    } -ContentType 'application/gzip' -Body $bytes -TimeoutSec 90 -SkipHttpErrorCheck
    $errorCode = [string]($response.Headers['x-ms-error-code'] | Select-Object -First 1)
    if ($response.StatusCode -ne 201 -and $errorCode -notin @('BlobAlreadyExists','ConditionNotMet')) { throw "Azure backup PUT failed HTTP $($response.StatusCode), $errorCode" }
    $azurePath = Join-Path $temporary 'azure.sql.gz'
    Invoke-WebRequest -Uri $destination -Headers @{Authorization="Bearer $token";'x-ms-version'='2023-11-03'} -OutFile $azurePath -TimeoutSec 90
    $azureSha = (Get-FileHash $azurePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($azureSha -ne $sha) { throw 'Azure read-back integrity mismatch.' }
    Write-Output "MYSQL_AZURE_BACKUP_OK object=$($manifest.objectName) bytes=$($bytes.Length) sha256=$sha putHttp=$($response.StatusCode) readBack=verified trigger=$TriggerProof"
} catch {
    $failure = $_
    try {
        $body = [Text.Encoding]::UTF8.GetBytes((@{title='NINJA-SEC: fallo copia MySQL a Azure';body='El job Copy-MysqlBackupToAzure fallo. Revisar Automation; no se ha confirmado una copia nueva. El respaldo OCI se conserva.'} | ConvertTo-Json -Compress))
        $endpoint = [uri]'https://cell1.notification.us-ashburn-1.oci.oraclecloud.com'
        $path = '/20181201/topics/ocid1.onstopic.oc1.iad.amaaaaaa3nxgmgaaxikr6t2szrwyitk7eicxdiuhkncemdewzhlm6qropqlq/messages'
        $date = [datetime]::UtcNow.ToString('R',[cultureinfo]::InvariantCulture)
        $checksum = [Convert]::ToBase64String([Security.Cryptography.SHA256]::HashData($body))
        $signed = "(request-target): post $path`nhost: $($endpoint.Host)`ndate: $date`nx-content-sha256: $checksum`ncontent-type: application/json`ncontent-length: $($body.Length)"
        $signature = [Convert]::ToBase64String($rsa.SignData([Text.Encoding]::UTF8.GetBytes($signed),[Security.Cryptography.HashAlgorithmName]::SHA256,[Security.Cryptography.RSASignaturePadding]::Pkcs1))
        $keyId = "$($source.tenancy)/$($source.user)/$($source.fingerprint)"
        $authorization = 'Signature version="1",keyId="{0}",algorithm="rsa-sha256",headers="(request-target) host date x-content-sha256 content-type content-length",signature="{1}"' -f $keyId,$signature
        $alert = Invoke-WebRequest -Uri "$($endpoint.AbsoluteUri.TrimEnd('/'))$path" -Method Post -Headers @{Authorization=$authorization;Date=$date;'x-content-sha256'=$checksum} -ContentType 'application/json' -Body $body -TimeoutSec 30
        Write-Output "AZURE_BACKUP_FAILURE_ALERT_PUBLISHED http=$($alert.StatusCode)"
    } catch { Write-Output 'AZURE_BACKUP_FAILURE_ALERT_FAILED: inspect Automation job errors.' }
    throw $failure
} finally {
    $rsa.Dispose()
    if ([IO.Directory]::Exists($temporary)) { [IO.Directory]::Delete($temporary,$true) }
}
