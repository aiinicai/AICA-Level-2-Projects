# Setup and deployment (for IT, no programming needed)

## What you need
* A Windows PC/server on the office network that stays on during working hours (the "server").
* **Python 3.10 or newer** from python.org. During install tick **"Add python.exe to PATH"**.
* Internet access on the server *only* for the one-time package install.

## One-time install
1. Copy the whole `challan_app` folder to the **server's local disk**, e.g. `C:\challan_app`.
   *Do not* put it on a network share that many people open - only the server runs the program; users use a browser.
2. Double-click **`setup.bat`**. It creates a private Python environment, installs packages and creates the empty database (`instance\challan.db`).
3. Double-click **`start_server.bat`**. Leave the window open. You should see "running on http://0.0.0.0:8080".
4. On the server open `http://localhost:8080`, log in as **admin / admin123** and set a new password when asked.

## Let other users connect
1. Find the server's name or IP: run `ipconfig` (IPv4 address, e.g. 192.168.1.20).
2. Allow port 8080 through Windows Firewall (PowerShell as administrator):
   ```powershell
   New-NetFirewallRule -DisplayName "Challan Register" -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow
   ```
3. Users open `http://192.168.1.20:8080` (or `http://SERVERNAME:8080`). Ask IT for a fixed IP / DNS name and bookmark it.

## First-time configuration (as Admin, menu Admin)
1. **Plants / GSTINs** - add your company's plant(s) with GSTIN, address, signatory. (Put your letterhead logo at `app\static\logo.png`.)
2. **Numbering series** - check the prefix/format (see note below).
3. **Users** - create Requester / Approver users; they must change the initial password at first login.
4. Optional: **Excel upload** the vendor master and historical challans (`samples\` has templates and examples).

> Numbering note: GST allows document numbers of at most 16 characters. `MNRC/2026-27/0001` is 17, so the default style is `MNRC/26-27/0001` (15) and `MRC/26-27/0001` (14). The system refuses any format that could exceed 16.

## Run automatically at start-up (recommended)
Use Windows Task Scheduler: *Create Task* -> Trigger "At startup" -> Action: start program `C:\challan_app\start_server.bat` -> tick "Run whether user is logged on or not" and "Run with highest privileges". (Or install it as a service with NSSM pointing at `venv\Scripts\python.exe run_server.py 8080`.)

## Backups (important)
* Schedule **`backup.bat`** daily in Task Scheduler. It makes a consistent copy of the database in `backups\` (keeps the last 30) even while people are working.
* Copy the `backups` folder to another machine/cloud regularly. To restore: stop the server, replace `instance\challan.db` with a backup file, start the server.
* Also keep `instance\secret.key` (keeps users logged in across restarts; not secret data about challans).

## Updating the program
Stop the server, copy the new `app` folder over the old one (keep `instance` and `backups`), run `setup.bat` again, start the server. The database is kept.

## Moving to PostgreSQL (optional)
1. Install PostgreSQL, create a database and user.
2. `venv\Scripts\pip install psycopg2-binary`
3. Set the environment variable `DATABASE_URL=postgresql://user:password@dbhost/challans` (System settings -> Environment variables), run `flask init-db`, start the server.
   (Existing SQLite data is not copied automatically; re-import via Excel or ask a developer.)

## HTTPS / security
Traffic is plain HTTP on the internal network. If you need HTTPS, place IIS/nginx/Caddy in front as a reverse proxy to port 8080. Keep the server patched and limit access to the office network/VPN.

## Troubleshooting
| Symptom | Fix |
|---|---|
| Others can't open the page | Firewall rule missing, wrong IP, or server asleep - disable sleep. |
| "database is locked" | Very rare; retry. If frequent, move to PostgreSQL. |
| Forgot admin password | On the server: `venv\Scripts\python -c "from app import create_app; from app.extensions import db; from app.models import User; from werkzeug.security import generate_password_hash as g; a=create_app(); c=a.app_context(); c.push(); u=User.query.filter_by(username='admin').one(); u.password_hash=g('Temp@12345'); u.must_change_password=True; db.session.commit()"` |
| Port 8080 in use | `python run_server.py 8090` and use that port. |
