@echo off

setlocal EnableDelayedExpansion

set "MAG_ROOT=%~dp0"

set "MAG_ROOT=%MAG_ROOT:~0,-1%"

cd /d "%MAG_ROOT%"



echo.

echo  Mag Factory Machine — branch, sprint, retro, bead, behavioral

echo  ==============================================================

echo.



if not exist "%MAG_ROOT%\.venv\Scripts\python.exe" (

  echo [ERROR] Missing venv. Run:

  echo   powershell -ExecutionPolicy Bypass -File "%MAG_ROOT%\scripts\ensure_venv.ps1"

  echo.

  pause

  exit /b 1

)



echo [1/3] Ensuring dashboard :8765 ...

call "%MAG_ROOT%\ensure_services.cmd"

if %ERRORLEVEL% neq 0 (

  echo.

  pause

  exit /b 1

)



set "GOAL=%*"

if "!GOAL!"=="" (

  set /p GOAL=Goal for this machine run: 

)

if "!GOAL!"=="" (

  echo [ERROR] No goal — type one at the prompt or pass as argument.

  echo   Example: launch_agent_machine.cmd "wire factory audit gate"

  echo.

  pause

  exit /b 2

)



echo.

echo [2/3] Running factory machine — may take several minutes ...

echo       Goal: !GOAL!

echo.



"%MAG_ROOT%\mag.cmd" factory-machine run --note "!GOAL!"

set "RC=%ERRORLEVEL%"



echo.

echo [3/3] Done. Exit code: %RC%

echo       Report: memory\runs\factory_machine\

echo       Retro:  memory\runs\retrospectives\

echo       Desk:   http://127.0.0.1:8765/?tab=chat

echo.



start "" "http://127.0.0.1:8765/?tab=chat"



pause

exit /b %RC%

