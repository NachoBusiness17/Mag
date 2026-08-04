@echo off
setlocal
cd /d "%~dp0"
REM Queue goals for DeepSeek orchestrator drain. Set MAG_DRAINER=1 before Start Everything for auto-run.

set "PY=%~dp0.venv\Scripts\python.exe"
set "GOAL=%*"
if "%GOAL%"=="" (
  echo Usage: queue_deepseek.cmd "your goal here"
  echo.
  echo Examples:
  echo   queue_deepseek.cmd "Run doctor and fix degraded health"
  echo   queue_deepseek.cmd "Improve scout --once and file residual"
  exit /b 1
)

call "%~dp0ensure_services.cmd" >nul 2>&1
"%PY%" main.py orchestrator queue add "%GOAL%" --provider deepseek --tag cursor-queued
echo.
echo Queued. Drain once:
echo   %PY% main.py orchestrator drain --once
echo.
echo Auto-drain: set MAG_DRAINER=1 then restart Start Everything.
exit /b 0
