param([string] $BlobName = '', [object] $WebhookData)
$ErrorActionPreference = 'Stop'
$target = Get-AutomationVariable -Name 'AwsAuditDestination'
if ($target -is [string]) { $target = $target | ConvertFrom-Json }
function Resolve-AwsResourceId([object] $record) {
    $ids = [Collections.Generic.List[string]]::new()
    foreach ($resource in @($record.resources)) {
        if ($resource.ARN) { $ids.Add([string]$resource.ARN) }
    }
    foreach ($part in @($record.requestParameters,$record.responseElements)) {
        foreach ($property in @('groupId','vpcId','subnetId','routeTableId','networkAclId','instanceId','resourceId','allocationId')) {
            if ($part.$property -is [string] -and $part.$property) { $ids.Add([string]$part.$property) }
        }
        foreach ($item in @($part.resourcesSet.items)) {
            if ($item.resourceId) { $ids.Add([string]$item.resourceId) }
        }
    }
    return (@($ids | Sort-Object -Unique) -join ',')
}
function Token([string]$resource) {
    (Invoke-RestMethod -Uri ($env:IDENTITY_ENDPOINT + '?resource=' + [uri]::EscapeDataString($resource)) -Headers @{Metadata='true';'X-IDENTITY-HEADER'=$env:IDENTITY_HEADER}).access_token
}
$headers = @{Authorization=('Bearer ' + (Token 'https://storage.azure.com/'));'x-ms-version'='2023-11-03'}
$monitorHeaders = @{Authorization=('Bearer ' + (Token 'https://monitor.azure.com/'))}
$delivery = $null
if ($WebhookData) {
    if ($WebhookData -is [string]) { $WebhookData = $WebhookData | ConvertFrom-Json }
    $delivery = $WebhookData.RequestBody | ConvertFrom-Json
    if ($delivery.blob -notmatch '^aws-audit-[a-f0-9]{64}\.json$') { throw 'Invalid delivery name' }
    foreach ($url in @($delivery.sourceUrl,$delivery.ackUrl)) {
        $uri = [uri]$url
        if ($uri.Scheme -ne 'https' -or $uri.Host -notmatch '^ninjasec-audit-533267256700\.s3[.-]us-east-1\.amazonaws\.com$') { throw 'Unexpected delivery endpoint' }
    }
    try { $raw = Invoke-WebRequest -Uri $delivery.sourceUrl -TimeoutSec 60 } catch {
        $status = [int]$_.Exception.Response.StatusCode
        $awsCode = 'Unknown'
        try { [xml]$failure = $_.ErrorDetails.Message; $awsCode = [string]$failure.Error.Code } catch {}
        # Do not expose the signed URL or session token in job output.
        throw "Source download failed HTTP $status AWS=$awsCode"
    }
    $rawBytes = [Text.Encoding]::UTF8.GetBytes($raw.Content)
    $rawHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($rawBytes)).ToLowerInvariant()
    if ($delivery.blob -ne "aws-audit-$rawHash.json") { throw 'Delivery hash mismatch' }
    $deliveryRecordCount = @((ConvertFrom-Json $raw.Content).Records).Count
    $uploadHeaders=$headers.Clone();$uploadHeaders['x-ms-blob-type']='BlockBlob';$uploadHeaders['If-None-Match']='*'
    $archive=Invoke-WebRequest -Uri ($target.container+'/'+$delivery.blob) -Method Put -Headers $uploadHeaders -ContentType 'application/json' -Body $rawBytes -SkipHttpErrorCheck
    $code=[string]($archive.Headers['x-ms-error-code'] | Select-Object -First 1)
    if ($archive.StatusCode -ne 201 -and $code -notin @('BlobAlreadyExists','ConditionNotMet','BlobImmutableDueToPolicy')) { throw "Archive HTTP $($archive.StatusCode) $code" }
    $BlobName=$delivery.blob
}
$names = @()
if ($BlobName) { $names = @($BlobName) } else {
    $marker = ''
    do {
        $listing = Invoke-WebRequest -Uri ($target.container + '?restype=container&comp=list&prefix=aws-audit-&marker=' + [uri]::EscapeDataString($marker)) -Headers $headers
        [xml]$xml = $listing.Content.TrimStart([char]0xFEFF)
        $names += @($xml.EnumerationResults.Blobs.Blob | ForEach-Object {$_.Name})
        $marker = [string]$xml.EnumerationResults.NextMarker
    } while ($marker)
}
$ingested = $skipped = 0
foreach ($name in $names) {
    if ($name -notmatch '^aws-audit-([a-f0-9]{64})\.json$') { throw 'Invalid batch name' }
    $expected = $Matches[1]
    $checkpoint = $target.checkpoints + '/' + $expected + '-v5.json'
    $seen = Invoke-WebRequest -Uri $checkpoint -Method Head -Headers $headers -SkipHttpErrorCheck
    if ($seen.StatusCode -eq 200) { $skipped++; continue }
    if ($seen.StatusCode -ne 404) { throw "Checkpoint read HTTP $($seen.StatusCode)" }
    $response = Invoke-WebRequest -Uri ($target.container + '/' + $name) -Headers $headers
    $bytes = [Text.Encoding]::UTF8.GetBytes($response.Content)
    $sha = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()
    if ($sha -ne $expected) { throw 'Batch SHA-256 mismatch' }
    $batch = $response.Content | ConvertFrom-Json
    if ($batch.schemaVersion -ne 1 -or !$batch.sources -or !$batch.Records) { throw 'Invalid audit batch' }
    foreach ($source in $batch.sources) { if ($source.sha256 -notmatch '^[a-f0-9]{64}$') { throw 'Missing source hash' } }
    $events = @($batch.Records | ForEach-Object {
        if (!$_.eventID) { throw 'Missing eventID' }
        [ordered]@{TimeGenerated=$_.eventTime;EventTime=$_.eventTime;OriginalEventTime=([datetimeoffset]$_.eventTime).ToUniversalTime().ToString('o');EventId=$_.eventID;EventName=$_.eventName;Region=$_.awsRegion;ResourceId=(Resolve-AwsResourceId $_);ResponseStatus=[string]$_.errorCode;SourceIp=[string]$_.sourceIPAddress;UserArn=[string]$_.userIdentity.arn;AWSAccountId=[string]$_.recipientAccountId;SourceBlob=$name}
    })
    if (@($events | ForEach-Object {$_['EventId']} | Select-Object -Unique).Count -ne $events.Count) { throw 'Duplicate event IDs in normalized batch' }
    for ($offset=0; $offset -lt $events.Count; $offset+=250) {
        $last = [Math]::Min($events.Count-1,$offset+249)
        $body = [Text.Encoding]::UTF8.GetBytes((ConvertTo-Json -InputObject @($events[$offset..$last]) -Depth 10 -Compress))
        $result = Invoke-WebRequest -Uri $target.ingestion -Method Post -Headers $monitorHeaders -ContentType 'application/json' -Body $body
        if ($result.StatusCode -ne 204) { throw 'Ingestion not acknowledged' }
    }
    $putHeaders = $headers.Clone(); $putHeaders['x-ms-blob-type']='BlockBlob'; $putHeaders['If-None-Match']='*'
    $saved = Invoke-WebRequest -Uri $checkpoint -Method Put -Headers $putHeaders -ContentType 'application/json' -Body ([Text.Encoding]::UTF8.GetBytes((@{blob=$name;events=$events.Count;completedUtc=[datetime]::UtcNow.ToString('o')} | ConvertTo-Json -Compress))) -SkipHttpErrorCheck
    if ($saved.StatusCode -notin @(201,412)) { throw "Checkpoint write HTTP $($saved.StatusCode)" }
    $ingested += $events.Count
}
Write-Output "AWS_AUDIT ingested=$ingested skipped=$skipped blobs=$($names.Count)"
if ($delivery) {
    $ack=[Text.Encoding]::UTF8.GetBytes((@{blob=$delivery.blob;sha256=$rawHash;recordCount=$deliveryRecordCount;completedUtc=[datetime]::UtcNow.ToString('o')} | ConvertTo-Json -Compress))
    try { $result=Invoke-WebRequest -Uri $delivery.ackUrl -Method Put -ContentType 'application/json' -Body $ack -TimeoutSec 60 } catch { throw 'AWS acknowledgement failed' }
    if ($result.StatusCode -ne 200) { throw 'AWS acknowledgement not saved' }
    Write-Output 'AWS_CHECKPOINT_ACK_PASS'
}
