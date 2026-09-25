# IBC Expert — Windows Installation Manual

## Customer installation
1. Obtain the owner-built `IBCExpert-Setup.exe` and its published SHA-256 value through a trusted channel.
2. Verify the installer hash if your distribution process provides one.
3. Run the installer and complete the normal Windows installation.
4. Start **IBC Expert** from the Start menu/shortcut.
5. On first application use, create the master user/password.
6. Do not place the owner's private licence-signing key anywhere inside the IBC Expert installation directory.

## Source/development installation
Python 3.11-3.14 is supported for source use. The validated Windows release target for Build 15 is 64-bit CPython 3.14.x. Run `launch_desktop.py`. Before third-party application modules load, the stdlib-only bootstrap checks `requirements.txt`; when dependencies are missing it presents first-run progress and installs only the missing pinned requirements. If a `wheelhouse/` directory is present, its SHA-256 manifest is verified and installation is forced offline with no package-index fallback.

## Offline dependency media
Prepare the wheelhouse on a trusted Windows build computer using `scripts/prepare_wheelhouse.ps1`. Preserve `wheelhouse/SHA256SUMS.txt`. See `packaging/OFFLINE_WHEELHOUSE.md` for the exact build/verification procedure.

## Local data
Operational data is stored under the application's local data root discovered by `AppPaths`; the primary SQLite database, encrypted vault, trial/licence state and local backups are not cloud databases. Normal runtime must not require an internet connection.

## Uninstall warning
Uninstalling the executable does not mean client data should be intentionally destroyed. Before uninstalling or migrating computers, create and verify an encrypted backup and preserve the data directory according to your organisation's retention policy.
