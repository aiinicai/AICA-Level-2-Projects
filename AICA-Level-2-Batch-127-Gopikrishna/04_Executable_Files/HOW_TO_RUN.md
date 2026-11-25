# How to run (Windows)

Requirements: Python 3.11 or newer; LibreOffice (free) for the Excel formula check. No internet is needed after setup.

1. Copy `cashflow_forecast` to a local folder (not inside OneDrive for a server).
2. In PowerShell, in that folder:

   ```powershell
   py -3 -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   powershell -ExecutionPolicy Bypass -File make_shortcuts.ps1 -Desktop
   ```

3. Double-click **Cash Flow Forecast - Demo** for a copy filled with synthetic data (sign-in details are shown on
   the sign-in page), or **Cash Flow Forecast** for an empty copy: the browser asks you to create the first Admin.
   The app runs with no window; **Stop Cash Flow Forecast** stops it. `start_app.bat` / `start_demo.bat` do the same.
4. Tests: `.venv\Scripts\python.exe -m pytest -q` (167 tests).

Intranet hosting with HTTPS, backups and password recovery: see `cashflow_forecast/README.md`.
