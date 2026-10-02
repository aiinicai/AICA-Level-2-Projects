@echo off
title ContainerPulse
cd /d "%~dp0"
echo Installing/checking required Python packages...
python -m pip install -r requirements.txt
if errorlevel 1 goto :error
echo.
echo Starting ContainerPulse...
python -m streamlit run app.py
goto :end
:error
echo.
echo ContainerPulse could not start. Please review the error above.
pause
:end
