@echo off
setlocal
set "ROOT=%~dp0"
set "PY=%ROOT%.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo Missing Mag venv. Run scripts\ensure_venv.ps1
  exit /b 1
)
cd /d "%ROOT%"

echo.
echo  Mag Voice
echo  ---------
echo  Primary:  http://127.0.0.1:8766/voice   (cast)
echo  Backup:   http://127.0.0.1:8765/voice   (dashboard - if lab is up)
echo  Mode:     local first, or pipeline swarm
echo.

REM Kill stale cast on 8766 if any
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8766" ^| findstr "LISTENING"') do (
  echo Stopping old cast PID %%p
  taskkill /F /PID %%p >nul 2>&1
)

echo Starting cast on :8766 ...
start "Mag Cast Voice" /MIN "%PY%" main.py cast

timeout /t 2 /nobreak >nul
echo.
echo Open: http://127.0.0.1:8766/voice
echo Hard-refresh the tab. Start conversation. Allow mic.
echo Leave this window minimized - closing it may stop cast.
echo.
endlocal
