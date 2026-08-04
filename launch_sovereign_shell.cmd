@echo off
setlocal
cd /d "%~dp0"
REM Mag Sovereign Shell — Tier 4 editor chrome (Monaco + file tree + agent pane).

set "MAG_ROOT=%~dp0"
set "MAG_ROOT=%MAG_ROOT:~0,-1%"
set "PY=%MAG_ROOT%\.venv\Scripts\python.exe"

echo.
echo   Mag Sovereign Shell ^| Tier 4 chrome
echo   Ensuring backend + dashboard are up...
call "%~dp0ensure_services.cmd"
if %ERRORLEVEL% neq 0 (
  echo [ERROR] Could not ensure services.
  pause
  exit /b 1
)

echo.
echo   Shell: http://127.0.0.1:8765/shell
echo   Office: http://127.0.0.1:8765
echo   Cursor bridge: python watch\cursor_bridge.py delegate "goal"
echo.

start "" "http://127.0.0.1:8765/shell"
exit /b 0
