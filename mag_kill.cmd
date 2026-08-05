@echo off
setlocal
cd /d "%~dp0"
title MAG - Kill Switch
color 0C

set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [ERROR] Missing venv python at %PY%
  pause
  exit /b 1
)

echo ============================================================
echo   MAG KILL SWITCH
echo   Stops supervisor, dashboard, backend, workers, seat-guard
echo   No respawn until you run start_everything.cmd or mag_on.cmd
echo ============================================================
echo.

"%PY%" "%~dp0main.py" power stop --json
echo.
echo Done. If anything lingers: Task Manager -^> python.exe under this repo.
echo.
pause
endlocal
