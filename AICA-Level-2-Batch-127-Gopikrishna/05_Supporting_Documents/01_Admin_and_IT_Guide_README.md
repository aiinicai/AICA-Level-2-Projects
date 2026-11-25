# Cash Flow Forecast

A local web app that replaces the daily Excel cash-flow review. It forecasts working capital in
10-day lots over 2–3 months, lets finance staff hold, defer or adjust items on screen, and exports an
Excel workbook with live formulas that is checked against the screen before anyone can download it.

- Runs on one PC or an intranet server. No cloud service, no paid API, no outbound network calls.
- Python 3.11+, FastAPI, SQLite, Jinja2/HTMX/Alpine/Bootstrap served locally.
- Currency OMR (3 decimals). Other currencies need a manual rate; only OMR flows are forecast.
- **Synthetic data only in this repository.** Never commit real company data.

For finance staff, see the **[User manual](docs/USER_MANUAL.md)**. File layouts are in
[docs/input_formats.md](docs/input_formats.md); the report layout is in [docs/forecast_layout.md](docs/forecast_layout.md).

---

## 1. Install (once per PC)

1. Install **Python 3.11 or later** from python.org (tick "Add python.exe to PATH").
2. Put this folder somewhere **outside OneDrive**, e.g. `C:\CashFlowApp`. OneDrive syncing a live database can damage it.
3. In PowerShell, in that folder:
   ```powershell
   py -3 -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
   (This is the only step that downloads anything. For a PC with no internet, run
   `pip download -r requirements.txt -d wheels` elsewhere, copy `wheels\`, then
   `pip install --no-index --find-links wheels -r requirements.txt`.)
4. Install **LibreOffice** (free) for the Excel formula check:
   `winget install --id TheDocumentFoundation.LibreOffice -e`, or the installer from libreoffice.org.
   Without it the app works, but every Excel export is blocked (by design).

## 2. Start

Once, run `powershell -ExecutionPolicy Bypass -File make_shortcuts.ps1` (add `-Desktop` for Desktop copies).
Then double-click the **Cash Flow Forecast** shortcut. The app starts in the background with **no window**
and opens in the browser. The first time, the browser asks you to create the first Admin (only possible on
this PC). Double-clicking again just reopens the browser. **Stop Cash Flow Forecast** stops it.

| File | What it does |
|---|---|
| **Cash Flow Forecast** shortcut / `start_app.bat` | Start the app hidden and open the browser (the .bat flashes a window for a moment; the shortcut does not) |
| **… - Demo** shortcut / `start_demo.bat` | A separate demo copy with synthetic data on `http://localhost:8001`; its sign-in details are shown on the sign-in page (this PC only) |
| **Stop …** shortcuts / `stop_app.bat`, `stop_demo.bat` | Stop the app / the demo |
| `make_shortcuts.ps1` | Create the shortcuts above |
| `reset_password.bat` | Forgotten password (including the Admin's): new temporary password, account unlocked |
| `backup_now.bat` | Encrypted backup now |
| `restore_backup.bat` | Restore a backup (stop the app first) |
| `setup_server.ps1` | Make this PC the intranet server (HTTPS, firewall, start with Windows) |

The hidden server writes its messages to `instance\logs\app.log` (the previous run: `app.previous.log`);
start-up problems appear in a message box. To watch it live, stop it and run
`.venv\Scripts\python.exe run.py` in a console instead. Do not start `run.py` from IDLE: it uses the system
Python, which does not have the libraries.

## 3. Intranet server (other users sign in with a link)

The app refuses to listen on the network without HTTPS, so passwords never travel in clear text.

1. Pick one PC or server that stays on. Install as in section 1 (outside OneDrive), start it once with
   the shortcut to create the first Admin in the browser, then stop it.
2. **Certificate**
   - Best: ask IT for a certificate from the company CA.
     `.venv\Scripts\python.exe scripts\make_cert.py --csr --name cashflow.yourcompany.local`
     makes `instance\certs\server.key` (stays on the server) and `server.csr` (send to IT).
     Save IT's signed certificate as `instance\certs\server.crt`.
   - Trial: `.venv\Scripts\python.exe scripts\make_cert.py --self-signed` (browsers warn until trusted).
3. In PowerShell **as Administrator**, in the app folder:
   ```powershell
   .\setup_server.ps1 -Port 8443 -BackupCopyDir "\\fileserver\finance\cff_backups"
   ```
   It writes `.env`, opens port 8443 for Domain/Private networks and registers the scheduled task
   "Cash Flow Forecast" that starts the app with Windows. It prints the link, e.g.
   `https://server-name:8443`. Undo with `.\setup_server.ps1 -Remove`.
   (If PowerShell blocks the script: `powershell -ExecutionPolicy Bypass -File .\setup_server.ps1`.)
4. Add users in **Admin → Users** and send them the link. Give each temporary password in person.

Stop / start the server: `Stop-ScheduledTask -TaskName "Cash Flow Forecast"` /
`Start-ScheduledTask -TaskName "Cash Flow Forecast"`.

## 4. Settings

Deployment settings are environment variables or lines in `.env` (copy `.env.example`). Business settings
(lots, horizon, approval, alert threshold…) are changed by an Admin in **Admin → Settings** and audited.

| Setting | Default | Meaning |
|---|---|---|
| `CFF_HOST`, `CFF_PORT` | 127.0.0.1, 8000 | Address and port. Any address other than 127.0.0.1 needs HTTPS. |
| `CFF_SSL_CERTFILE`, `CFF_SSL_KEYFILE` | – | Certificate and key (both, or neither). |
| `CFF_INSTANCE_DIR` | `instance` | Database, uploads, exports, backups, keys. |
| `CFF_SECRET_KEY` | generated | Session signing key (`instance\secret.key`). |
| `CFF_BACKUP_PASSPHRASE` | generated | Backup encryption passphrase (`instance\backup.key`). |
| `CFF_SESSION_MAX_AGE_MINUTES` | 480 | Sign-in lasts this long. |
| `CFF_UPLOAD_MAX_MB` | 10 | Largest upload. |
| `CFF_AUTO_BACKUP` / `CFF_BACKUP_KEEP` | true / 30 | Daily backup while running / how many to keep. |
| `CFF_BACKUP_COPY_DIR` | – | Second location for every backup. **Set this.** |
| `CFF_SOFFICE_PATH` | found automatically | LibreOffice, if installed in an unusual place. |
| `CFF_UTC_OFFSET_HOURS` | 4 | Local time shown on screens (Oman). |

## 5. Backups and restore

- An **encrypted** backup (database + every uploaded file) is made automatically once a day while the app
  runs, and on demand (**Admin → Backups → Back up now**, or `backup_now.bat`). The newest 30 are kept in
  `instance\backups`; set `CFF_BACKUP_COPY_DIR` so each one is also copied off the PC.
- Encryption: key derived with scrypt from the backup passphrase; Fernet (AES + HMAC), so a changed or
  damaged backup is refused rather than restored.
- **Keep a copy of `instance\backup.key` (or your `CFF_BACKUP_PASSPHRASE`) away from the server**, e.g. in
  the company password safe. Without it no backup can be opened.
- Check a backup: `.venv\Scripts\python.exe -m app.cli verify-backup <file>`.
- Restore: stop the app, run `restore_backup.bat`, pick the file, type `RESTORE`. The current data is backed
  up first, so a restore can itself be undone.
- Moving to a new server: install, copy `instance\backup.key` (and `secret.key`) into the new `instance\`,
  restore the latest backup.

## 6. Security summary

| Requirement | How |
|---|---|
| Passwords | Argon2id; at least 10 characters, letters with numbers/symbols, not the user name. Lock after 5 failures for 15 minutes. |
| Sessions | Signed cookie, SameSite strict, Secure under HTTPS, ended by a password change or reset. CSRF token on every change. |
| HTTPS | Required for any network address; HSTS sent. |
| Roles | Admin, Preparer, Viewer; Approver when approval is on. Nobody approves their own change. |
| Uploads | `.xlsx` / `.csv` only, size and row limits, macro-enabled or macro-containing workbooks refused, zip-bomb checks, SHA-256 of every file logged. |
| Excel export | Live formulas, recalculated in LibreOffice and compared cell by cell; blocked on any difference. SHA-256 logged. |
| Audit | Append-only log of sign-ins, uploads, changes, approvals, exports, settings, backups; viewer with CSV download. |
| Secrets | None in code: generated into `instance\` (git-ignored) or given in `.env`. |
| Backups | Encrypted; tamper-evident. |
| Network | No outbound calls; all scripts and styles served locally; LibreOffice runs with update checks off. |

## 7. Updating the app

Stop it, make a backup, replace the program files (keep `instance\`, `.env`, `.venv`), then
`.venv\Scripts\python.exe -m pip install -r requirements.txt` and start again. The database is upgraded
automatically on start.

## 8. Troubleshooting

| Problem | Fix |
|---|---|
| `No module named 'pydantic'` | You started `run.py` with the system Python (e.g. IDLE). Use `start_app.bat`. |
| Typing the password shows nothing | Normal: passwords are hidden. Type it and press Enter. |
| Forgot a password | Admin: **Admin → Users → Reset password**. Forgotten Admin password: `reset_password.bat` on the server. |
| Account locked | Wait 15 minutes, or Admin → Users → Unlock. |
| Export blocked: formula check could not run | Install LibreOffice (section 1), or set `CFF_SOFFICE_PATH`. |
| Export blocked: N differences | The page lists each cell. Please report it: the app refused to release a workbook that disagrees with the screen. |
| Other PCs cannot open the link | Check the scheduled task is running, the firewall rule exists, and the link uses `https://` and the right port. |
| Browser warns about the certificate | Self-signed certificate: ask IT for a company-CA certificate (section 3). |

## 9. Developers

```powershell
.venv\Scripts\python.exe -m pytest -q
```
`tests/test_acceptance.py` holds the specification's acceptance tests, run end to end through the web app and
the Excel check. Tests that need LibreOffice are skipped where it is not installed.

Useful console commands (`.venv\Scripts\python.exe -m app.cli <command>`): `forecast`, `pdcs`, `holds`,
`hold`, `release`, `export`, `backup`, `list-backups`, `verify-backup`, `restore-backup`, `list-users`,
`reset-password`, `create-user`, `import`, `import-folder`, `show-settings`.

| Folder | Contents |
|---|---|
| `app/core` | settings, money helpers |
| `app/models` | database tables |
| `app/importers` | file reading, header matching, validation |
| `app/engine` | lots and the forecast engine (pure functions) |
| `app/services` | overrides and holds, auth, backups, exports, snapshots, audit |
| `app/export` | Excel workbook (XlsxWriter) and the LibreOffice check |
| `app/routers`, `app/templates`, `app/static` | web screens |
| `input_templates/` | blank upload templates |
| `synthetic_data/` | synthetic test files (day 1, day 2, acceptance) |
| `scripts/` | template, synthetic-data and certificate generators |
