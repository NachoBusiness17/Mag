@echo off
REM Pull bleeding-edge agent research repos into mine\raw\agent_bleeding_edge\
REM Manifest: configs/agent_bleeding_edge_repos.yaml
REM Optional Wave 2: set MAG_BLEEDING_EDGE_WAVE2=1
REM Optional GitHub stars: set MAG_GH_STAR=1 and have gh auth login
setlocal
cd /d "%~dp0.."
set "DEST=%MAG_BLEEDING_EDGE_DEST%"
if "%DEST%"=="" set "DEST=%~dp0..\mine\raw\agent_bleeding_edge"
if not exist "%DEST%" mkdir "%DEST%"

call :clone exo-explore/exo https://github.com/exo-explore/exo.git
call :clone letta-ai/letta https://github.com/letta-ai/letta.git
call :clone mem0ai/mem0 https://github.com/mem0ai/mem0.git
call :clone OpenHands/trajectory-visualizer https://github.com/OpenHands/trajectory-visualizer.git
call :clone clay-good/agent-replay https://github.com/clay-good/agent-replay.git
call :clone AgentOps-AI/agentops https://github.com/AgentOps-AI/agentops.git
call :clone arize-ai/phoenix https://github.com/arize-ai/phoenix.git
call :clone a2aproject/A2A https://github.com/a2aproject/A2A.git
call :clone lastmile-ai/mcp-agent https://github.com/lastmile-ai/mcp-agent.git
call :clone jina-ai/late-chunking https://github.com/jina-ai/late-chunking.git
call :clone getzep/zep https://github.com/getzep/zep.git
call :clone sweepai/sweep https://github.com/sweepai/sweep.git

if "%MAG_BLEEDING_EDGE_WAVE2%"=="1" (
  call :clone agentlens-hq/agentlens https://github.com/agentlens-hq/agentlens.git
  call :clone tranhoangtu-it/agentlens https://github.com/tranhoangtu-it/agentlens.git
  call :clone Allen-Saji/agent-bazaar https://github.com/Allen-Saji/agent-bazaar.git
  call :clone Agent-Bazaar/Agent-Bazaar https://github.com/Agent-Bazaar/Agent-Bazaar.git
  call :clone fixie-ai/fixie-sdk https://github.com/fixie-ai/fixie-sdk.git
)

echo Done. Index: docs\ref\AGENT_BLEEDING_EDGE_REPOS_INDEX.md
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
  REM Phoenix (and some large trees) need long paths on Windows
  git -C "%DIR%" config core.longpaths true 2>nul
  if exist "%DIR%\.git" if not exist "%DIR%\README.md" if not exist "%DIR%\readme.md" if not exist "%DIR%\pyproject.toml" (
    git -C "%DIR%" restore --source=HEAD :/ 2>nul
  )
)
if "%MAG_GH_STAR%"=="1" (
  where gh >nul 2>&1 && gh repo star %SUB% 2>nul
)
exit /b 0
