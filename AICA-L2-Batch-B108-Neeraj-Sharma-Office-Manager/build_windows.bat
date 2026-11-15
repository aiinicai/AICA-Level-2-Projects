@echo off
REM Run this once on a Windows PC that has Python 3.11+ installed. Produces dist\OfficeManager\OfficeManager.exe
python -m venv .venv || goto :err
call .venv\Scripts\activate.bat
pip install -r requirements-dev.txt || goto :err
python -m pytest -q || goto :err
pyinstaller --noconfirm OfficeManager.spec || goto :err
echo.
echo Done. Copy the dist\OfficeManager folder to the office PCs and run OfficeManager.exe
goto :eof
:err
echo Build failed. Send the messages above to your developer.
exit /b 1
