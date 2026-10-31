Unicode True
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "nsDialogs.nsh"
!include "x64.nsh"
!include "FileFunc.nsh"
!ifndef PAYLOAD
 !error "Pass /DPAYLOAD=absolute-package-directory"
!endif
!ifndef OUTPUT
 !error "Pass /DOUTPUT=absolute-installer-path"
!endif
Name "SALES360 Offline"
OutFile "${OUTPUT}"
InstallDir "$LOCALAPPDATA\Programs\SALES360"
InstallDirRegKey HKCU "Software\SALES360" "InstallDir"
RequestExecutionLevel user
SetCompressor zlib
BrandingText "SALES360 0.9.1 | Offline Windows x64 | Unsigned evaluation build"
VIProductVersion "0.9.1.0"
VIAddVersionKey "ProductName" "SALES360 Offline"
VIAddVersionKey "FileDescription" "SALES360 Offline Windows Installer"
VIAddVersionKey "FileVersion" "0.9.1"
VIAddVersionKey "LegalCopyright" "SALES360 project"
Var DemoRadio
Var EmptyRadio
Var Dialog
Var TestMode
Var DesktopRequested
Var FolderAllowed
Var FolderHandle
Var FolderEntry
!define MUI_ICON "${PAYLOAD}\icons\sales360.ico"
!define MUI_UNICON "${PAYLOAD}\icons\sales360.ico"
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE "Install SALES360 Offline"
!define MUI_WELCOMEPAGE_TEXT "Install the local finance workspace with bundled Python, .NET and PostgreSQL.$\r$\n$\r$\nNo internet or API keys are required to run the installed application. Email delivery and live ERP/e-invoicing are unavailable offline.$\r$\n$\r$\nThis unsigned local build has documented unfinished business features. Read OFFLINE-README.txt before using company data."
!insertmacro MUI_PAGE_WELCOME
!define MUI_DIRECTORYPAGE_TEXT_TOP "Select a new folder, an existing empty folder, or the existing SALES360 application folder to upgrade. Browse selects the folder; click Next to validate it. Company data stays separate."
!define MUI_PAGE_CUSTOMFUNCTION_LEAVE DirectoryLeave
!insertmacro MUI_PAGE_DIRECTORY
Page custom ModePage ModeLeave
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\INSTALLATION-AND-USAGE.html"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "Create a desktop icon"
!define MUI_FINISHPAGE_SHOWREADME_FUNCTION CreateDesktopIcon
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED
!define MUI_FINISHPAGE_NOAUTOCLOSE
!define MUI_FINISHPAGE_TEXT "Installation is complete. Launch SALES360 from the desktop or Start menu.$\r$\n$\r$\nOn first launch, create your Administrator account with your own email or username and password. The local setup link is protected and can enroll the first Administrator once.$\r$\n$\r$\nBusiness data is stored separately under your Local AppData and is preserved during uninstall."
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
Function .onInit
 ${GetParameters} $0
 ${GetOptions} $0 "/TESTINSTALL=" $TestMode
 ${GetOptions} $0 "/DESKTOPICON=" $DesktopRequested
 ${IfNot} ${RunningX64}
  MessageBox MB_ICONSTOP "SALES360 requires 64-bit Windows." /SD IDOK
  Abort
 ${EndIf}
FunctionEnd
# Do not validate with .onVerifyInstDir: Windows also invokes it inside the
# Browse dialog. Modal messages there can block selection of a different folder.
Function CheckInstallFolder
 StrCpy $FolderAllowed 1
 IfFileExists "$INSTDIR\sales360-installation.txt" folder_done 0
 ClearErrors
 FindFirst $FolderHandle $FolderEntry "$INSTDIR\*"
 IfErrors folder_done
 folder_loop:
  StrCmp $FolderEntry "" folder_close
  StrCmp $FolderEntry "." folder_next
  StrCmp $FolderEntry ".." folder_next
  StrCpy $FolderAllowed 0
  Goto folder_close
 folder_next:
  ClearErrors
  FindNext $FolderHandle $FolderEntry
  IfErrors folder_close folder_loop
 folder_close:
  FindClose $FolderHandle
 folder_done:
FunctionEnd
Function ValidateInstallFolder
 Call CheckInstallFolder
 ${If} $FolderAllowed != 1
  SetErrorLevel 1
  ${IfNot} ${Silent}
   MessageBox MB_ICONSTOP "The selected folder contains files that are not a recognized SALES360 installation:$\r$\n$INSTDIR$\r$\n$\r$\nChoose an existing empty folder, type a new folder name, or choose the existing SALES360 application folder for an upgrade. Company data and unrelated files have not been changed."
  ${EndIf}
  Abort
 ${EndIf}
 SetErrorLevel 0
FunctionEnd
Function DirectoryLeave
 Call ValidateInstallFolder
FunctionEnd
Function ModePage
 nsDialogs::Create 1018
 Pop $Dialog
 ${NSD_CreateLabel} 0 0 100% 30u "Choose first-run data. Existing application data is always retained."
 Pop $0
 ${NSD_CreateRadioButton} 0 38u 100% 18u "Empty offline company - create your own customers and projects"
 Pop $EmptyRadio
 ${NSD_Check} $EmptyRadio
 ${NSD_CreateRadioButton} 0 64u 100% 18u "Synthetic demonstration - 1,000 sample projects"
 Pop $DemoRadio
 ${NSD_CreateLabel} 0 100u 100% 50u "This installs a local application, not a public server. No firewall rules or cloud connections will be added. Email addresses are local login identifiers; recovery is managed locally."
 Pop $0
 nsDialogs::Show
FunctionEnd
Function ModeLeave
 ${NSD_GetState} $DemoRadio $1
FunctionEnd
Section "SALES360 Offline" Main
 Call ValidateInstallFolder
 SetShellVarContext current
 IfFileExists "$INSTDIR\runtime\python\python.exe" 0 copyfiles
 nsExec::ExecToLog '"$INSTDIR\runtime\python\python.exe" "$INSTDIR\SALES360.py" --stop'
 Pop $0
 ${If} $0 != 0
  MessageBox MB_ICONSTOP "Close SALES360 before repairing or upgrading. Your business data has not been changed." /SD IDOK
  Abort
 ${EndIf}
 copyfiles:
 ClearErrors
 SetOutPath "$INSTDIR"
 ${If} ${Errors}
  SetErrorLevel 2
  MessageBox MB_ICONSTOP "The installation folder could not be created or opened. Choose a folder writable by your Windows account. Company data has not been changed." /SD IDOK
  Abort
 ${EndIf}
 File /r "${PAYLOAD}\*"
 ${If} $1 == ${BST_CHECKED}
  FileOpen $0 "$INSTDIR\offline-demo.flag" w
  FileWrite $0 "Synthetic demonstration selected"
  FileClose $0
 ${EndIf}
 FileOpen $0 "$INSTDIR\sales360-installation.txt" w
 FileWrite $0 "SALES360 Offline 0.9.1 - user installation"
 FileClose $0
 WriteUninstaller "$INSTDIR\Uninstall-SALES360.exe"
 ${If} $TestMode == "1"
  FileOpen $0 "$INSTDIR\test-install.flag" w
  FileWrite $0 "Isolated installer verification; no shortcuts or registry entries"
  FileClose $0
 ${Else}
 CreateDirectory "$SMPROGRAMS\SALES360"
 CreateShortcut "$SMPROGRAMS\SALES360\SALES360 Offline.lnk" "$INSTDIR\runtime\python\pythonw.exe" '"$INSTDIR\SALES360.py"' "$INSTDIR\icons\sales360.ico"
 CreateShortcut "$SMPROGRAMS\SALES360\Stop SALES360.lnk" "$INSTDIR\runtime\python\python.exe" '"$INSTDIR\SALES360.py" --stop'
 CreateShortcut "$SMPROGRAMS\SALES360\Read offline guide.lnk" "$INSTDIR\OFFLINE-README.txt"
 WriteRegStr HKCU "Software\SALES360" "InstallDir" "$INSTDIR"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SALES360" "DisplayName" "SALES360 Offline"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SALES360" "DisplayVersion" "0.9.1"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SALES360" "UninstallString" '"$INSTDIR\Uninstall-SALES360.exe"'
 WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SALES360" "NoModify" 1
 ${EndIf}
 ${If} ${Silent}
  ${If} $DesktopRequested == "1"
   Call CreateDesktopIcon
  ${EndIf}
 ${EndIf}
SectionEnd
Function CreateDesktopIcon
 ${If} $TestMode == "1"
  CreateDirectory "$INSTDIR\test-shortcuts"
  CreateShortcut "$INSTDIR\test-shortcuts\SALES360 Offline.lnk" "$INSTDIR\runtime\python\pythonw.exe" '"$INSTDIR\SALES360.py"' "$INSTDIR\icons\sales360.ico"
 ${Else}
  CreateShortcut "$DESKTOP\SALES360 Offline.lnk" "$INSTDIR\runtime\python\pythonw.exe" '"$INSTDIR\SALES360.py"' "$INSTDIR\icons\sales360.ico"
 ${EndIf}
FunctionEnd
Section "Uninstall"
 SetShellVarContext current
 IfFileExists "$INSTDIR\sales360-installation.txt" 0 unsafe
 nsExec::ExecToLog '"$INSTDIR\runtime\python\python.exe" "$INSTDIR\SALES360.py" --stop'
 Pop $0
 ${If} $0 != 0
  MessageBox MB_ICONSTOP "Close SALES360 before uninstalling." /SD IDOK
  Abort
 ${EndIf}
 IfFileExists "$INSTDIR\test-install.flag" skipshortcuts 0
 Delete "$DESKTOP\SALES360 Offline.lnk"
 Delete "$SMPROGRAMS\SALES360\SALES360 Offline.lnk"
 Delete "$SMPROGRAMS\SALES360\Stop SALES360.lnk"
 Delete "$SMPROGRAMS\SALES360\Read offline guide.lnk"
 RMDir "$SMPROGRAMS\SALES360"
 DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SALES360"
 DeleteRegKey HKCU "Software\SALES360"
 skipshortcuts:
 RMDir /r "$INSTDIR\icons"
 RMDir /r "$INSTDIR\test-shortcuts"
 Delete "$INSTDIR\INSTALLATION-AND-USAGE.html"
 Delete "$INSTDIR\INSTALLATION-AND-USAGE.pdf"
 RMDir /r "$INSTDIR\host"
 RMDir /r "$INSTDIR\runtime"
 RMDir /r "$INSTDIR\apps"
 RMDir /r "$INSTDIR\scripts"
 RMDir /r "$INSTDIR\templates"
 RMDir /r "$INSTDIR\docs"
 RMDir /r "$INSTDIR\licenses"
 Delete "$INSTDIR\SALES360.py"
 Delete "$INSTDIR\Start-SALES360.bat"
 Delete "$INSTDIR\Stop-SALES360.bat"
 Delete "$INSTDIR\Backup-SALES360.bat"
 Delete "$INSTDIR\Restore-SALES360.bat"
 Delete "$INSTDIR\OFFLINE-README.txt"
 Delete "$INSTDIR\bundle-manifest.json"
 Delete "$INSTDIR\offline-demo.flag"
 Delete "$INSTDIR\sales360-installation.txt"
 Delete "$INSTDIR\test-install.flag"
 Delete "$INSTDIR\Uninstall-SALES360.exe"
 RMDir "$INSTDIR"
 Goto done
 unsafe:
 MessageBox MB_ICONSTOP "Installation marker missing. Refusing to remove files." /SD IDOK
 Abort
 done:
SectionEnd
