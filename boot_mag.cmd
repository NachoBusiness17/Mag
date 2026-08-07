@echo off
REM Full-stack Mag boot — silent (Windows Startup / auto).
REM Supervisor: backend :8000 + dashboard :8765 + integral lab + scribe (+ mirror if set)
REM Opens Direct Mag: http://127.0.0.1:8765/?tab=chat
setlocal
cd /d "%~dp0"

set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [MAG boot] Missing venv python at %PY%
  exit /b 1
)

REM Already healthy? just open face
"%PY%" -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8765/',timeout=2).status==200 else 1)" >nul 2>&1
if %ERRORLEVEL% equ 0 (
  start "" "http://127.0.0.1:8765/?tab=chat"
  exit /b 0
)

"%PY%" "%~dp0main.py" power start --browser
exit /b %ERRORLEVEL%
