@echo off
cd /d C:\Users\foste\Documents\projects\local_sovereign_agent
title MAG Tripartite supervisor (Engine + Scribe + Dashboard)
:loop
echo [%date% %time%] launching Tripartite supervisor...
echo   roles: Engineer (MAG_ENGINE_CMD, optional) / Scribe (synthesis_agent.py) / Dashboard (:8765) / Drainer (task queue auto-advance)
".venv\Scripts\python.exe" mag_launch.py
echo [%date% %time%] supervisor exited %ERRORLEVEL% - restart 3s
timeout /t 3 /nobreak >nul
goto loop