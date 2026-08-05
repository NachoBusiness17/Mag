@echo off
REM Sync home PC from remote branch + refresh research clones.
REM Safe from wrong cwd: resolves repo via MAG_ROOT or mag.cmd walk-up.
setlocal EnableDelayedExpansion

set "ROOT=%MAG_ROOT%"
if not defined ROOT set "ROOT=%~dp0.."
set "ROOT=%ROOT:\=/%"
set "ROOT=%ROOT:/=\%"

REM Walk up until mag.cmd found (max 6 levels)
set "TRY=%ROOT%"
set /a N=0
:find_root
if exist "%TRY%\mag.cmd" goto found
set /a N+=1
if %N% GEQ 6 goto no_root
pushd "%TRY%\.." 2>nul || goto no_root
set "TRY=%CD%"
popd
goto find_root

:found
cd /d "%TRY%"
echo [home_sync] repo: %CD%

set "BRANCH=%~1"
if "%BRANCH%"=="" (
  for /f "tokens=*" %%b in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set "BRANCH=%%b"
)
if "%BRANCH%"=="" set "BRANCH=cursor/mesh-comm-research-e2ce"

echo [home_sync] fetch + checkout %BRANCH%
git fetch origin
if errorlevel 1 goto fail
git checkout %BRANCH%
if errorlevel 1 goto fail
git pull origin %BRANCH%
if errorlevel 1 goto fail

if exist "scripts\pull_mesh_comm_repos.cmd" call scripts\pull_mesh_comm_repos.cmd
if exist "scripts\pull_gstdcoin_repos.cmd" call scripts\pull_gstdcoin_repos.cmd

if exist "mag.cmd" (
  call mag.cmd doctor
  call mag.cmd context-pack --mode janitor
) else (
  echo [home_sync] warn: mag.cmd missing
)

echo [home_sync] done
exit /b 0

:no_root
echo [home_sync] ERROR: cannot find mag.cmd. Set MAG_ROOT or cd to repo.
echo Example: set MAG_ROOT=%USERPROFILE%\Documents\projects\local_sovereign_agent
exit /b 1

:fail
echo [home_sync] ERROR: git step failed
exit /b 1
