@echo off
setlocal
cd /d "%~dp0"
REM Mag agent — INTERACTIVE REPL (operator typing). For queued/restful work use:
REM   launch_agent_queue.cmd "goal"
REM   python watch/cursor_bridge.py task "goal" --mode queue

set "MAG_ROOT=%~dp0"
set "MAG_ROOT=%MAG_ROOT:~0,-1%"
set "PY=%MAG_ROOT%\.venv\Scripts\python.exe"
set "PROVIDER=deepseek"
set "TITLE=Mag agent"
set "ARGS=main.py agent --provider %PROVIDER% %*"
set "MAG_ALLOW_REPL=1"

echo.
echo   NOTE: Interactive REPL. For improve/background use launch_agent_queue.cmd
echo.
echo   Mag agent ^| %PROVIDER% + local tools
echo  Ensuring backend + dashboard are up...
if /I "%MAG_INTEGRAL_LAB%"=="1" (
  call "%~dp0ensure_backend.cmd"
) else (
  call "%~dp0ensure_services.cmd"
)
if %ERRORLEVEL% neq 0 (
  echo [ERROR] Could not ensure services. See messages above.
  pause
  exit /b 1
)
echo.

set "MAG_AGENT_SESSION=deepseek"

where wt >nul 2>&1
if %ERRORLEVEL% equ 0 (
  wt -d "%MAG_ROOT%" powershell -NoExit -NoProfile -ExecutionPolicy Bypass -Command "chcp 65001 | Out-Null; $Host.UI.RawUI.WindowTitle = '%TITLE%'; Write-Host ''; Write-Host '  Mag agent | %PROVIDER% + local tools | Grok not used' -ForegroundColor Green; Write-Host '  /paste ... /end  /file  /pack  /save  /help  /quit' -ForegroundColor DarkGray; Write-Host ''; & '%PY%' %ARGS%"
  exit /b 0
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "Set-Location -LiteralPath '%MAG_ROOT%'; chcp 65001 | Out-Null; $Host.UI.RawUI.WindowTitle = '%TITLE%'; Write-Host ''; Write-Host '  Mag agent | %PROVIDER% + local tools | Grok not used' -ForegroundColor Green; Write-Host '  /paste ... /end  /file  /pack  /save  /help  /quit' -ForegroundColor DarkGray; Write-Host ''; & '%PY%' %ARGS%; Write-Host ''; pause"
endlocal
