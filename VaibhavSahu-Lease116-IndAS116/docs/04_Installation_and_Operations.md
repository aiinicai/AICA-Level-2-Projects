# Lease116 — Installation and Operations

| Item | Detail |
|---|---|
| Document | 04 — Installation, backup, upgrade and troubleshooting |
| Supported | Windows 10 / 11, x64 and ARM64 (Snapdragon); 8 GB RAM recommended; ~1.5 GB disk for the Python environment |
| Internet | Needed once for Setup (Python packages). Day-to-day use is fully offline |

## 1. Where things live

| Item | Location | Notes |
|---|---|---|
| Program (this folder) | e.g. `Documents\Ind AS 116 Lease App` | Can be moved; re-run Setup after moving to refresh the shortcuts |
| Python environment | `%LOCALAPPDATA%\Lease116\venv` | Private to Lease116; does not affect other Python installations |
| **Data** — database, uploaded agreements, backups | `%LOCALAPPDATA%\Lease116\data` | Kept outside OneDrive / Documents so a live database is never synced mid-write. Override with the environment variable `LEASE116_DATA_DIR` |
| Setup log | `%LOCALAPPDATA%\Lease116\setup.log` | |
| Server log | `%LOCALAPPDATA%\Lease116\logs\server.log` | Written when Lease116 is started with `Lease116.exe` (tray icon → *Show log file*) |

## 2. Install

1. Double-click **`Setup.bat`** in the program folder.
2. Setup finds a 64-bit Python 3.10–3.13 (x64 preferred). If none is found — or on Windows-on-ARM where only ARM64 Python exists — it installs **Python 3.12 x64** for the current user with `winget` (no administrator rights needed). x64 Python runs on ARM64 Windows through Windows' built-in emulation and gives access to every OCR / computer-vision package.
3. It creates the private environment, installs the packages (`requirements.txt`, then the document-intelligence extras and the optional Claude connector), runs a self-test and creates **Desktop** and **Start-menu** shortcuts.
4. Typical duration 5–15 minutes. Re-running Setup is safe (repair / upgrade). Options: `Setup.bat -Rebuild` (recreate the environment), `-SkipOCR`, `-NoShortcut`.

## 3. Start and stop

| Action | How |
|---|---|
| Start | Double-click the desktop shortcut **Lease116** (or `Lease116.exe` in the program folder). No console window opens: a Lease116 icon appears next to the clock and the browser opens http://127.0.0.1:8116 |
| Already running? | Starting again just opens the browser |
| Stop | Right-click the Lease116 icon next to the clock → **Stop Lease116** (the icon may be under the **^** arrow) |
| Alternative | `Start.bat` starts Lease116 in a console window; close that window (or press Ctrl+C) to stop it |
| Access | Only from this PC (the server listens on 127.0.0.1) |

## 4. Optional components

| Component | Purpose | How |
|---|---|---|
| Local AI model | Better reading of unusual clauses, fully offline | Install **Ollama** or **LM Studio**, download an instruct model (e.g. `qwen2.5:7b-instruct`), start it, then *Settings → AI engine → Detect local AI servers* and pick the model |
| Claude API | Highest-accuracy reading for complex agreements | *Settings → AI engine → Allow cloud AI* + API key. Each document still needs the user's explicit consent, which is audit-logged. Check client confidentiality terms first |
| Tesseract OCR | Second OCR engine | Install Tesseract for Windows; Lease116 detects it automatically |

## 5. Backup, restore, upgrade

| Task | Steps |
|---|---|
| Backup | *Settings → System → Back up database and documents now* → a ZIP in `%LOCALAPPDATA%\Lease116\data\backups`. Copy it to your practice's backup location |
| Restore | Stop Lease116; extract `lease116.db` and the `documents` folder from the backup ZIP into `%LOCALAPPDATA%\Lease116\data` (keep a copy of the current files); start Lease116 |
| Upgrade | Replace the program folder with the new version; run `Setup.bat`; start. The database is upgraded automatically on start-up; calculation runs already approved are immutable |
| Upgrade to v1.1 (lessor module) | No database change. Lessor leases calculated before v1.1 show a *recalculate* banner and are listed in *Reports → Missing Data / Exception Report*: recalculate Draft leases; reopen approved ones (reason: recalculation with lessor engine 2.0), recalculate and approve again. The demonstration portfolio in an existing database is not changed (DEMO-012 appears only when the demo is loaded into a new workspace) |
| Uninstall | Delete the program folder, the shortcuts and `%LOCALAPPDATA%\Lease116\venv`. Delete `%LOCALAPPDATA%\Lease116\data` only after taking a backup |

## 6. Security and confidentiality controls

* Local-only web server; passwords hashed (PBKDF2-SHA256, 200,000 iterations); 12-hour sessions.
* Maker-checker with segregation of duties; period locks; reason-mandatory reopening.
* Audit trail of every change, approval, export, login and cloud-AI consent.
* Agreements are processed offline unless cloud AI is explicitly enabled and consented per document.
* Change the default `admin` password at first sign-in; create named users for each team member.

## 7. Troubleshooting

| Symptom | Resolution |
|---|---|
| Browser shows "This site can't be reached — 127.0.0.1 refused to connect" | Lease116 is not running. Start it with the desktop shortcut / `Lease116.exe`, then reload the page |
| Lease116.exe reports that it could not start | The message shows the last lines of the server log; the full log is `%LOCALAPPDATA%\Lease116\logs\server.log`. Run `Setup.bat` to repair the environment if a package is reported missing |
| Setup says Python was not found and winget is unavailable | Install Python 3.12 (64-bit, x64) from python.org, tick "Add python.exe to PATH", re-run Setup |
| "Port 8116 is used by another program" | Close the other program, or set the environment variable `LEASE116_PORT` to a free port (e.g. 8117) before starting |
| Scanned PDFs return little text | Check *Settings → AI engine → This computer*: OCR engines should list `rapidocr`. If not, run `Setup.bat -Rebuild`; on ARM64 ensure x64 Python was installed |
| Browser shows an old screen after an upgrade | Press Ctrl+F5 once |
| Forgotten admin password | Another administrator can reset it (*Settings → Users & roles*). If no administrator is available, restore from a backup or contact your IT support |
