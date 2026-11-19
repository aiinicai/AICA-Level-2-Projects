@echo off
rem Update to the newest acct_assistant_v*.zip in your Downloads folder, then run setup.
rem Only the program files are replaced; your data and settings stay as they are.
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$z = Get-ChildItem -Path ([Environment]::GetFolderPath('UserProfile') + '\Downloads') -Filter 'acct_assistant_v*.zip' | Sort-Object LastWriteTime -Descending | Select-Object -First 1;" ^
  "if (-not $z) { Write-Host '  No acct_assistant_v*.zip found in Downloads.'; exit 1 }" ^
  "Write-Host ('  Updating from ' + $z.Name); Unblock-File $z.FullName;" ^
  "$t = Join-Path $env:TEMP ('aa_update_' + [guid]::NewGuid()); Expand-Archive -Path $z.FullName -DestinationPath $t -Force;" ^
  "$src = Join-Path $t 'acct_assistant'; if (-not (Test-Path $src)) { $src = $t };" ^
  "Get-ChildItem -Recurse $src | Unblock-File; Copy-Item -Path (Join-Path $src '*') -Destination '%~dp0' -Recurse -Force;" ^
  "Remove-Item -Recurse -Force $t; exit 0"
if errorlevel 1 (
  pause
  exit /b 1
)
call "%~dp0Setup or update.bat"
