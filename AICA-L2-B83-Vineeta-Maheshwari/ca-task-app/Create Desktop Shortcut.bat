@echo off
title Create Desktop Shortcut - CA Task App
setlocal
set "SCRIPT_DIR=%~dp0"

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$desktop = [Environment]::GetFolderPath('Desktop');" ^
  "$s = $ws.CreateShortcut([System.IO.Path]::Combine($desktop, 'CA Task App.lnk'));" ^
  "$s.TargetPath = [System.IO.Path]::Combine('%SCRIPT_DIR%', 'Start CA Task App.bat');" ^
  "$s.WorkingDirectory = '%SCRIPT_DIR%';" ^
  "$s.IconLocation = [System.IO.Path]::Combine('%SCRIPT_DIR%', 'assets\icon.ico');" ^
  "$s.WindowStyle = 7;" ^
  "$s.Description = 'CA Task Delegation and Tracking App';" ^
  "$s.Save()"

echo.
echo Done! A "CA Task App" icon has been added to your Desktop.
echo Double-click it any time to launch the app.
echo.
pause
