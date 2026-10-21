@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
powershell.exe -NoProfile -File "%~dp0run-scheduled.ps1"
set "SIGNIN_EXIT=%ERRORLEVEL%"
type "cookie\logs\last-run.log"
pause
exit /b %SIGNIN_EXIT%
