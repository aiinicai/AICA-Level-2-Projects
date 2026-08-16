; CMA Pro Builder — Inno Setup script
; Compile:  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\cma.iss
; Output:   E:\AI_SOFTWARE\CMA_Software\Setup\01_With_Key\CMA-Pro-Builder-Setup-1.0.0.exe
;
; Installs to C:\CMA-Pro-Builder (no Program Files permission issues — the app
; writes its database + license into data\ next to the exe).

#define MyAppName      "CMA Pro Builder"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "Kuber R Purkar"

[Setup]
AppId={{C7A1B2D3-4E5F-4A6B-8C9D-CMAPROBUILDER1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={sd}\CMA-Pro-Builder
DefaultGroupName={#MyAppName}
OutputDir=E:\AI_SOFTWARE\CMA_Software\Setup\01_With_Key
OutputBaseFilename=CMA-Pro-Builder-Setup_{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\CMA-Pro-Builder.exe
; Never overwrite live data on reinstall/upgrade
DirExistsWarning=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\release\CMA-Pro-Builder.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "start.bat";               DestDir: "{app}"; Flags: ignoreversion
Source: "stop.bat";                DestDir: "{app}"; Flags: ignoreversion
Source: "start-hidden.vbs";        DestDir: "{app}"; Flags: ignoreversion
Source: "check-status.bat";        DestDir: "{app}"; Flags: ignoreversion
Source: "add-firewall-rules.bat";  DestDir: "{app}"; Flags: ignoreversion
Source: "README.txt";              DestDir: "{app}"; Flags: isreadme

[Dirs]
Name: "{app}\data"

[Tasks]
Name: "desktopicon";     Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"
Name: "startupshortcut"; Description: "Start CMA Pro Builder automatically when Windows boots"; GroupDescription: "Auto-start:"; Flags: unchecked

[Icons]
Name: "{group}\Start CMA Pro Builder";        Filename: "{app}\start-hidden.vbs"; WorkingDir: "{app}"
Name: "{group}\Start CMA Pro Builder (console)"; Filename: "{app}\start.bat";    WorkingDir: "{app}"
Name: "{group}\Stop CMA Pro Builder";         Filename: "{app}\stop.bat";        WorkingDir: "{app}"
Name: "{group}\Check Status";                 Filename: "{app}\check-status.bat"; WorkingDir: "{app}"
Name: "{group}\Setup Guide";                  Filename: "{app}\README.txt"
Name: "{commondesktop}\CMA Pro Builder";      Filename: "{app}\start-hidden.vbs"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userstartup}\CMA Pro Builder";        Filename: "{app}\start-hidden.vbs"; WorkingDir: "{app}"; Tasks: startupshortcut

[Run]
Filename: "{app}\add-firewall-rules.bat"; Description: "Open firewall port 8080 for LAN access (recommended)"; WorkingDir: "{app}"; Flags: postinstall runascurrentuser unchecked
Filename: "{app}\start-hidden.vbs";       Description: "Start CMA Pro Builder now";  WorkingDir: "{app}"; Flags: postinstall shellexec skipifsilent

; NOTE: data\ is intentionally NOT touched by the uninstaller — client data
; and the license survive uninstall/reinstall (upgrades keep everything).
