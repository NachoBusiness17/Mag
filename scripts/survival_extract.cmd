@echo off
REM Survival extract — pull everything local before cloud/GitHub rent ends.
setlocal EnableDelayedExpansion
cd /d "%~dp0.."
set "PY=%CD%\.venv\Scripts\python.exe"
set "BRANCH=%~1"
if "%BRANCH%"=="" set "BRANCH=cursor/mesh-comm-research-e2ce"

echo [survival] repo: %CD%
echo [survival] branch: %BRANCH%

if not exist "%PY%" (
  echo Missing venv — run scripts\ensure_venv.ps1 first
  exit /b 1
)

echo ==^> git fetch + checkout
git fetch origin
git checkout %BRANCH%
git pull origin %BRANCH%
if errorlevel 1 (
  echo [warn] git pull failed — continuing with local tree
)

echo ==^> pull research clones (mesh + gstd)
if exist scripts\pull_mesh_comm_repos.cmd call scripts\pull_mesh_comm_repos.cmd
if exist scripts\pull_gstdcoin_repos.cmd call scripts\pull_gstdcoin_repos.cmd
if exist scripts\pull_steal_protocol_repos.cmd call scripts\pull_steal_protocol_repos.cmd

echo ==^> mesh deep dive
if exist scripts\mesh_comm_deep_dive.cmd call scripts\mesh_comm_deep_dive.cmd

echo ==^> portable bag
"%PY%" scripts\_survival_bag.py

echo ==^> context pack
if exist mag.cmd call mag.cmd context-pack --mode full

echo ==^> doctor
if exist mag.cmd call mag.cmd doctor

echo.
echo === SURVIVAL EXTRACT DONE ===
echo.
echo Verify:
echo   (Get-ChildItem -Recurse mine\raw\mesh_comm -Directory -Filter .git).Count  ^→ 13
echo   Test-Path memory\research_packs\mesh_forest\INTEGRATION_BRIEF.md
echo   type memory\portable_bags\LATEST.txt
echo.
echo Copy off-machine:
echo   - memory\portable_bags\survival-*
echo   - mine\raw\mesh_comm\  (full mesh source)
echo   - mine\raw\  (gstd if pulled)
echo   - git bundle: git bundle create mag-survival.bundle --all
echo.
echo Use locally:
echo   .\mag.cmd lab
echo   .\mag.cmd agent --provider deepseek
echo.
echo Guide: docs\ref\OPERATOR_SURVIVAL_EXTRACT.md
exit /b 0
