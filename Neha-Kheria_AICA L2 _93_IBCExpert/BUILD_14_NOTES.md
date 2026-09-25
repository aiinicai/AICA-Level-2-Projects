# Build 14 Notes

Application version: `0.1.14-dev`. Database schema/migration unchanged.

This build adds only release/acceptance tooling and documentation; completed application business functionality was not redesigned or reworked.

Added:
- `scripts/release_evidence.py`: stdlib release-gate evidence schema, SHA-256 evidence binding, validation and Markdown reporting.
- `scripts/run_windows_release_gate.ps1/.bat`: Windows release-workstation harness that creates a fresh pinned environment, runs the monolithic pytest suite, builds/verifies the customer package, builds the installer, and prepares the clean-machine kit.
- `scripts/clean_windows_acceptance.ps1/.bat`: PowerShell-only guided clean-Windows acceptance recorder requiring no Python on the end-user test machine.
- `docs/WINDOWS_RELEASE_ACCEPTANCE.md`: exact release-workstation and clean-machine procedure.
- `tests/test_release_harness.py`: cross-platform structural/behavior tests for the evidence recorder and Windows harness safety invariants.

The harness never marks Windows clean-machine gates passed automatically. Actual Windows package/installer execution and clean-machine acceptance remain platform-specific release gates until performed and recorded.

No internet legal/database download/update functionality was added. The database, encrypted vault and working data remain local.
