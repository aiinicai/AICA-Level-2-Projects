@echo off
rem Browser version. Uses Python 3.13 / 3.12 / 3.11 if installed
rem (very new Pythons may not support Streamlit yet).
cd /d "%~dp0"
set PYV=
for %%V in (3.13 3.12 3.11) do (
  if not defined PYV ( py -%%V --version >nul 2>&1 && set PYV=-%%V )
)
echo Using Python %PYV%
py %PYV% -m pip install -r requirements.txt --quiet || goto fail
py %PYV% -m streamlit run streamlit_app.py
goto end
:fail
echo.
echo Installation failed. Please install Python 3.12 from python.org and run this file again.
:end
pause
