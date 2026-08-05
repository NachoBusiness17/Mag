@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0\.."
title Mag v3 DeepSeek code run
color 0B

set "PY=%~dp0..\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
set "FAIL=0"

echo.
echo === Mag v3 DeepSeek code run ===
echo Seat law: DeepSeek = build/drain · Grok = [priority] plan only · Ollama = scut
echo.

REM --- 0. Keys ---
if "%DEEPSEEK_API_KEY%"=="" (
  if exist "%~dp0..\.env" (
    for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0..\.env") do (
      if /i "%%a"=="DEEPSEEK_API_KEY" set "DEEPSEEK_API_KEY=%%b"
    )
  )
)
if "%DEEPSEEK_API_KEY%"=="" (
  echo [FAIL] DEEPSEEK_API_KEY not set — copy .env.example to .env
  exit /b 1
)
echo [OK] DeepSeek key present

REM --- 1. v2 ritual (requires merged stack on branch) ---
echo.
echo [1/7] doctor...
"%PY%" main.py doctor >nul 2>&1 || set "FAIL=1"

echo [2/7] routing smoke...
"%PY%" scripts\routing_smoke.py >nul 2>&1 || set "FAIL=1"

echo [3/7] v3-status...
"%PY%" main.py v3-status >nul 2>&1 || set "FAIL=1"

REM --- 2. Boot stack ---
echo [4/7] power start...
"%PY%" main.py power start --json > "%TEMP%\mag_ds_start.json" 2>&1
findstr /C:"\"ok\": true" "%TEMP%\mag_ds_start.json" >nul || set "FAIL=1"

REM --- 3. Register Cursor peer ---
echo [5/7] seat register...
"%PY%" main.py seats register --seat cursor --goal "v3 deepseek run" --json > "%TEMP%\mag_ds_seat.json" 2>&1

REM --- 4. Queue + drain one DeepSeek goal ---
set "GOAL=%*"
if "%GOAL%"=="" set "GOAL=[build] v3 wiring smoke — list queue/todo.md open items and file summary to memory/working.md"

echo [6/7] queue + drain (DeepSeek)...
echo   Goal: %GOAL%
"%PY%" main.py orchestrator queue add "%GOAL%" --provider deepseek --tag v3-deepseek-run
"%PY%" main.py orchestrator drain --once --json > "%TEMP%\mag_ds_drain.json" 2>&1
findstr /C:"task_id" "%TEMP%\mag_ds_drain.json" >nul || set "FAIL=1"

echo [7/7] improve-loop + spider...
"%PY%" main.py improve-loop cycle --json > "%TEMP%\mag_ds_il.json" 2>&1
"%PY%" main.py spider --once >nul 2>&1
"%PY%" main.py training-events --stats

echo.
if %FAIL% equ 0 (
  echo [PASS] v3 DeepSeek run started — watch: mag.cmd watch
  echo   Drain again: %PY% main.py orchestrator drain --once
  echo   Kill stack:  mag_kill.cmd
) else (
  echo [FAIL] see output — docs/ref/V3_DEEPSEEK_RUN.md
)
exit /b %FAIL%
