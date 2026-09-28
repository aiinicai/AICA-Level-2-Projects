@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0upload-skill.ps1" strategic-advisory-mandate-letter
pause
