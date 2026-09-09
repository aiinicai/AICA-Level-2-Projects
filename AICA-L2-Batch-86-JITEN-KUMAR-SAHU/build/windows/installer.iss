; =============================================================
; ClientLedger India — Inno Setup script
; Requires Inno Setup 6 (https://jrsoftware.org/isinfo.php)
; Run build.bat FIRST so dist\ClientLedgerIndia\ exists, then either:
;   - open this file in the Inno Setup IDE and click Build, or
;   - run:  iscc installer.iss
; Produces ONE file: Output\ClientLedgerIndia-Setup.exe
; =============================================================

#define MyAppName "ClientLedger India"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Your Firm Name"
#define MyAppExeName "ClientLedgerIndia.exe"

[Setup]
AppId={{6C1D9C2B-6E7A-4F0B-9C34-CLIENTLEDGERIN}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=ClientLedgerIndia-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; A single client machine only — no admin rights required to install
; under the user's own AppData if you prefer; change PrivilegesRequired
; to "lowest" for a fully non-admin install.
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
; Pulls in EVERYTHING PyInstaller produced (exe + all dependent DLLs/
; libraries + the templates folder + the bundled pw-browsers folder).
Source: "dist\ClientLedgerIndia\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName} now"; Flags: nowait postinstall skipifsilent

; NOTE on the data folder: the app itself (not this installer) shows a
; one-time folder picker the first time it runs, asking where to keep
; the Database / GSTR1 / GSTR2A / GSTR2B / GSTR3B / TDS_TCS folders.
; That choice is remembered in %APPDATA%\ClientLedgerIndia\config.json,
; completely independent of where the program files are installed —
; so re-installing or upgrading the app never touches client data.
