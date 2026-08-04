@echo off
setlocal
cd /d "%~dp0"
where docker >nul 2>&1
if %ERRORLEVEL% neq 0 (
  echo Docker not installed.
  exit /b 1
)
docker compose down
echo Mag container stopped.
exit /b 0
