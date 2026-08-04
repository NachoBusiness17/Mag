@echo off
setlocal
cd /d "%~dp0"
title MAG - Stop Everything
color 0C

set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [ERROR] Missing venv python at %PY%
  pause
  exit /b 1
)

echo ============================================================
echo   MAG - Stop Everything
echo   Kills supervisor, backend, dashboard, scribe, mag daemon
echo ============================================================
echo.

"%PY%" "%~dp0mag_launch.py" --stop
echo.
echo Done. Ports 8000, 8765, and 8743 should be free.
echo Run "MAG - Start Everything" to bring the stack back.
echo.
pause
endlocal
