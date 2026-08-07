@echo off
REM Backend :8000 only — agent tools. Does not start dashboard (use mag.cmd lab for :8765).
setlocal
cd /d "%~dp0"
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" exit /b 1

"%PY%" -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=2).status==200 else 1)" >nul 2>&1
if %ERRORLEVEL% equ 0 (
  echo   [ok] backend :8000
  exit /b 0
)

echo   Starting backend :8000...
start "" /min "%PY%" -m backend.server
set /a n=0
:wait_be
"%PY%" -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=2).status==200 else 1)" >nul 2>&1
if %ERRORLEVEL% equ 0 goto be_up
set /a n+=1
if %n% geq 45 exit /b 1
timeout /t 1 /nobreak >nul
goto wait_be
:be_up
echo   [ok] backend :8000
exit /b 0
