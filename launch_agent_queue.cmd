@echo off
setlocal
cd /d "%~dp0"
REM Queue one goal — restful one-shot, NOT interactive REPL
set "PY=%~dp0.venv\Scripts\python.exe"
if "%~1"=="" (
  echo Usage: launch_agent_queue.cmd "goal text"
  echo Prefer this over launch_agent.cmd for background / improve work.
  exit /b 2
)
call "%~dp0ensure_services.cmd"
"%PY%" watch\cursor_bridge.py task "%*" --mode queue --seat cursor
exit /b %ERRORLEVEL%
