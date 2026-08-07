@echo off
setlocal
cd /d "%~dp0"
title MAG Desktop — Turn On + Cursor Seat
color 0B

echo ============================================================
echo   MAG DESKTOP — one switch to working state
echo   1) Turn on stack (backend + dashboard)
echo   2) Register Cursor seat (if lab up)
echo   3) Open dashboard Body tab for status
echo ============================================================
echo.

call "%~dp0mag_on.cmd"
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%

set "PY=%~dp0.venv\Scripts\python.exe"
echo.
echo Registering Cursor seat with orchestrator...
"%PY%" watch\cursor_session_boot.py 2>nul
"%PY%" watch\cursor_bridge.py register "Desktop session" 2>nul

echo.
echo Hooks: run scripts\install_cursor_hooks.cmd once (copies configs/cursor → .cursor)
echo Improve: python watch/cursor_bridge.py improve --claim "..." --enqueue
echo Exit:    mag_kill.cmd
echo.
endlocal
