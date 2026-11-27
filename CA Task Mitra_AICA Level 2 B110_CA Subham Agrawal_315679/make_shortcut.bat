@echo off
REM Creates a "CA Task Mitra" icon on your Desktop (uses the EXE if built, else run_windows.bat)
set T=%~dp0dist\CA-Task-Mitra.exe
if not exist "%T%" set T=%~dp0run_windows.bat
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\CA Task Mitra.lnk');$s.TargetPath='%T%';$s.WorkingDirectory='%~dp0';$s.Save()"
echo Shortcut created on Desktop.
pause
