# Deployment Guide – ABC Travel & Expense

## 1. Requirements
* Any Windows 10/11, Windows Server, macOS or Linux machine.
* **Node.js 22 LTS or newer** (includes the built-in SQLite database). The Windows launcher installs it
  automatically through `winget` if it is missing.
* No other software, no npm packages, no separate database server.

## 2. Quick start (single PC / trial)
1. Unzip and open `04_Executable_Application/ABC_Travel_Expense_App`.
2. Windows: double-click **Start_ABC_Travel_App.bat**. macOS: double-click **Start_ABC_Travel_App.command**.
   Linux: `./start_mac_linux.sh`.
3. The browser opens at http://localhost:8080. The first person to sign up becomes the Administrator.
4. Keep the black console window open – it is the server. Close it to stop.

Demo with sample data: **Start_Demo_Mode.bat** → http://localhost:8081, login `admin@abc-demo.com` / `Demo@1234`.

## 3. Office network (LAN)
The server listens on all network cards. Other PCs can open `http://<server-ip>:8080`
(allow port 8080 in Windows Defender Firewall when asked). For phone installation and for security,
use HTTPS as below.

## 4. HTTPS (needed for installing the PWA on phones and other PCs)
Option A – company certificate:
```
set HTTPS_KEY=C:\certs\travel.key
set HTTPS_CERT=C:\certs\travel.crt
set PORT=443
node launch.js
```
Option B – reverse proxy (recommended for internet access): put IIS, Nginx, Caddy or a cloud load
balancer with a valid certificate in front and forward to `http://localhost:8080`.
Example Caddyfile:
```
travel.abc-company.com {
    reverse_proxy localhost:8080
}
```
Option C – **one-click public link (built in):** double-click `Start_Public_Link.bat`.
It installs Cloudflare's free `cloudflared` once (via winget), starts the app and prints a secure link such as
`https://brave-lion-sample.trycloudflare.com`. Share it on WhatsApp/email; employees open it on their phones and tap
**Install App** (iPhone: Share → Add to Home Screen). The link is saved in `PUBLIC_LINK.txt`.
Notes: the quick link changes every time it is restarted and works only while the PC is on and the window is open.
For a permanent address (e.g. `https://travel.abc-company.com`) create a named Cloudflare Tunnel on your company domain
(`cloudflared tunnel login`, `cloudflared tunnel create abc-travel`, `cloudflared tunnel route dns abc-travel travel.abc-company.com`,
`cloudflared tunnel run --url http://localhost:8080 abc-travel`) or host the app on a cloud server.

## 5. Environment variables
| Variable | Default | Meaning |
|---|---|---|
| PORT | 8080 | Port number |
| HOST | 0.0.0.0 | Network interface |
| DB_FILE | data/abc_travel.db | SQLite database file |
| HTTPS_KEY / HTTPS_CERT | – | Enable HTTPS with these PEM files |

## 6. Run as a Windows service (always on)
Use Windows Task Scheduler: *Create Task → Trigger: At startup → Action: Start a program*
`node.exe` with arguments `launch.js --no-browser`, *Start in:* the app folder, *Run whether user is logged on or not*.
(Alternatively NSSM or PM2 can wrap `node launch.js --no-browser`.)

## 7. Data, backup & restore
* All data is in `data/abc_travel.db`; bills and tickets are in `uploads/`.
* Admin → Analytics → **Backup database** downloads a consistent copy at any time.
* Daily backup: copy the `data` and `uploads` folders to a backup drive (schedule with Task Scheduler / robocopy).
* Restore: stop the server, replace `data/abc_travel.db` (delete any `-wal`/`-shm` files) and `uploads/`, start again.

## 8. Security notes
* Passwords are stored as salted scrypt hashes; sessions are random 256-bit tokens that expire after 7 days.
* Repeated failed logins are blocked for 5 minutes and logged.
* Only PDF / image files up to 5 MB are accepted; duplicates are detected by SHA-256 hash.
* Every sign-up, login, failed attempt, logout, employee change and setting change is recorded in `auth_logs`.
* For internet exposure always use HTTPS and keep Node.js updated.
