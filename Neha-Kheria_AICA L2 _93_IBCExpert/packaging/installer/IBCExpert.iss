; IBC Expert customer installer definition (Inno Setup 6)
; Build only from a customer package that has already passed verify_customer_package.py.
; Owner tools and the private licence signing key must never be present in SourceDir.

#ifndef SourceDir
  #define SourceDir "..\..\dist\IBCExpert"
#endif
#ifndef OutputDir
  #define OutputDir "..\..\release"
#endif
#ifndef AppVersion
  #define AppVersion "0.1.12"
#endif

#define MyAppName "IBC Expert"
#define MyAppPublisher "IBC Expert"
#define MyAppExeName "IBCExpert.exe"

[Setup]
AppId={{5B1AC3C8-C4B9-46CE-9655-CC2E75578292}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\IBC Expert
DefaultGroupName=IBC Expert
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename=IBCExpert-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupLogging=yes
CloseApplications=yes
RestartApplications=no
ChangesAssociations=no
ChangesEnvironment=no

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\IBC Expert"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\IBC Expert"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch IBC Expert"; Flags: nowait postinstall skipifsilent
