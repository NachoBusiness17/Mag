@echo off
REM ILAP steal pass — pull forest + field-steal top orchestrator repos + probe
setlocal
cd /d "%~dp0.."
set "PY=%CD%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

call scripts\pull_steal_protocol_repos.cmd

"%PY%" main.py field-steal --root mine/raw/steal_protocol/robzilla1738/agentswarm --max-files 35
"%PY%" main.py field-steal --root mine/raw/steal_protocol/arvarik/bmas --max-files 35
"%PY%" main.py field-steal --root mine/raw/steal_protocol/Bradliebs/ollama-agent-harness --max-files 30

"%PY%" main.py probe-local steal-protocol
"%PY%" main.py coding-session preflight
"%PY%" main.py coding-session plan

echo Done. Packs under memory/improve/field_steal/ · index docs/ref/STEAL_PROTOCOL_REPOS_INDEX.md
exit /b 0
