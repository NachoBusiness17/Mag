@echo off
setlocal
cd /d "%~dp0"
REM Cursor seat — container boundary. Hooks on host write watch/; Mag reads via mount.
echo.
echo   Mag Cursor seat (container-bound)
echo   Host hooks -^> watch\cursor_feed.jsonl  ^|  Mag reads inside Docker
echo.

call "%~dp0launch_mag_container.cmd"
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%

echo   Building context pack inside container...
docker compose exec -T mag python main.py context-pack --agent --goal "Cursor session — follow Mag preamble; file outcomes to trail"

echo.
echo   Preamble: memory\cursor_preamble_latest.md  (host mount)
echo   Feed:     watch\cursor_feed.jsonl
echo   Home:     http://127.0.0.1:8765
echo   In Cursor: @ memory/cursor_preamble_latest.md
echo.
exit /b 0
