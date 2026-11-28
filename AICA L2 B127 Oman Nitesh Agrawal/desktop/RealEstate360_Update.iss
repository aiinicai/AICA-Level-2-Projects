; Inno Setup Upgrade Script for RealEstate360_Update.exe
; Upgrades application binaries while preserving %LOCALAPPDATA%\RealEstate360\data\realestate360.db
#define MyAppName "RealEstate 360"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "RealEstate 360 Systems"
#define MyAppExeName "RealEstate360.exe"

[Setup]
AppId={{7E8F4B21-6C94-4A81-9E2B-360REALESTATE}
AppName={#MyAppName} (Upgrade)
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=output
OutputBaseFilename=RealEstate360_Update
Compression=lzma2/ultra64
SolidCompression=yes
CreateUninstallRegKey=no
Uninstallable=no
WizardStyle=modern
SetupLogging=yes

[Files]
Source: "dist\RealEstate360\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch updated {#MyAppName}"; Flags: nowait postinstall skipifsilent
