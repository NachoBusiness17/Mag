@echo off
setlocal
cd /d "%~dp0\.."
title Mag v3 home smoke
color 0E

set "PY=%~dp0..\.venv\Scripts\python.exe"
set "FAIL=0"
if not exist "%PY%" set "PY=python"

echo.
echo === Mag v3 home smoke ===
echo.

echo [1/8] power start...
"%PY%" main.py power start --json > "%TEMP%\mag_v3_start.json" 2>&1
findstr /C:"\"ok\": true" "%TEMP%\mag_v3_start.json" >nul || set "FAIL=1"

echo [2/8] doctor...
"%PY%" main.py doctor >nul 2>&1 || set "FAIL=1"

echo [3/8] power status...
"%PY%" main.py power status

echo [4/8] seat register...
"%PY%" main.py seats register --seat cursor --goal "v3 smoke" --json > "%TEMP%\mag_v3_seat.json" 2>&1
findstr /C:"ext-" "%TEMP%\mag_v3_seat.json" >nul || set "FAIL=1"

echo [5/8] switchboard peers...
"%PY%" main.py switchboard peers --live >nul 2>&1 || set "FAIL=1"

echo [6/8] improve-loop cycle...
"%PY%" main.py improve-loop cycle --json > "%TEMP%\mag_v3_il.json" 2>&1
findstr /C:"improve_loop.v1" "%TEMP%\mag_v3_il.json" >nul || set "FAIL=1"

echo [7/8] nervous + spider...
"%PY%" main.py nervous >nul 2>&1 || set "FAIL=1"
"%PY%" main.py spider --once >nul 2>&1 || set "FAIL=1"

echo [8/8] power stop (kill switch)...
"%PY%" main.py power stop --json > "%TEMP%\mag_v3_stop.json" 2>&1

echo.
if %FAIL% equ 0 (
  echo [PASS] v3 home smoke
) else (
  echo [FAIL] see output above — docs/ref/V3_HOME_SHIP_CHECKLIST.md
)
exit /b %FAIL%
