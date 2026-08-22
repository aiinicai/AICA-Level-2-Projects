# Installation Guide

## The simple way (recommended for everyone)

1. **Install Node.js.** Go to https://nodejs.org, download the **LTS** version for Windows, run the installer, accept the defaults. This is the only thing CA Docs needs that isn't already on a typical Windows PC. Restart the computer after installing.
2. **Copy the `cadocs-app` folder** to the PC that will act as the office "server" (any PC that stays on during office hours — it doesn't need to be special hardware). For example, `C:\CADocs\`.
3. **Double-click `setup.bat`** inside that folder. A black window will open and run for a few minutes — it installs everything, sets up the database, and builds the application. When it says "Setup complete!", you're done. You only need to do this once (or again later if the application is updated).
4. **Double-click `start.bat`.** Your browser opens automatically to `http://localhost:4000` with CA Docs running.
5. Click **Manage Formats** (top right) and log in with the default password `ChangeMe123!` — then immediately go to Settings and change it (see `docs/ADMIN_MANUAL.md`).
6. Import one of the sample templates from `sample-templates\` to see the whole pipeline (import → placeholder detection → generation → PDF) work end to end.

To make CA Docs available to other PCs on the office network, or start automatically on boot, see "Run CA Docs automatically" and "Make it reachable from other PCs" below.

If `setup.bat` stops with an error, it prints what went wrong before pausing — read that message first. The rest of this document explains what each step does manually, for troubleshooting or for anyone who prefers to run the commands themselves.

---

## Run CA Docs automatically (so nobody has to double-click start.bat every morning)

1. Press `Win + R`, type `shell:startup`, press Enter — this opens your Windows Startup folder.
2. Right-click `start.bat` in the CA Docs folder → **Create shortcut**.
3. Drag that shortcut into the Startup folder you opened in step 1.

Now CA Docs starts automatically whenever this PC turns on or a user logs in. (For a more robust "runs even when nobody is logged in" setup on a dedicated server PC, see the Windows Service option in `docs/DEPLOYMENT.md`.)

## Make it reachable from other PCs on the office LAN

By default, `http://localhost:4000` only works on the same PC CA Docs is running on. For every staff PC to reach it:

1. Find this PC's local IP address: open Command Prompt, run `ipconfig`, note the "IPv4 Address" (e.g. `192.168.1.50`).
2. On every staff PC, browse to `http://192.168.1.50:4000` (using the actual IP you found) instead of `localhost`.
3. You may need to allow this through Windows Firewall — see `docs/DEPLOYMENT.md` for the exact command.

For a static IP, always-on service setup, and firewall rules in full detail, see `docs/DEPLOYMENT.md`.

---

## What `setup.bat` does, step by step (for troubleshooting or manual setup)

If you'd rather run these yourself, or need to know what to check when something fails:

### 1. Install dependencies
```
cd backend
npm install
cd ../frontend
npm install
```

### 2. Configure the backend
```
cd backend
copy .env.example .env
```
Open `.env` in Notepad if you want to change anything before first run — most importantly `DEFAULT_ADMIN_PASSWORD` (the initial Manage Formats password) and `SOFFICE_PATH` (see PDF conversion note below). None of this is required to get started; sensible defaults are already set.

### 3. Set up the database
```
cd backend
npx prisma db push
npx prisma generate
npm run seed
```
`db push` syncs the database structure to match `prisma/schema.prisma`, creating any missing tables — safe to re-run any time, including after future updates to the application.

### 4. Build both parts
```
cd backend
npm run build

cd ../frontend
npm run build
```

### 5. Merge the frontend into the backend
```
xcopy /e /i /y frontend\dist backend\public
```
This is the step that lets one program serve everything — the backend serves the built frontend directly, so there's only one address (`http://localhost:4000`) and nothing to configure about how the frontend finds the backend.

### 6. Run it
```
cd backend
node dist\server.js
```
Then open `http://localhost:4000` in a browser.

---

## Optional: PDF generation (LibreOffice)

Word-to-PDF conversion requires LibreOffice. This is **optional** — everything else works without it, and Word (.docx) downloads always work regardless. To enable PDF downloads:

1. Install LibreOffice from https://www.libreoffice.org/download/download/ (the "Still" version).
2. Note the install path — usually `C:\Program Files\LibreOffice\program\soffice.exe`.
3. Open `backend\.env` in Notepad and set `SOFFICE_PATH` to that path.
4. Restart CA Docs (close the "CA Docs - server" window, run `start.bat` again).

## Updating CA Docs later

When you receive an updated copy of the application, copy the new files over the old folder (keeping your `backend\.env` and `backend\data\cadocs.db` — don't overwrite those), then run `setup.bat` again to rebuild.
