# IBC Expert — Windows Installer Build

IBC Expert uses a PyInstaller **onedir** customer package and an Inno Setup 6 wrapper. The installer
is built only after the onedir package passes the customer-package security verifier.

## Prerequisites

- Windows x64
- CPython 3.14 x64
- verified `dist\IBCExpert` produced by `scripts\build_windows.ps1`
- Inno Setup 6 (`ISCC.exe`)

## Build

```powershell
.\scripts\build_installer.ps1 -AppVersion "0.1.15"
```

If Inno Setup is in a non-standard location:

```powershell
.\scripts\build_installer.ps1 -AppVersion "0.1.15" -InnoSetupCompiler "D:\Tools\Inno Setup 6\ISCC.exe"
```

Output:

- `release\IBCExpert-Setup-0.1.15.exe`
- installer SHA-256 added to `release\SHA256SUMS.txt`

The installer writes the application into Program Files by default. IBC Expert's working database,
encrypted vault, settings and backups remain in the application's local per-user data locations and
are not stored in the installer directory.

## Mandatory release rule

Never point the installer at a folder that has not passed `scripts\verify_customer_package.py`.
Never place `owner_tools` or `owner_private_key.ibckey` under `dist\IBCExpert`.
