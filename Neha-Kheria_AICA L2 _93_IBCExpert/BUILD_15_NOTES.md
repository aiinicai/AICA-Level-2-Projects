# Build 15 Notes — Python 3.14 Compatibility

Application version: `0.1.15-dev`. Database schema/migration version unchanged.

This build is a compatibility/release-target update only. Completed business functionality was not redesigned or reworked.

Changes:
- Windows release target is now explicitly **64-bit CPython 3.14.x**.
- Refreshed pinned packages that materially affect Python 3.14 support, including FastAPI, PyWebView, cryptography, Argon2, Pillow, PyMuPDF, ReportLab, pytest and PyInstaller.
- PyInstaller pin updated to `6.22.3` (Python 3.14 support exists from PyInstaller 6.15+).
- PyWebView updated to 6.2.1; on Windows its pythonnet dependency resolves to current Python-3.14-capable releases when the wheelhouse is prepared.
- Added `scripts/validate_python_target.py`; Windows build/release scripts fail closed unless CPython 3.14 x64 is selected.
- Production wheelhouse preparation now requires Python 3.14 so it cannot accidentally produce wheels for a different minor version.
- First-run bootstrap now checks the **installed distribution version against the exact pin**, not merely whether an import is present; stale incompatible packages are therefore upgraded/replaced during dependency setup.
- PyMuPDF OCR integration now imports `pymupdf` directly while preserving the existing local `fitz` alias in code.
- Added regression tests for the Python 3.14 pins, release-script guard, and exact-version bootstrap behavior.

Security/offline posture is unchanged:
- no automatic internet legal/database import or updater;
- all imports remain explicit user actions;
- primary SQLite database, encrypted vault and working data remain local;
- future internet update capability remains disabled and unimplemented.

Release status:
- Source/regression validation can be performed in the build environment, but the product is **not yet claimed as Windows/Python-3.14 release validated**.
- The next exact task remains running the Windows release/acceptance harness, now under CPython 3.14 x64.

Build-environment validation:
- Python `compileall` succeeded for application, tests, scripts, owner tools and launchers.
- 23 compatibility/packaging/bootstrap-focused tests passed.
- 15 document/web/desktop/security regression tests passed.
- `test_backup.py` passed 3/3 separately.
- The available sandbox is Python 3.13/Linux, so these checks do not replace the required CPython 3.14/Windows release gate.
