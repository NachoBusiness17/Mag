@echo off
setlocal
set "MAG_ROOT=%~dp0"
set "MAG_ROOT=%MAG_ROOT:~0,-1%"
set "URL=http://127.0.0.1:8765/"
cd /d "%MAG_ROOT%"
echo Ensuring MAG services on %URL%
call "%~dp0ensure_services.cmd"
if %ERRORLEVEL% neq 0 (
  pause
  exit /b 1
)

:open
start "" "%URL%"
endlocal
exit /b 0
