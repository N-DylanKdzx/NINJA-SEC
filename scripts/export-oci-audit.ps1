[CmdletBinding()]
param(
    [Parameter(Mandatory)][string] $CompartmentId,
    [Parameter(Mandatory)][datetimeoffset] $StartTime,
    [Parameter(Mandatory)][datetimeoffset] $EndTime,
    [Parameter(Mandatory)][string] $OutputPath,
    [string] $Profile,
    [string] $OciExecutable = 'oci',
    [string[]] $OciArguments = @()
)

$ErrorActionPreference = 'Stop'
if ($StartTime -ge $EndTime -or ($EndTime - $StartTime).TotalHours -gt 24) {
    throw 'Select a positive interval of at most 24 hours.'
}

$arguments = $OciArguments + @(
    'audit', 'event', 'list', '--all', '--output', 'json',
    '--compartment-id', $CompartmentId,
    '--start-time', $StartTime.UtcDateTime.ToString('yyyy-MM-ddTHH:mm:ssZ'),
    '--end-time', $EndTime.UtcDateTime.ToString('yyyy-MM-ddTHH:mm:ssZ')
)
if ($Profile) { $arguments += @('--profile', $Profile) }

$result = & $OciExecutable @arguments
if ($LASTEXITCODE -ne 0) { throw "OCI CLI exited with code $LASTEXITCODE." }
$events = ($result -join "`n" | ConvertFrom-Json).data
if ($null -eq $events) { throw 'OCI CLI response has no data array.' }

$destination = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputPath)
$temporary = "$destination.$([guid]::NewGuid()).tmp"
try {
    [IO.File]::WriteAllText($temporary, ($result -join "`n"), [Text.UTF8Encoding]::new($false))
    [IO.File]::Move($temporary, $destination)
} finally {
    if ([IO.File]::Exists($temporary)) { [IO.File]::Delete($temporary) }
}

[pscustomobject]@{
    Count = @($events).Count
    Sha256 = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
    Path = $destination
}
