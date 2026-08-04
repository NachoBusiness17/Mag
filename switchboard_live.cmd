@echo off
REM ============================================================
REM  switchboard_live.cmd — bring the Mag switchboard operator LIVE
REM  Boots, in separate windows:
REM    1) DASHBOARD :8765  (the switchboard — FIND/FILE/LOAD cockpit)
REM    2) MAG OPERATOR     (sense->judge->act loop, interval from configs/mag.yaml)
REM    3) GUARD            (failsafe: auto-restarts lab if down)
REM  Optional 4) seat-guard run (supervised long-lived coding seat)
REM  All three are killable per-window (Ctrl+C) — reversible.
REM ============================================================
cd /d "%~dp0"
set "PY=.venv\Scripts\python.exe"

echo [switchboard] booting dashboard :8765 ...
start "MAG switchboard :8765" cmd /k "%PY% main.py dashboard --host 127.0.0.1 --port 8765"

echo [switchboard] booting mag operator loop ...
start "MAG operator loop" cmd /k "%PY% main.py mag"

echo [switchboard] booting guard failsafe ...
start "MAG guard failsafe" cmd /k "%PY% main.py guard --restart"

if /i "%~1"=="--seat" (
  echo [switchboard] booting supervised coding seat (seat-guard, deepseek) ...
  start "MAG seat guard" cmd /k "%PY% main.py seat-guard run --provider deepseek"
)

echo [switchboard] stack requested. Verify: switchboard_status.cmd
