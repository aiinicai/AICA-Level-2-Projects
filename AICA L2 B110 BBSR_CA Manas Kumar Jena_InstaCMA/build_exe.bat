@echo off
REM ==================================================================
REM  InstaCMA - build the Windows application (double-click)
REM  Needs Python 3.10 - 3.12 (64-bit) with "Add Python to PATH" ticked.
REM  Output: dist\InstaCMA\InstaCMA.exe
REM ==================================================================
cd /d "%~dp0"
echo [1/4] Installing libraries ...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller
if errorlevel 1 goto :error
echo [2/4] Creating sample files ...
python samples\generate_samples.py
if errorlevel 1 goto :error
echo [3/4] Running the tests ...
python -m unittest tests/test_all.py
if errorlevel 1 echo (Some tests failed - see above. The build continues.)
echo [4/4] Building the application ...
python -m PyInstaller --noconfirm --clean InstaCMA.spec
if errorlevel 1 goto :error
rmdir /s /q build
echo.
echo  Done.  Open:  dist\InstaCMA\InstaCMA.exe
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\InstaCMA.lnk'); $s.TargetPath=(Resolve-Path 'dist\InstaCMA\InstaCMA.exe').Path; $s.WorkingDirectory=(Resolve-Path 'dist\InstaCMA').Path; $s.IconLocation=(Resolve-Path 'dist\InstaCMA\InstaCMA.exe').Path+',0'; $s.Description='InstaCMA - Developed by CA Manas Kumar Jena'; $s.Save()"
echo  A shortcut "InstaCMA" has been placed on your Desktop.
explorer "dist\InstaCMA"
echo  Copy the whole "dist\InstaCMA" folder to any Windows PC.
pause
exit /b 0
:error
echo Build stopped because of an error (see above).
pause
exit /b 1
