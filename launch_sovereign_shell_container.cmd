@echo off
REM Sovereign shell — container must be up (launch_mag_container.cmd).
setlocal
cd /d "%~dp0"

call "%~dp0launch_mag_container.cmd"
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%

start "" "http://127.0.0.1:8765/shell"
exit /b 0
