@echo off
REM Builds CompanyOS.exe using the virtual environment in ..\venv
setlocal
cd /d "%~dp0"

set VENV_PY=..\venv\Scripts\python.exe
if not exist "%VENV_PY%" (
    echo Could not find %VENV_PY% - run setup first: python -m venv ..\venv  ^&^&  ..\venv\Scripts\pip install -r requirements.txt
    exit /b 1
)

echo Cleaning old build...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

echo Building CompanyOS.exe with PyInstaller...
"%VENV_PY%" -m PyInstaller company_os.spec --noconfirm

if exist dist\CompanyOS.exe (
    echo.
    echo ============================================================
    echo  BUILD SUCCESSFUL:  dist\CompanyOS.exe
    echo  Copy the whole "dist" folder to wherever you want to run it
    echo  from (the exe creates its own "data" and "backups" folders
    echo  next to itself the first time it runs^).
    echo ============================================================
) else (
    echo BUILD FAILED - see the log above.
    exit /b 1
)
