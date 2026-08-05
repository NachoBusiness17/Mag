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
echo   MAG - Stop Everything (kill switch)
echo   Stops supervisor, backend, dashboard, workers, seat-guard
echo ============================================================
echo.

"%PY%" "%~dp0main.py" power stop
echo.
echo Done. Ports 8000, 8765, and 8743 should be free.
echo Run "mag_on.cmd" or "start_everything.cmd" to bring the stack back.
echo.
pause
endlocal
