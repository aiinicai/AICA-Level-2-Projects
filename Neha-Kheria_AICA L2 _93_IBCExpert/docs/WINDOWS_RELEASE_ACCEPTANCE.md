# IBC Expert — Windows Release and Clean-Machine Acceptance

Build 15 retains the Build 14 release harness and adds the CPython 3.14 release target; it does **not** claim that Windows gates have already passed.
The ordinary application remains offline-first: it has no legal/database web downloader or automatic updater, and its primary database and working data stay local on the computer.

## A. Trusted Windows release workstation

Requirements: Windows 10/11, 64-bit CPython 3.14.x, verified `wheelhouse/` if doing an offline release build, Inno Setup 6, and the owner's **public** Ed25519 licence verification key. Never place the private signing key in the project/customer build tree.

From PowerShell in the project root:

```powershell
.\scripts\run_windows_release_gate.ps1 -PublicKeyPath C:\secure\licence_public_key.hex -Wheelhouse C:\secure\ibc-wheelhouse
```

The harness creates a fresh release virtual environment, installs the pinned requirements, runs the complete pytest suite, builds the PyInstaller onedir customer package, verifies that owner/private-key material is excluded, builds the Inno Setup installer, creates SHA-256-bound release evidence, and prepares `release\clean-windows-acceptance`.

A successful normal pip install does **not** count as first-run bootstrap acceptance. `bootstrap_online` and `bootstrap_wheelhouse` remain BLOCKED until the real first-run bootstrap/progress path is explicitly exercised in disposable Windows source-install environments.

## B. First-run bootstrap acceptance

On disposable Windows test environments, separately exercise the real application bootstrap UI/path:

1. Online package-index path, with no pre-existing third-party runtime packages.
2. Verified offline wheelhouse path, with internet unavailable.

Record PASS/FAIL and evidence in `windows_release_evidence.json` using `scripts\release_evidence.py set ...`. A selected wheelhouse must fail closed if missing, incomplete or tampered.

## C. Clean Windows machine/VM

Copy only the generated `release\clean-windows-acceptance` kit to a genuinely clean Windows VM/PC. Use synthetic data only. Run:

```bat
clean_windows_acceptance.bat
```

The recorder is PowerShell-only; Python is not required on the end-user machine. It guides installation, launch, core synthetic workflow, backup/restore, restart persistence, and trial-expiry/offline-activation checks. It never auto-marks a gate PASS.

## D. Return and validate evidence

Copy the completed evidence JSON back to `release\evidence` together with any evidence files it references. Then run:

```powershell
.\.release-venv\Scripts\python.exe scripts\release_evidence.py validate release\evidence\windows_release_evidence.json --require-complete
.\.release-venv\Scripts\python.exe scripts\release_evidence.py report release\evidence\windows_release_evidence.json --output release\evidence\WINDOWS_RELEASE_REPORT.md
```

Do not call the product COMPLETE unless validation succeeds with every defined gate PASS. If a Windows-specific defect is found, fix only that defect, rerun the affected regression tests, and rerun the failed release gate.
