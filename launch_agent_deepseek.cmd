@echo off
setlocal
cd /d "%~dp0"
REM Mag agent DeepSeek - remote brain + Mag tools. Icon: mag_agent_deepseek.ico

set "MAG_ROOT=%~dp0"
set "MAG_ROOT=%MAG_ROOT:~0,-1%"
set "PY=%MAG_ROOT%\.venv\Scripts\python.exe"
set "PROVIDER=deepseek"
set "TITLE=Mag agent - DeepSeek"
set "ARGS=main.py agent --provider %PROVIDER% %*"
set "MAG_AGENT_SESSION=deepseek"

if "%~1"==":run_agent" goto run_agent

echo.
echo   Mag agent ^| DeepSeek + local tools
echo   Ensuring backend + dashboard are up...
call "%~dp0ensure_services.cmd"
if %ERRORLEVEL% neq 0 (
  echo [ERROR] Could not ensure services. See messages above.
  pause
  exit /b 1
)
echo.

where wt >nul 2>&1
if %ERRORLEVEL% equ 0 (
  wt -d "%MAG_ROOT%" powershell -NoExit -NoProfile -ExecutionPolicy Bypass -Command "chcp 65001 | Out-Null; $Host.UI.RawUI.WindowTitle = '%TITLE%'; Write-Host ''; Write-Host '  Mag agent | DeepSeek + local tools | Grok not used' -ForegroundColor Blue; Write-Host '  /paste ... /end  /file  /pack  /save  /help  /quit' -ForegroundColor DarkGray; Write-Host ''; $env:MAG_AGENT_SESSION='deepseek'; & '%PY%' %ARGS%"
  exit /b 0
)

start "Mag agent - DeepSeek" cmd /k call "%~f0" :run_agent
exit /b 0

:run_agent
set "MAG_ROOT=%~dp0"
set "MAG_ROOT=%MAG_ROOT:~0,-1%"
set "PY=%MAG_ROOT%\.venv\Scripts\python.exe"
set "PROVIDER=deepseek"
set "TITLE=Mag agent - DeepSeek"
set "ARGS=main.py agent --provider %PROVIDER%"
set "MAG_AGENT_SESSION=deepseek"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Set-Location -LiteralPath '%MAG_ROOT%'; chcp 65001 | Out-Null; $Host.UI.RawUI.WindowTitle = '%TITLE%'; Write-Host ''; Write-Host '  Mag agent | DeepSeek + local tools | Grok not used' -ForegroundColor Blue; Write-Host '  /paste ... /end  /file  /pack  /save  /help  /quit' -ForegroundColor DarkGray; Write-Host ''; $env:MAG_AGENT_SESSION='deepseek'; & '%PY%' %ARGS%; Write-Host ''; pause"
endlocal
