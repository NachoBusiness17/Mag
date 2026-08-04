@echo off
setlocal
cd /d "%~dp0"
REM Phase 1 body-green verification — run after Start Everything

set "PY=%~dp0.venv\Scripts\python.exe"
set "FAIL=0"

echo.
echo === Phase 1 verify ===
echo.

echo [1/4] multi-smoke...
"%PY%" main.py multi-smoke > "%TEMP%\mag_smoke.json" 2>&1
findstr /C:"\"ok\": true" "%TEMP%\mag_smoke.json" >nul || set "FAIL=1"
findstr /C:"dual_local" "%TEMP%\mag_smoke.json"
if %FAIL% equ 1 (
  echo [FAIL] multi-smoke
) else (
  echo [OK] multi-smoke
)

echo.
echo [2/4] catch-up (live board)...
"%PY%" main.py catch-up > "%TEMP%\mag_catchup.json" 2>&1
findstr /C:"live_stale\": false" "%TEMP%\mag_catchup.json" >nul && echo [OK] live_stale=false || echo [WARN] live_stale still true — run python main.py lab for integral watcher

echo.
echo [3/4] nervous...
"%PY%" main.py nervous

echo.
echo [4/4] orchestrator queue smoke (optional — queues doctor goal)...
if "%~1"=="--with-drain" (
  "%PY%" main.py orchestrator queue add "Run python main.py doctor; report status only" --provider deepseek --tag phase1
  "%PY%" main.py orchestrator drain --once
  "%PY%" main.py orchestrator queue status
) else (
  echo   Skip drain — pass --with-drain to queue+spawn one task
)

echo.
echo Done. Hard refresh http://127.0.0.1:8765 Ctrl+Shift+R
exit /b %FAIL%
