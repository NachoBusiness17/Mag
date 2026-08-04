@echo off
setlocal
cd /d "%~dp0"
title MAG - Start Everything
color 0A

if /I "%~1"=="--no-mirror" set MAG_NO_MIRROR=1

set "PY=%~dp0.venv\Scripts\python.exe"
set "PYW=%~dp0.venv\Scripts\pythonw.exe"
if not exist "%PY%" (
  echo [ERROR] Missing venv python at %PY%
  echo Run: powershell -ExecutionPolicy Bypass -File "%~dp0scripts\ensure_venv.ps1"
  pause
  exit /b 1
)

echo ============================================================
echo   MAG - Start Everything
echo   Backend :8000  ^|  Dashboard :8765  ^|  Mirror :8743
echo   One self-healing supervisor. Drainer toggle on Status tab.
echo ============================================================
echo.

REM ---- 1. Start the one supervisor (skip if stack already healthy) ----
"%PY%" -c "import urllib.request,sys; urls=('http://127.0.0.1:8000/health','http://127.0.0.1:8765/'); sys.exit(0 if all(urllib.request.urlopen(u,timeout=2).status==200 for u in urls) else 1)" >nul 2>&1
if %ERRORLEVEL% equ 0 (
  echo [1/4] MAG core already running — skipping supervisor start.
  goto wait_services
)
echo [1/4] Starting MAG supervisor (backend + dashboard + mirror + scribe)...
"%PY%" "%~dp0mag_launch.py" --once >nul 2>&1
start "" /min "%PYW%" "%~dp0mag_launch.py"

REM ---- 2. Wait for core services ----
echo [2/4] Waiting for backend and dashboard...
set /a tries=0
:wait_services
"%PY%" -c "import urllib.request,sys; urls=('http://127.0.0.1:8000/health','http://127.0.0.1:8765/'); sys.exit(0 if all(urllib.request.urlopen(u,timeout=2).status==200 for u in urls) else 1)" >nul 2>&1
if %ERRORLEVEL% equ 0 goto services_up
set /a tries+=1
if %tries% geq 60 (
  echo [ERROR] MAG did not start within 60 seconds. See logs\backend_sv.err.log and logs\dashboard_sv.err.log.
  pause
  exit /b 1
)
<nul set /p=.
timeout /t 1 /nobreak >nul
goto wait_services
:services_up
echo       Backend and dashboard are up.

REM ---- 3. Wait for Mirror desk (optional) ----
if defined MAG_NO_MIRROR (
  echo [3/4] Mirror skipped (MAG_NO_MIRROR=1).
  goto open_browsers
)
echo [3/4] Waiting for Mirror desk :8743 (optional)...
set /a mtries=0
:wait_mirror
"%PY%" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8743/',timeout=2)" >nul 2>&1
if %ERRORLEVEL% equ 0 goto mirror_up
set /a mtries+=1
if %mtries% geq 25 (
  echo       Mirror not up yet — Mag still works; check logs\mirror_sv.err.log
  goto open_browsers
)
timeout /t 1 /nobreak >nul
goto wait_mirror
:mirror_up
echo       Mirror desk is up.

:open_browsers
echo.
echo [4/4] Opening desks in browser...
start "" http://127.0.0.1:8765
if not defined MAG_NO_MIRROR start "" http://127.0.0.1:8743/

echo.
echo ============================================================
echo   Services launched (detached, self-healing):
echo     - Backend :8000
echo     - Dashboard :8765 (Mag home)
echo     - Mirror :8743 (strike desk, if scaffold found)
echo     - Scribe (running commentary)
echo   Drainer: Status tab toggle (or MAG_DRAINER=1)
echo   Sovereign Shell: http://127.0.0.1:8765/shell
echo   Cursor seat: launch_cursor_seat.cmd
echo   Close this window - services keep running.
echo ============================================================
echo.
pause
endlocal
