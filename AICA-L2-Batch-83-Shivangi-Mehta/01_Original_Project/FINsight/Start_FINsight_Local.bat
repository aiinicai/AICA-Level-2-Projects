@echo off
REM FINsight - Local Computer mode.
REM Double-click this file, or right-click it and choose
REM "Send to > Desktop (create shortcut)" to make a desktop icon for it.
REM Only this computer will be able to open FINsight.
set FINSIGHT_LAUNCH_MODE=local
"%~dp0FINsight.exe"
pause
