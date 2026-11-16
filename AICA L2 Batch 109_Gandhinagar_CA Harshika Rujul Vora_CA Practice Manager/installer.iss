; Inno Setup script: turns dist\CAPracticeManager into a normal Windows installer
; (CAPracticeManager-Setup.exe) with Start menu + desktop shortcuts and an uninstaller.
; No administrator rights needed: it installs for the current user.
; Build:  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

#ifndef MyAppVersion
  #define MyAppVersion "2.1.0"
#endif

[Setup]
AppId={{6E1C2B7A-4F3D-4B8E-9C61-CA0000000002}
AppName=CA Practice Manager
AppVersion={#MyAppVersion}
AppPublisher=CA Practice Manager
DefaultDirName={localappdata}\Programs\CA Practice Manager
DefaultGroupName=CA Practice Manager
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=CAPracticeManager-Setup
SetupIconFile=assets\app.ico
UninstallDisplayIcon={app}\CAPracticeManager.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "dist\CAPracticeManager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\CA Practice Manager"; Filename: "{app}\CAPracticeManager.exe"
Name: "{autodesktop}\CA Practice Manager"; Filename: "{app}\CAPracticeManager.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\CAPracticeManager.exe"; Description: "Open CA Practice Manager now"; Flags: nowait postinstall skipifsilent
