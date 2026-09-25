# IBC Expert — Windows Customer Packaging

This folder builds the ordinary **customer** application as a PyInstaller **onedir** package.
It does not package `owner_tools` and must never receive the owner private signing key.

## Required owner preparation

Generate the signing pair once from a protected owner-only source checkout:

```powershell
python -m owner_tools.licence_generator.cli generate-key --key-dir D:\IBCExpertOwnerKeys
```

Keep `owner_private_key.ibckey` only in the protected owner location. Back it up securely.
The only licensing file supplied to the customer build is:

`licence_public_key.hex`

## Build on Windows

Build 15 release packaging must use 64-bit CPython 3.14.x. The build scripts fail closed if another Python minor version is selected.

From the project root:

```powershell
.\scripts\build_windows.ps1 -PublicKeyPath "D:\IBCExpertOwnerKeys\licence_public_key.hex"
```

or:

```bat
scripts\build_windows.bat D:\IBCExpertOwnerKeys\licence_public_key.hex
```

The script validates the public key, installs pinned dependencies (preferring a local `wheelhouse`
when present), builds `dist\IBCExpert`, verifies that owner/private-key material is absent, and
creates `release\IBCExpert-Windows.zip` plus `release\SHA256SUMS.txt`.

## Mandatory security rule

Never copy `owner_private_key.ibckey`, a PEM private key, or the `owner_tools` directory into
`dist\IBCExpert` or any customer installer. The post-build verifier fails if such material is found.

## Offline dependency media

Prepare and verify the offline wheelhouse before taking a source/build machine offline:

```powershell
.\scripts\prepare_wheelhouse.ps1 -Clean
```

See `packaging\OFFLINE_WHEELHOUSE.md`.

## Optional Windows installer

After the verified `dist\IBCExpert` package exists and Inno Setup 6 is installed:

```powershell
.\scripts\build_installer.ps1
```

Or build the onedir package and installer in one command:

```powershell
.\scripts\build_windows.ps1 -PublicKeyPath "D:\IBCExpertOwnerKeys\licence_public_key.hex" -BuildInstaller
```

See `packaging\INSTALLER.md`.
