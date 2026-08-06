@echo off
:: Double-click or run — triggers UAC, fixes WLAN services
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0fix-wifi.ps1\"' -Verb RunAs"
    exit /b
)
powershell -ExecutionPolicy Bypass -File "%~dp0fix-wifi.ps1"
pause
