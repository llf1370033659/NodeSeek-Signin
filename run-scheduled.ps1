param([switch]$TestFailureNotification, [switch]$ForceLogin)

$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$taskRoot = $PSScriptRoot
$taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
$taskScript = Join-Path $taskRoot 'auto_signin.py'
$taskLogs = Join-Path $taskRoot 'cookie\logs'
New-Item -ItemType Directory -Path $taskLogs -Force | Out-Null
$taskPrefix = if ($TestFailureNotification) { 'test' } else { 'last' }
$taskOutput = Join-Path $taskLogs ($taskPrefix + '-run.log')
$taskError = Join-Path $taskLogs ($taskPrefix + '-error.log')
$taskNotifyLog = Join-Path $taskLogs ($taskPrefix + '-notification.log')
$taskCode = 1
$taskTimedOut = $false
$taskStartedAt = [DateTimeOffset]::Now.ToString('o')

try {
    if ($TestFailureNotification) {
        Set-Content -LiteralPath $taskOutput -Value 'Simulated failure to test notification; sign-in was not run.' -Encoding UTF8
        Set-Content -LiteralPath $taskError -Value '' -Encoding UTF8
        $taskCode = 2
    } else {
        $taskArguments = @('-u', ('"' + $taskScript + '"'))
        if ($ForceLogin) { $taskArguments += '--force-login' }
        $taskProcess = Start-Process -FilePath $taskPython -ArgumentList $taskArguments -WorkingDirectory $taskRoot -WindowStyle Hidden -RedirectStandardOutput $taskOutput -RedirectStandardError $taskError -PassThru
        # Retain the handle before a fast child exits (Windows PowerShell 5.1).
        $taskProcessHandle = $taskProcess.Handle
        if (-not $taskProcess.WaitForExit(600000)) {
            $taskTimedOut = $true
            & "$env:SystemRoot\System32\taskkill.exe" /PID $taskProcess.Id /T /F | Out-Null
            $taskCode = 124
        } else {
            $taskProcess.WaitForExit()
            $taskCode = $taskProcess.ExitCode
            if ($null -eq $taskCode) { throw 'Could not read child exit code' }
        }
    }
} catch {
    Set-Content -LiteralPath $taskError -Value ('Runner failed: ' + $_.Exception.GetType().Name) -Encoding UTF8
    $taskCode = 1
}

$taskMailStatus = 'not_needed'
if ($taskCode -ne 0) {
    try {
        $taskMailArguments = @((Join-Path $taskRoot 'send-notification.py'), '--exit-code', [string]$taskCode)
        if ($TestFailureNotification) { $taskMailArguments += '--test' }
        if ($taskTimedOut) { $taskMailArguments += '--timed-out' }
        & $taskPython @taskMailArguments *> $taskNotifyLog
        $taskMailStatus = if ($LASTEXITCODE -eq 0) { 'sent' } else { 'failed' }
    } catch {
        Set-Content -LiteralPath $taskNotifyLog -Value ('Notification runner failed: ' + $_.Exception.GetType().Name) -Encoding UTF8
        $taskMailStatus = 'failed'
    }
} else {
    Set-Content -LiteralPath $taskNotifyLog -Value 'Successful sign-in; no notification needed.' -Encoding UTF8
}

[pscustomobject]@{
    StartedAt = $taskStartedAt
    FinishedAt = [DateTimeOffset]::Now.ToString('o')
    ExitCode = $taskCode
    TimedOut = $taskTimedOut
    Notification = $taskMailStatus
    Test = [bool]$TestFailureNotification
    ForceLogin = [bool]$ForceLogin
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskLogs ($taskPrefix + '-result.json')) -Encoding UTF8
Write-Output ('NodeSeek result: ' + $taskCode + '; notification: ' + $taskMailStatus)
exit $taskCode
