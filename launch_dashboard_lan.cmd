@echo off
REM Launch Mag dashboard on the LAN so other devices on the same network
REM can load the Mag device website and query the local agent.
REM
REM   python main.py dashboard --host 0.0.0.0 --port 8765
REM
REM Then from another device on the same network open:
REM   http://<THIS-PC-LAN-IP>:8765/
REM
REM Find this PC's LAN IP with:  ipconfig  (look for IPv4 Address)
REM
setlocal
set "MAG_ROOT=%~dp0"
set "MAG_ROOT=%MAG_ROOT:~0,-1%"
set "PY=%MAG_ROOT%\.venv\Scripts\python.exe"
cd /d "%MAG_ROOT%"

if not exist "%PY%" (
  echo Mag venv python missing: "%PY%"
  pause
  exit /b 1
)

echo.
echo  ============================================================
echo   Mag LAN dashboard  -  http://0.0.0.0:8765/
echo   Reachable from other devices on the same local network.
echo   Find this PC's IP with:  ipconfig
echo   Then open  http://<IP>:8765/  from a phone/tablet/laptop.
echo.
echo   G2 auth: set MAG_REMOTE_TOKEN before tablet POSTs write todo/working.
echo   Header: Authorization: Bearer ^<your-token^>
echo   Dev bypass (trusted LAN only): set MAG_REMOTE_AUTH_DISABLE=1
echo   Ctrl+C to stop.
echo  ============================================================
echo.

set MAG_BIND_HOST=0.0.0.0
"%PY%" main.py dashboard --host 0.0.0.0 --port 8765
endlocal
