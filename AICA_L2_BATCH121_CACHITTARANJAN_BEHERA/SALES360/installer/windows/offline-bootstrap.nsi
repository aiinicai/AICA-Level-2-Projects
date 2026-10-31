Unicode True
!include "LogicLib.nsh"
!include "FileFunc.nsh"
!include "x64.nsh"
Name "SALES360 Offline Setup"
Icon "${ICONPATH}"
InstallDir "$LOCALAPPDATA\Programs\SALES360"
InstallDirRegKey HKCU "Software\SALES360" "InstallDir"
OutFile "${OUTPUT}"
RequestExecutionLevel user
SetCompressor zlib
ShowInstDetails show
LicenseData "${LICENSEPATH}"
Page license
Page instfiles
Var Arguments
Var Attempts
Function .onInit
 ${IfNot} ${RunningX64}
  MessageBox MB_ICONSTOP "64-bit Windows is required." /SD IDOK
  Abort
 ${EndIf}
 ${GetParameters} $Arguments
FunctionEnd
Section
 InitPluginsDir
 SetOutPath "$PLUGINSDIR"
 File /oname=VC_redist.x64.exe "${VCREDIST}"
 File /oname=SALES360-Application-Setup.exe "${APPLICATION}"
 IfFileExists "$WINDIR\Sysnative\msvcp140.dll" checkruntime 0
 Goto prerequisite
 checkruntime:
 IfFileExists "$WINDIR\Sysnative\vcruntime140.dll" installapp prerequisite
 prerequisite:
 DetailPrint "Installing the bundled Microsoft C++ runtime. No download is needed."
 ExecShell "runas" "$PLUGINSDIR\VC_redist.x64.exe" "/install /passive /norestart"
 StrCpy $Attempts 0
 waitruntime:
 Sleep 1000
 IntOp $Attempts $Attempts + 1
 IfFileExists "$WINDIR\Sysnative\msvcp140.dll" checkagain 0
 IntCmp $Attempts 180 failed waitruntime failed
 checkagain:
 IfFileExists "$WINDIR\Sysnative\vcruntime140.dll" installapp 0
 IntCmp $Attempts 180 failed waitruntime failed
 failed:
 MessageBox MB_ICONSTOP "The Microsoft runtime is required. Setup was cancelled or could not complete. No API key or internet connection is required; run the bundled Microsoft prerequisite and try again." /SD IDOK
 SetErrorLevel 1
 Quit
 installapp:
 DetailPrint "Starting SALES360 application installation."
 ExecWait '"$PLUGINSDIR\SALES360-Application-Setup.exe" $Arguments /D=$INSTDIR' $0
 SetErrorLevel $0
 ${If} $0 != 0
  DetailPrint "Application installation was cancelled or failed (exit $0)."
  IfSilent +2
  MessageBox MB_ICONEXCLAMATION "SALES360 application setup did not complete. Choose an empty installation folder and run setup again. Existing business data has been preserved."
  Abort
 ${EndIf}
SectionEnd
