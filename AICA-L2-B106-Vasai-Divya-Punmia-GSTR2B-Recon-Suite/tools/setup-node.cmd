@echo off
rem ----------------------------------------------------------------------
rem  Makes sure a suitable Node.js (20.19+ / 22.12+) WITH npm is available.
rem  1) Uses the portable copy in .\runtime\node if present
rem  2) Otherwise uses Node.js installed on this computer (if new enough and npm exists)
rem  3) Otherwise downloads a portable Node.js into .\runtime\node
rem  Adds the chosen Node.js to PATH for the calling BAT file, and keeps
rem  npm's download cache inside .\runtime\npm-cache (not on drive C:).
rem ----------------------------------------------------------------------
set "GSR_NODE_DIR=%~dp0..\runtime\node"
set "npm_config_cache=%~dp0..\runtime\npm-cache"
set "npm_config_update_notifier=false"
set "npm_config_fund=false"
set "npm_config_audit=false"

rem NOTE: PATH is never changed inside ( ) blocks, because PATH can contain ")".
if exist "%GSR_NODE_DIR%\node.exe" goto :use_portable

where node >nul 2>nul
if errorlevel 1 goto :download
where npm >nul 2>nul
if errorlevel 1 (
  echo       Node.js is installed but npm is missing - a portable copy will be used instead.
  goto :download
)
call :version_ok
if errorlevel 1 (
  echo       Installed Node.js is too old - a portable newer version will be used instead.
  goto :download
)
goto :done

:download
echo       Setting up a private copy of Node.js inside the app folder...
echo       ^(one time only, needs internet, about 30 MB^)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0get-node.ps1" -Dest "%GSR_NODE_DIR%"
if errorlevel 1 goto :fail
if not exist "%GSR_NODE_DIR%\node.exe" goto :fail

:use_portable
set "PATH=%GSR_NODE_DIR%;%PATH%"
call :version_ok
if errorlevel 1 goto :fail

:done
for /f "delims=" %%v in ('node -v') do echo       Node.js %%v ready.
exit /b 0

:version_ok
node -e "const [a,b]=process.versions.node.split('.').map(Number);process.exit(a>22||(a===22&&b>=12)||(a===20&&b>=19)?0:1)" >nul 2>nul
exit /b %errorlevel%

:fail
echo.
echo [ERROR] Could not set up Node.js automatically.
echo         Please install it manually, then run this file again:
echo           - Download the LTS installer from https://nodejs.org   OR
echo           - Open Command Prompt and run:  winget install OpenJS.NodeJS.LTS
exit /b 1
