@echo off
REM Pull steal-protocol research repos into mine\raw\steal_protocol\
REM Manifest: configs/steal_protocol_repos.yaml
REM Optional GitHub stars: set MAG_GH_STAR=1 and have gh auth login
setlocal
cd /d "%~dp0.."
set "DEST=%MAG_STEAL_DEST%"
if "%DEST%"=="" set "DEST=%~dp0..\mine\raw\steal_protocol"
if not exist "%DEST%" mkdir "%DEST%"

call :clone robzilla1738/agentswarm https://github.com/robzilla1738/agentswarm.git
call :clone arvarik/bmas https://github.com/arvarik/bmas.git
call :clone whiteducksoftware/flock https://github.com/whiteducksoftware/flock.git
call :clone hemantsingh443/blackboard-core https://github.com/hemantsingh443/blackboard-core.git
call :clone Bradliebs/ollama-agent-harness https://github.com/Bradliebs/ollama-agent-harness.git
call :clone marikarx/subagent-router https://github.com/marikarx/subagent-router.git
call :clone Leeroo-AI/leeroo_orchestrator https://github.com/Leeroo-AI/leeroo_orchestrator.git
call :clone EIT-EAST-Lab/C3 https://github.com/EIT-EAST-Lab/C3.git
call :clone togethercomputer/moa https://github.com/togethercomputer/moa.git
call :clone microsoft/conductor https://github.com/microsoft/conductor.git
call :clone claudioed/agent-blackboard https://github.com/claudioed/agent-blackboard.git

echo Done. Index: docs\ref\STEAL_PROTOCOL_REPOS_INDEX.md
exit /b 0

:clone
set "SUB=%~1"
set "URL=%~2"
set "DIR=%DEST%\%SUB%"
if not exist "%DIR%\.." mkdir "%DIR%\.."
if exist "%DIR%\.git" (
  echo ==^> pull %SUB%
  git -C "%DIR%" pull --ff-only
) else (
  echo ==^> clone %SUB%
  git clone --depth 1 "%URL%" "%DIR%"
)
if "%MAG_GH_STAR%"=="1" (
  where gh >nul 2>&1 && gh repo star %SUB% 2>nul
)
exit /b 0
