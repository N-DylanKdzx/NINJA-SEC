function Invoke-NinjaSecReplayStep {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][scriptblock]$Action,
        [Parameter(Mandatory)][string]$Evidence,
        [switch]$AllowRetry,
        [ValidateRange(1, 600)][int]$RetryWindowSeconds = 300
    )

    # Keep the same Terraform state and credentials only during a short,
    # interactive recovery window. The caller still owns guarded cleanup.
    $deadline = $null
    while ($true) {
        try {
            & $Action
            Add-Content -Encoding UTF8 -LiteralPath $Evidence -Value "M105_STEP_VERIFIED $Name"
            Write-Host "M105_STEP_VERIFIED $Name"
            return
        } catch {
            $failure = $_
            Add-Content -Encoding UTF8 -LiteralPath $Evidence -Value "M105_STEP_FAILED $Name $($failure.Exception.Message)"
            if (!$AllowRetry -or [Console]::IsInputRedirected) { throw $failure }
            if ($null -eq $deadline) {
                $deadline = [DateTime]::UtcNow.AddSeconds($RetryWindowSeconds)
            }
            Write-Host "Error en $Name. Pulsa R para reintentar este paso o Q para limpiar el ensayo."
            $retry = $false
            while ([DateTime]::UtcNow -lt $deadline) {
                if ([Console]::KeyAvailable) {
                    $key = [Console]::ReadKey($true).Key
                    if ($key -eq [ConsoleKey]::Q) { throw $failure }
                    if ($key -eq [ConsoleKey]::R) {
                        $retry = $true
                        break
                    }
                }
                Start-Sleep -Milliseconds 300
            }
            if (!$retry) { throw $failure }
        }
    }
}
