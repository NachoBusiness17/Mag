@echo off
cd /d "%~dp0"
call "%~dp0ensure_services.cmd"
if %ERRORLEVEL% equ 0 start "" http://127.0.0.1:8765/
