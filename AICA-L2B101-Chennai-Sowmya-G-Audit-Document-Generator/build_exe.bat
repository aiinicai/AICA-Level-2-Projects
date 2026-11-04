@echo off
rem Builds "Audit Document Generator.exe" in the dist folder.
rem Run once on any Windows PC with Python 3.11 - 3.13.
cd /d "%~dp0"
set PYV=
for %%V in (3.13 3.12 3.11) do (
  if not defined PYV ( py -%%V --version >nul 2>&1 && set PYV=-%%V )
)
echo Using Python %PYV%
py %PYV% -m pip install --upgrade pyinstaller python-docx pdfplumber || goto fail
py %PYV% -m PyInstaller --noconfirm --onefile --windowed --name "Audit Document Generator" --icon app.ico --add-data "ca_logo.jpeg;." --collect-data docx --collect-data pdfminer --exclude-module pandas --exclude-module numpy --exclude-module pyarrow --exclude-module streamlit --exclude-module matplotlib --exclude-module scipy --exclude-module jinja2 desktop_app.py || goto fail
echo.
echo Done. The program is in the "dist" folder: "Audit Document Generator.exe"
goto end
:fail
echo.
echo Build failed. Please install Python 3.12 from python.org and run this file again.
:end
pause
