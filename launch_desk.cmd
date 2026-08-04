@echo off
REM One double-click: .env + drainer + backend + mag lab + DeepSeek agent.
REM Same as your two-window setup, automated.
setlocal
cd /d "%~dp0"
title Mag Desk
color 0B

set "PY=%~dp0.venv\Scripts\python.exe"
set "PYW=%~dp0.venv\Scripts\pythonw.exe"
if not exist "%PY%" (
  echo Missing venv. Run: scripts\ensure_venv.ps1
  pause
  exit /b 1
)

echo ============================================================
echo   MAG DESK - launch everything you use daily
echo   backend :8000  ^|  lab :8765  ^|  DeepSeek agent
echo ============================================================
echo.

REM Load .env + enable drainer when MAG_DRAINER=1 in .env (runs: mag autorun)
"%PY%" -c "from models.env_load import load_dotenv; load_dotenv(); import os; from mag.preferences import set_drainer; set_drainer(os.getenv('MAG_DRAINER','0').strip().lower() in ('1','true','yes'))" 2>nul

echo [1/3] Tool backend...
call "%~dp0ensure_backend.cmd"
if %ERRORLEVEL% neq 0 (
  echo [ERROR] backend did not start. See logs.
  pause
  exit /b 1
)

echo [2/3] Mag lab (watch + companion + dashboard)...
"%PY%" -c "from mag.runtime import read_heartbeat; import sys; h=read_heartbeat(); sys.exit(0 if h.get('alive') else 1)" >nul 2>&1
if %ERRORLEVEL% equ 0 (
  echo       Already running.
) else (
  start "Mag lab" /min cmd /k "cd /d "%~dp0" && mag.cmd lab"
  echo       Started minimized window "Mag lab" — leave it open.
  ping -n 8 127.0.0.1 >nul
)

echo [3/3] DeepSeek agent seat...
set "MAG_INTEGRAL_LAB=1"
call "%~dp0launch_agent.cmd" %*

echo.
echo ============================================================
echo   Desk is up.
echo   Dashboard: http://127.0.0.1:8765/
echo   Agent:     type goals in the agent window (not !pause)
echo   Stop lab:  close "Mag lab" window or Ctrl+C there
echo ============================================================
echo.
endlocal
