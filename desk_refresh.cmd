@echo off
setlocal
cd /d "%~dp0"
title MAG Desk Reload
echo.
echo  MAG desk reload — restart lab + refresh local seat
echo  (only kills :8765 listener; your other python windows stay up)
echo.
"%~dp0.venv\Scripts\python.exe" "%~dp0main.py" desk reload --json
echo.
echo  Browser: Ctrl+Shift+R on http://127.0.0.1:8765
echo.
pause
