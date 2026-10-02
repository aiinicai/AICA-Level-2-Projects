@echo off
rem Open the offline app (app\LookThrough.html) in Chrome; fall back to Edge, then the default browser.
rem No setup needed. The app cannot run in Internet Explorer / Edge IE mode, so the default browser is the last resort.
setlocal
set "APP=%~dp0app\LookThrough.html"
if not exist "%APP%" ( echo app\LookThrough.html not found. & pause & exit /b 1 )
for %%B in ("%ProgramFiles%\Google\Chrome\Application\chrome.exe" "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe") do (
  if exist "%%~B" ( start "" "%%~B" "%APP%" & exit /b 0 )
)
start "" "%APP%"
