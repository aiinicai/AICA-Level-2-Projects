@echo off
REM FINsight - Private LAN Host mode.
REM Double-click this file, or right-click it and choose
REM "Send to > Desktop (create shortcut)" to make a desktop icon for it.
REM Other computers on this SAME TRUSTED NETWORK will be able to open
REM FINsight in their browser using the LAN address this prints below.
REM Do not use this on a public or untrusted network.
set FINSIGHT_LAUNCH_MODE=lan
"%~dp0FINsight.exe"
pause
