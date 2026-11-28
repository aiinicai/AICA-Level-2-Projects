# RealEstate 360 — User, Administrator & Windows Packaging Manual

## 1. Overview
RealEstate 360 is a Monthly MIS, IFRS Financial Reporting, Project Cost Control, Sales & Inventory, Collections, Construction Earned Value, and Cash Flow Forecasting system designed for real estate developers (default currency: OMR with 3-decimal precision).

## 2. Monthly MIS Closing Workflow
1. Open the target period (`2026-11`).
2. Navigate to **Data Upload & GL Map** to upload ERP Trial Balances (`.xlsx` / `.csv`) and download standardized templates for supporting schedules.
3. Map any unmapped accounts using the **GL Mapping Wizard** (saved for subsequent months).
4. Review **Financial MIS & IFRS** to confirm `0.000 OMR` Trial Balance reconciliation and intercompany eliminations.
5. Collect departmental comments and submit/approve Maker-Checker adjustments under **MIS Workflow & Locks**.
6. Export the **Excel MIS Pack**, **Board PDF**, or **PowerPoint (.pptx)** deck under **Reports & Exports**, then **Lock** the period.

## 3. Running Desktop Standalone & Building Windows Executables (Windows 10/11 x64)
1. **Run Standalone from Python (No Node.js Required)**:
   - Run `python desktop/main.py` directly from the project root.
   - `desktop/main.py` starts an embedded local HTTP + SQLite API server (`sqlite3` + `desktop/web_dist` + `desktop/seed_dataset.json`), opens the native PySide6 desktop window (or default browser if PySide6 is not installed), and waits for the local server before loading.
2. **Build `RealEstate360.exe`, `RealEstate360_Portable.zip`, `RealEstate360_Setup.exe`, and `RealEstate360_Update.exe`**:
   - Double-click `desktop\build_windows.bat` or run `powershell -ExecutionPolicy Bypass -File desktop\build_windows.ps1` on a Windows 10/11 build host with Python 3.11+ (plus Inno Setup 6 for setup/update `.exe` installers).
   - Output installers and binaries are written to `desktop\release\`.
3. **Data Preservation**:
   - User data is stored in `%LOCALAPPDATA%\RealEstate360\data\realestate360.db`, separate from `{app}` executables so upgrades and repairs preserve all business records.

## 4. Troubleshooting
- **Connection Refused (`ERR_CONNECTION_REFUSED`)**: Resolved in `desktop/main.py` via the embedded `ThreadingHTTPServer` + `wait_for_server()` startup check. Verify `desktop/web_dist/index.html` and `desktop/seed_dataset.json` are present, or pass `--port 3360` if another process occupies the default port.
- **Publication Blocked**: Ensure Trial Balance Debits equal Credits within the configured materiality threshold and zero GL accounts remain `Unmapped`.
- **Database Integrity**: Check `/api/health` or use **Security, Backup & Admin** to create or restore a `.db` snapshot.
- **Online AI Commentary**: Requires `GEMINI_API_KEY` configured in server environment secrets. The deterministic offline CFO engine works without internet access.
