@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\activate.bat (
    echo First time: setting up the environment. Please wait...
    python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
echo.
echo Building the program. This takes several minutes - please wait...
pyinstaller --noconfirm --clean --onefile --windowed --name CA_GST_Filing_Assistant ^
  --add-data "schemas;schemas" --collect-all tkinterdnd2 --collect-submodules app main.py
echo.
if exist dist\CA_GST_Filing_Assistant.exe (
    echo DONE. Your program is here:  %~dp0dist\CA_GST_Filing_Assistant.exe
    echo Copy only that one file to your staff.
) else (
    echo The build did not finish. Please take a photo of this window and send it for help.
)
pause
