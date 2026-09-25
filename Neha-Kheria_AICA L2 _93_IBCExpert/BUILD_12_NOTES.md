# Build 12 Notes — Offline Wheelhouse + Windows Installer Definition

Build 12 continues directly from Build 11. Completed modules were not redesigned.

Added:
- `scripts/prepare_wheelhouse.ps1/.bat`: trusted Windows procedure that downloads pinned direct and transitive dependencies as wheels only, writes hashes, and proves offline resolution.
- `scripts/verify_wheelhouse.py`: SHA-256 manifest generation/verification plus offline pip dry-run dependency resolution.
- `app/core/bootstrap.py`: a selected offline wheelhouse now fails closed when its hash manifest is missing, incomplete or tampered; no silent internet fallback occurs after wheelhouse selection.
- `packaging/OFFLINE_WHEELHOUSE.md`: offline preparation/use/security procedure.
- `packaging/installer/IBCExpert.iss`: Inno Setup 6 customer installer definition around the verified PyInstaller onedir output.
- `scripts/build_installer.ps1/.bat`: re-verifies the customer package before installer compilation and writes the installer SHA-256 to the release manifest.
- `packaging/INSTALLER.md`: installer build procedure.
- `scripts/build_windows.ps1`: verifies a present wheelhouse before dependency installation and can optionally invoke the installer build.
- `tests/test_offline_packaging.py`: wheelhouse tamper/member checks and packaging/installer integration checks.

Validation:
- Python `compileall` succeeds for application, scripts, tests, owner tools and launchers.
- Full monolithic pytest run exits cleanly: **66/66 tests passed** in this build environment.
- Wheelhouse tamper/member checks and packaging/installer integration tests pass.

Not claimed:
- Windows PyInstaller output still cannot be built in this Linux sandbox.
- Inno Setup cannot be executed here; only its definition/integration can be statically and unit tested.
- Clean-Windows installation/launch/trial/activation acceptance remains pending.
