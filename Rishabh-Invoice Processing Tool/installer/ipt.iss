; Inno Setup script for IPT – compile with ISCC.exe installer\ipt.iss (build_exe.bat does this).
; Installs the program only. Company data stays in %LOCALAPPDATA%\IPT_DATA and is NOT removed on uninstall.
#define AppVersion GetEnv("IPT_VERSION")
[Setup]
AppId={{6B0E7C1E-4D7A-4C55-9C2F-1F3B9E0A1D27}
AppName=IPT - Invoice Processing Tool
AppVersion={#AppVersion}
AppPublisher=IPT
DefaultDirName={autopf}\IPT
DefaultGroupName=IPT
OutputDir=..\dist
OutputBaseFilename=IPT_Setup_{#AppVersion}
Compression=lzma2
SolidCompression=yes
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName=IPT - Invoice Processing Tool

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\dist\IPT\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\IPT - Invoice Processing Tool"; Filename: "{app}\IPT.exe"
Name: "{group}\User manual"; Filename: "{app}\_internal\docs\USER_MANUAL.md"
Name: "{group}\Uninstall IPT"; Filename: "{uninstallexe}"
Name: "{autodesktop}\IPT"; Filename: "{app}\IPT.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\IPT.exe"; Description: "Start IPT now"; Flags: nowait postinstall skipifsilent

; Upgrades: installing a newer version over an old one keeps IPT_DATA; on first start IPT backs up the
; database and runs its migrations automatically.
