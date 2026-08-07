@echo off
REM Pull agent-platform research repos into mine\raw\agent_platform\
REM Manifest: configs/agent_platform_repos.yaml
REM Optional Wave 2 (huge/archived): set MAG_AGENT_PLATFORM_WAVE2=1
REM Optional GitHub stars: set MAG_GH_STAR=1 and have gh auth login
setlocal
cd /d "%~dp0.."
set "DEST=%MAG_AGENT_PLATFORM_DEST%"
if "%DEST%"=="" set "DEST=%~dp0..\mine\raw\agent_platform"
if not exist "%DEST%" mkdir "%DEST%"

call :clone OpenHands/OpenHands https://github.com/OpenHands/OpenHands.git
call :clone SWE-agent/SWE-agent https://github.com/SWE-agent/SWE-agent.git
call :clone Aider-AI/aider https://github.com/Aider-AI/aider.git
call :clone jj-vcs/jj https://github.com/jj-vcs/jj.git
call :clone BerriAI/litellm https://github.com/BerriAI/litellm.git
call :clone modelcontextprotocol/python-sdk https://github.com/modelcontextprotocol/python-sdk.git
call :clone continuedev/continue https://github.com/continuedev/continue.git
call :clone meltylabs/melty https://github.com/meltylabs/melty.git
call :clone trypear/pearai-submodule https://github.com/trypear/pearai-submodule.git

REM Wave 1b — worktree ops / terminal / kanban (2026 trench)
call :clone SWE-agent/mini-swe-agent https://github.com/SWE-agent/mini-swe-agent.git
call :clone anomalyco/opencode https://github.com/anomalyco/opencode.git
call :clone nekocode/agent-worktree https://github.com/nekocode/agent-worktree.git
call :clone WorktreePilot/worktree-pilot https://github.com/WorktreePilot/worktree-pilot.git
call :clone alamops/agetor https://github.com/alamops/agetor.git
call :clone cline/cline https://github.com/cline/cline.git
call :clone cline/kanban https://github.com/cline/kanban.git
call :clone mifunedev/openharness https://github.com/mifunedev/openharness.git
call :clone RunMaestro/Maestro https://github.com/RunMaestro/Maestro.git

REM Wave 1c — SDK harness references
call :clone google/adk-python https://github.com/google/adk-python.git
call :clone openai/openai-agents-python https://github.com/openai/openai-agents-python.git

if "%MAG_AGENT_PLATFORM_WAVE2%"=="1" (
  call :clone voideditor/void https://github.com/voideditor/void.git
  call :clone codestoryai/aide https://github.com/codestoryai/aide.git
  call :clone codestoryai/sidecar https://github.com/codestoryai/sidecar.git
  call :clone facebook/sapling https://github.com/facebook/sapling.git
  call :clone axelgar/opentree https://github.com/axelgar/opentree.git
  call :clone emdgroup/maestro https://github.com/emdgroup/maestro.git
  call :clone Knwar/kankanban https://github.com/Knwar/kankanban.git
)

echo Done. Index: docs\ref\AGENT_PLATFORM_REPOS_INDEX.md
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
