; Petrosuite.iss — Inno Setup installer script.
; Build with: open this file in Inno Setup Compiler, click "Compile"
;             (or from command line: ISCC.exe Petrosuite.iss)
;
; PREREQUISITE: run PyInstaller FIRST (see ../BUILD.md) so that
; dist\Petrosuite\ exists before compiling this script.

#define MyAppName "Petrosuite"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "SKP"
#define MyAppExeName "Petrosuite.exe"

[Setup]
AppId={{B7B6C1B0-6E1A-4C1E-9B8A-2B2A6C5A9E3D}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=Petrosuite_Setup_v{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Requires Admin rights to install to Program Files
PrivilegesRequired=admin
#ifexist "app_icon.ico"
SetupIconFile=app_icon.ico
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"

[Files]
; Everything PyInstaller produced, including Petrosuite.exe, Qt DLLs, and
; the bundled web/ folder (app.html, fonts, lib).
Source: "dist\Petrosuite\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName} now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Uninstalling removes the installed program files only. The user's actual
; business data (SQLite DB at %LOCALAPPDATA%\Petrosuite\skp_gst.db) is
; deliberately NOT deleted on uninstall — accounting data must survive an
; uninstall/reinstall or version upgrade.
