@echo off
setlocal
cd /d "%~dp0"
title MAG - Turn On
color 0A

if /I "%~1"=="--no-mirror" set MAG_NO_MIRROR=1

set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [ERROR] Missing venv python at %PY%
  pause
  exit /b 1
)

echo ============================================================
echo   MAG TURN ON
echo   Backend :8000  ^|  Dashboard :8765  ^|  optional Mirror :8743
echo ============================================================
echo.

"%PY%" "%~dp0main.py" power start --browser
echo.
echo Dashboard: http://127.0.0.1:8765  ^(Body tab = stack status^)
echo Kill switch: mag_kill.cmd  or  mag.cmd power stop
echo.
pause
endlocal
