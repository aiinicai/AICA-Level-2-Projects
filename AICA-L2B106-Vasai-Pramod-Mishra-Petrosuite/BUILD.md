# Build instructions (Windows)

Prerequisites: Python 3, Inno Setup.

| Step | Command / action |
|---|---|
| 1. Install dependencies | `cd pyapp` then `py -m pip install -r requirements.txt` |
| 2. Private files (production only) | Copy `license_secret_local.py.example` to `license_secret_local.py` and `auth_local.py.example` to `auth_local.py`, then fill in your real values. Both are git-ignored |
| 3. Build the app | `py -m PyInstaller Petrosuite.spec` (output: `dist\Petrosuite\`) |
| 4. Build the installer | Open `Petrosuite.iss` in Inno Setup Compiler and click Compile (output: `installer_output\Petrosuite_Setup_v1.0.0.exe`) |

Notes:
- `web/app.html` is packed inside the build, so any change to it needs steps 3 and 4 again.
- If `pyinstaller` is not on PATH, use `py -m PyInstaller`.
- Windows Smart App Control may block an unsigned exe. Options: turn it off on the build PC,
  test on another PC, or code-sign the exe.
- Without the two private files, the build uses the demo secret and demo passwords.
  Never distribute such a build to clients.
- `tools/generate_key.py` is for the software owner only; do not ship it in the installer.
