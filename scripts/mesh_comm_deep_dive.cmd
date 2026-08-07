@echo off
REM Mesh forest deep dive — all 13 clones + integration brief for local agent.
setlocal EnableDelayedExpansion
cd /d "%~dp0.."
set "PY=%CD%\.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo Missing venv. Run scripts\ensure_venv.ps1
  exit /b 1
)

echo ==^> mesh deep dive: pull clones
call scripts\pull_mesh_comm_repos.cmd
if errorlevel 1 exit /b 1

echo ==^> field-steal all repos
set "DEST=%CD%\mine\raw\mesh_comm"
for %%R in (
  "permissionlesstech\bitchat"
  "permissionlesstech\bitchat-android"
  "permissionlesstech\georelays"
  "bridgefy\sdk-android"
  "bridgefy\sdk-ios"
  "bridgefy\bridgefy_flutter"
  "bridgefy\bridgefy-react-native"
  "bridgefy\sdk-android-beta"
  "bridgefy\sdk-ios-beta"
  "briar\briar"
  "briar\briar-mailbox"
  "briar\briar-desktop"
  "briar\onionwrapper"
) do (
  if exist "%DEST%\%%~R" (
    echo ==^> steal %%~R
    "%PY%" main.py field-steal --root "%DEST%\%%~R" --max-files 35
  ) else (
    echo skip missing %%~R
  )
)

if not exist "memory\research_packs\mesh_forest" mkdir "memory\research_packs\mesh_forest"
echo ==^> integration brief
"%PY%" scripts\_mesh_integration_brief.py

echo.
echo Done. Next:
echo   .\mag.cmd agent --provider deepseek
echo   Goal: Read memory\research_packs\mesh_forest\INTEGRATION_BRIEF.md
echo   Guide: docs\ref\MESH_LOCAL_AGENT.md
exit /b 0
