# Deployment Guide — Windows LAN Environment

This covers the **advanced/production** version of running CA Docs: as a background Windows Service that starts on boot even if nobody logs in, with a fixed LAN address every staff PC can rely on.

**If you just want it running reliably for a small office**, the "Run CA Docs automatically" section in `docs/INSTALLATION.md` (a Startup-folder shortcut) is usually enough and requires no extra software. Come back to this document for the more robust always-on-service setup, or if you want a fixed address for staff to bookmark.

CA Docs runs as a **single program on a single port** (the backend serves the frontend directly — see `docs/ARCHITECTURE.md`), so there's only one service to manage here, not two.

## 1. Fix the server PC's IP address

Give the server PC a static local IP (or a DHCP reservation) via your router settings, e.g. `192.168.1.50`. Every staff PC will point their browser at this address, so it must not change.

## 2. Run CA Docs as a Windows Service (via NSSM)

Running it via `start.bat` means it stops the moment someone closes that window or the PC signs out. Use **NSSM** (Non-Sucking Service Manager) to run it as a proper background service instead.

1. Download NSSM: https://nssm.cc/download, extract `nssm.exe` (64-bit) to e.g. `C:\CADocs\nssm.exe`.
2. Make sure you've already run `setup.bat` at least once (see `INSTALLATION.md`) so `backend\dist` and `backend\public` exist.
3. Open an **Administrator** Command Prompt and run:
   ```
   C:\CADocs\nssm.exe install CADocs
   ```
4. In the dialog that opens:
   - **Path**: `C:\Program Files\nodejs\node.exe`
   - **Startup directory**: `C:\CADocs\backend`
   - **Arguments**: `dist\server.js`
5. Click **Install service**.
6. Start it and set it to launch automatically on boot:
   ```
   net start CADocs
   ```
   Then open `services.msc`, find "CADocs", and set **Startup type** to **Automatic**.

## 3. Open the Windows Firewall for LAN access

By default Windows Firewall blocks inbound connections from other PCs. Run (as Administrator):
```
netsh advfirewall firewall add rule name="CADocs" dir=in action=allow protocol=TCP localport=4000
```

## 4. Point staff PCs at the server

On every staff PC, bookmark:
```
http://192.168.1.50:4000
```
(substitute your server's actual static IP). No installation is needed on staff PCs — any modern browser (Edge, Chrome, Firefox) works.

## 5. Reverse-proxy option (optional, cleaner URLs)

If you'd rather staff type `http://cadocs` instead of an IP:port, install IIS with URL Rewrite + Application Request Routing, or a lightweight option like `Caddy`, to proxy port 80 → 4000 and register `cadocs` as a local DNS name on your office router. This is optional polish, not required for a working deployment.

## 6. Backups

Automatic backups run inside the CA Docs process on the cron schedule set in **Settings → Backup Frequency** (default: daily at 9 PM). Because this depends on the service being *running* at that time, make sure the server PC itself is not shut down overnight, or adjust the schedule to office hours.

For extra safety, also point Windows' own File History or a scheduled `robocopy` job at the `Backup Folder` configured in Settings, to copy backup ZIPs off the server PC onto a separate drive or NAS — a backup that lives only on the machine it protects is not a real backup.

## 7. Updating the application later

Copy the new source files over the old folder (keeping `backend\.env` and `backend\data\cadocs.db`), then:
```
cd C:\CADocs\backend
net stop CADocs
```
Run `setup.bat` again from the CA Docs root folder (it will reinstall dependencies, apply any new database migrations, and rebuild everything, including copying the frontend into `backend\public`). Then:
```
net start CADocs
```

## 8. Health check

`http://192.168.1.50:4000/api/health` should return `{"success":true,"status":"ok"}`. Point a simple uptime check or scheduled task at this URL if you want an early warning the service has stopped.
