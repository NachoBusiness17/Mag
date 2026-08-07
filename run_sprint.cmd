@echo off
REM Run coding-session sprint until closed — works from any cwd (uses mag.cmd).
setlocal
cd /d "%~dp0"
"%~dp0mag.cmd" coding-session run %*
exit /b %ERRORLEVEL%
