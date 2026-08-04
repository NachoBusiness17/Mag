@echo off
REM switchboard_status.cmd — is the switchboard operator LIVE?
cd /d "%~dp0"
set "PY=.venv\Scripts\python.exe"
echo === Mag switchboard status ===
"%PY%" main.py nervous
echo.
echo === Governor trail (last 3 cycles) ===
"%PY%" -c "import json,sys; lines=open(r'memory/runs/governor_trail.jsonl',encoding='utf-8').read().strip().splitlines(); [print(l[:160]) for l in lines[-3:]]" 2>nul || echo (no governor trail yet)
echo.
echo === Seat guard trail (last 3) ===
"%PY%" -c "import json; lines=open(r'memory/runs/seat_guard/seat_guard_trail.jsonl',encoding='utf-8').read().strip().splitlines(); [print(l[:160]) for l in lines[-3:]]" 2>nul || echo (no seat guard trail yet)
