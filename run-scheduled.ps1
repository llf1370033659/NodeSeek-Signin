$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$taskRoot = $PSScriptRoot
$taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
$taskScript = Join-Path $taskRoot 'auto_signin.py'
$taskLogs = Join-Path $taskRoot 'cookie\logs'
New-Item -ItemType Directory -Path $taskLogs -Force | Out-Null
$taskProcess = Start-Process -FilePath $taskPython -ArgumentList @('-u', ('"' + $taskScript + '"')) -WorkingDirectory $taskRoot -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput (Join-Path $taskLogs 'last-run.log') -RedirectStandardError (Join-Path $taskLogs 'last-error.log')
exit $taskProcess.ExitCode
