@echo off
setlocal
REM Starts the DPDP Readiness Assessor with Gemini drafting the observation prose.
REM The key is held only in this window's environment for this run. It is never
REM written to a file. Leave it blank to run offline.
set /p "GEMINI_API_KEY=Paste your Gemini API key (or press Enter to run offline): "
"%~dp0DPDP_Assessor.exe"
endlocal
