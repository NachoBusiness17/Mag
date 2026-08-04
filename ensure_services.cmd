@echo off
REM ensure_services.cmd - Ensure backend (:8000) and dashboard (:8765) are up.
REM Does NOT spawn a new supervisor when services are already healthy.
setlocal
cd /d "%~dp0"
set "PY=%~dp0.venv\Scripts\python.exe"
set "PYW=%~dp0.venv\Scripts\pythonw.exe"
if not exist "%PY%" (
  echo [ERROR] Missing venv python at "%PY%"
  exit /b 1
)

"%PY%" -c "import urllib.request,sys; urls=('http://127.0.0.1:8000/health','http://127.0.0.1:8765/'); sys.exit(0 if all(urllib.request.urlopen(u,timeout=2).status==200 for u in urls) else 1)" >nul 2>&1
if %ERRORLEVEL% equ 0 goto services_up

echo   Starting MAG services...
"%PY%" "%~dp0mag_launch.py" --once >nul 2>&1
if %ERRORLEVEL% neq 0 (
  echo   [ERROR] mag_launch --once failed. See logs\mag_launch.log
  exit /b 1
)

"%PY%" -c "import json,sys; from pathlib import Path; import mag_launch as m; p=Path('state/mag_launch.json'); d=json.loads(p.read_text()) if p.is_file() else {}; sup=int(d.get('supervisor_pid') or 0); sys.exit(0 if sup and m._pid_alive(sup) and m._is_supervisor_pid(sup) else 1)" >nul 2>&1
if %ERRORLEVEL% neq 0 (
  start "" /min "%PYW%" "%~dp0mag_launch.py"
)

set /a n=0
:wait_services
"%PY%" -c "import urllib.request,sys; urls=('http://127.0.0.1:8000/health','http://127.0.0.1:8765/'); sys.exit(0 if all(urllib.request.urlopen(u,timeout=2).status==200 for u in urls) else 1)" >nul 2>&1
if %ERRORLEVEL% equ 0 goto services_up
set /a n+=1
if %n% geq 60 (
  echo   [ERROR] services did not start in 60s. Check logs\backend_sv.err.log and logs\dashboard_sv.err.log
  exit /b 1
)
<nul set /p=.
timeout /t 1 /nobreak >nul
goto wait_services

:services_up
echo   [ok] backend :8000 and dashboard :8765 up
endlocal
exit /b 0
