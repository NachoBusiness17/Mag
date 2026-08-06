@echo off
REM Switch cutting-edge Mag environment tracks (Windows wrapper).
REM Usage: scripts\env_switch.cmd list|use|status|run|sync [track]
setlocal EnableDelayedExpansion

set "ROOT=%MAG_ROOT%"
if not defined ROOT set "ROOT=%~dp0.."
set "ROOT=%ROOT:\=/%"
set "ROOT=%ROOT:/=\%"

powershell -ExecutionPolicy Bypass -File "%~dp0env_switch.ps1" %*
exit /b %ERRORLEVEL%
