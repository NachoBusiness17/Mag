@echo off
cd /d C:\Users\foste\Documents\projects\local_sovereign_agent
title MAG dashboard :8765
:loop
echo [%date% %time%] starting dashboard...
".venv\Scripts\python.exe" main.py dashboard --host 127.0.0.1 --port 8765
echo [%date% %time%] exited %ERRORLEVEL% - restart 2s
timeout /t 2 /nobreak >nul
goto loop