@echo off
REM Mag container launcher — preferred entry (not host-native mag_launch).
REM Agent tools and subprocesses stay inside Docker; host gets localhost ports only.
setlocal
cd /d "%~dp0"

where docker >nul 2>&1
if %ERRORLEVEL% neq 0 (
  echo [ERROR] Docker not found. Install Docker Desktop, then re-run.
  echo         See docs\CONTAINER.md
  pause
  exit /b 1
)

if not exist ".env" (
  if exist ".env.example" (
    copy /Y ".env.example" ".env" >nul
    echo Created .env from .env.example — fill API keys before agent chat.
  )
)

echo.
echo   Mag container — starting cage (backend :8000, dashboard :8765)
echo   Boundary: memory/, watch/, logs/, state/, queue/ mounted from this folder.
echo.

docker compose up -d --build
if %ERRORLEVEL% neq 0 (
  echo [ERROR] docker compose up failed. See docs\CONTAINER.md
  pause
  exit /b 1
)

set /a n=0
:wait_up
docker compose exec -T mag python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/v1/health', timeout=2)" >nul 2>&1
if %ERRORLEVEL% equ 0 goto open_ui
set /a n+=1
if %n% geq 90 (
  echo [ERROR] dashboard did not become healthy in 90s. Check: docker compose logs mag
  pause
  exit /b 1
)
timeout /t 1 /nobreak >nul
goto wait_up

:open_ui
echo   [ok] http://127.0.0.1:8765/
start "" "http://127.0.0.1:8765/"
exit /b 0
