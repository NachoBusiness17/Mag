@echo off
REM Pull mesh / offline comm research repos into mine\raw\mesh_comm\
setlocal
cd /d "%~dp0.."
set "DEST=%MAG_MESH_DEST%"
if "%DEST%"=="" set "DEST=%~dp0..\mine\raw\mesh_comm"
if not exist "%DEST%" mkdir "%DEST%"

call :clone permissionlesstech/bitchat https://github.com/permissionlesstech/bitchat.git
call :clone permissionlesstech/bitchat-android https://github.com/permissionlesstech/bitchat-android.git
call :clone permissionlesstech/georelays https://github.com/permissionlesstech/georelays.git
call :clone bridgefy/sdk-android https://github.com/bridgefy/sdk-android.git
call :clone bridgefy/sdk-ios https://github.com/bridgefy/sdk-ios.git
call :clone bridgefy/bridgefy_flutter https://github.com/bridgefy/bridgefy_flutter.git
call :clone bridgefy/bridgefy-react-native https://github.com/bridgefy/bridgefy-react-native.git
call :clone bridgefy/sdk-android-beta https://github.com/bridgefy/sdk-android-beta.git
call :clone bridgefy/sdk-ios-beta https://github.com/bridgefy/sdk-ios-beta.git
call :clone briar/briar https://github.com/briar/briar.git
call :clone briar/briar-mailbox https://github.com/briar/briar-mailbox.git
call :clone briar/briar-desktop https://github.com/briar/briar-desktop.git
call :clone briar/onionwrapper https://github.com/briar/onionwrapper.git

echo Done. Index: docs\ref\MESH_COMM_REPOS_INDEX.md
exit /b 0

:clone
set "SUB=%~1"
set "URL=%~2"
set "DIR=%DEST%\%SUB%"
if not exist "%DIR%" mkdir "%DIR%\.."
if exist "%DIR%\.git" (
  echo ==^> pull %SUB%
  git -C "%DIR%" pull --ff-only
) else (
  echo ==^> clone %SUB%
  git clone --depth 1 "%URL%" "%DIR%"
)
exit /b 0
