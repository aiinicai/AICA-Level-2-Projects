# Sample Advisory Lead and Meeting Tracker

Sample Advisory Private Limited, www.example.com

One code base, three ways to run it:

| Version | What it is | Where data is kept |
|---|---|---|
| Desktop app | Windows, Mac plus Linux app built with Electron | SQLite database on the computer, daily backups |
| Team server | Small Node server for the office network; everyone shares one database | SQLite database on the server, daily backups |
| PWA | Installable web app (desktop, Android, iPhone), works offline | On the device (browser storage), synced to the team server when it is served from there |

## Folder layout

```
src/main.js        Electron main process: window, menus, native save dialogs, PDF export, backups
src/preload.js     Safe bridge between the window and the main process
src/db.js          SQLite storage (sql.js, no native build needed) shared by desktop plus server
src/gcal.js        Google Calendar API sync (OAuth for installed apps, PKCE, loopback)
server/server.js   Team server: REST API plus static hosting of the PWA
app/               The tracker itself (index.html) plus PWA manifest, service worker, icons
build/             App icons for installers
test/smoke.js      Automated check of the desktop app
```

## 1. Desktop app

Quickest route on Windows: unzip **Sample Advisory Lead and Meeting Tracker 1.0.0 win.zip** anywhere (for example `C:\Sample Advisory Tracker`) and run **Sample Advisory Lead and Meeting Tracker.exe**. No installation needed. Windows SmartScreen may warn because the app is not code signed: choose More info, then Run anyway.

From source (needs Node.js 20 LTS or newer from nodejs.org):

```
npm install
npm start
```

Build a proper installer with Start menu plus desktop shortcuts. Run on the target platform:

```
npm run dist:win      (Windows installer, run on Windows)
npm run dist:mac      (Mac .dmg, run on a Mac)
npm run dist:linux    (Linux AppImage)
```

The installer appears in the `dist` folder.

**What the desktop version adds**
* Every entry plus edit is written to a SQLite database with an activity log of each save.
* Automatic daily backup (last 30 kept); File menu, Back up database now; Restore a backup from Reports and export.
* Excel, Word, PDF plus .ics files save through a normal Save As window; PDFs are generated directly, no print window.
* Direct Google Calendar sync through the Google API (section 4).
* Entries made earlier in the browser version on the same computer are carried into the database on first launch.

**Data location**
* Windows: `%APPDATA%\Sample Advisory Lead and Meeting Tracker\dealflow-tracker.sqlite`
* Mac: `~/Library/Application Support/Sample Advisory Lead and Meeting Tracker/`
* Linux: `~/.config/Sample Advisory Lead and Meeting Tracker/`

Backups sit in the `backups` folder next to the database. Reports and export, Open data folder takes you there.

## 2. Team server (shared database for the office)

On an always on office computer with Node.js installed:

```
npm install --omit=dev
npm run server
```

Then open `http://<that computer's IP>:8080` from any computer on the network. Everyone works on the same leads, meetings plus investors; changes from colleagues load automatically every 45 seconds, and a save that would overwrite a colleague's newer change is refused with the latest data reloaded.

Settings (environment variables):

| Variable | Default | Purpose |
|---|---|---|
| PORT | 8080 | Port to listen on |
| HOST | 0.0.0.0 | Network interface |
| DATA_DIR | server/data | Database plus backups folder |
| TRACKER_USER plus TRACKER_PASS | not set | Require a login for the whole app |

Windows example with a login:

```
set TRACKER_USER=sample-advisory
set TRACKER_PASS=choose-a-strong-password
npm run server
```

Keep the server on the office network. To reach it from outside, put it behind HTTPS (for example Caddy, IIS reverse proxy, Cloudflare Tunnel) with the login switched on.

## 3. PWA (installable app)

The `app` folder is a complete Progressive Web App: manifest, service worker for offline use, icons plus shortcuts to Today's actions plus Meeting tracker.

Browsers only allow installation from **HTTPS** (`http://localhost` also counts). Options:

1. **Team server** (section 2). On the server computer open `http://localhost:8080` and choose Install. For phones plus other computers, serve it over HTTPS as described above; the installed app then shares the team database.
2. **Private static hosting** of the `app` folder on any HTTPS host your firm controls (company web server, IIS, a password protected site). Data then stays on each device.

**Important:** `index.html` contains the full tracker data including contact numbers plus emails. Never put it on a public website. Use a private, password protected location only.

To install: open the site in Chrome, Edge, Brave (desktop, Android) and click **Install as app** in the sidebar, alternatively the install icon in the address bar. On iPhone plus iPad use Safari, Share, Add to Home Screen.

## 4. Google Calendar sync through the API (desktop app)

Every version has Add to Google Calendar links, Gmail invite drafts plus .ics export. The desktop app can also push meetings straight into your calendar and keep them updated. One time setup, about five minutes:

1. Go to console.cloud.google.com, sign in with the Google account that owns the calendar, create a project (for example Sample Advisory Tracker).
2. APIs and Services, Library: enable **Google Calendar API**.
3. APIs and Services, OAuth consent screen: user type **Internal** for a Google Workspace domain, otherwise **External**; add your own email under Test users.
4. APIs and Services, Credentials, Create credentials, **OAuth client ID**, application type **Desktop app**. Copy the client ID plus client secret.
5. In the tracker open Reports and export, Google Calendar sync (API), paste both, click Connect Google Calendar, then approve in the browser window that opens.

After that: Sync upcoming meetings, Sync all scheduled meetings, a Sync to Google now button on each meeting. Tick Email invitations to attendees to have Google send invitations from your Gmail. Changing a meeting in the tracker and syncing again updates the same Google event. The refresh token is encrypted with the Windows, Mac keychain before it is stored.

## 5. Google Drive sync, deal pipeline plus automation (version 1.1)

**Drive sync.** Reports and export, Google account card: Connect (or Disconnect then Connect if you connected before 1.1, so Google asks for Drive access too; enable the **Google Drive API** in the same Cloud project). Then the Google Drive sync card: paste the shared folder link, Start syncing. Each device writes its own `journal_<user>_<device>.json`; every device merges all of them. n8n writes `journal_n8n_automation.json` into the same folder.

**Deal pipeline.** A new view shows engaged clients from Prospect to merchant banker appointed. Set a lead's stage in its panel. Prospect plus Data complete are sent to n8n (it creates the project code name plus client folder, or starts the information memorandum); later stages, code names, Drive links plus document progress come back from n8n through Drive sync.

**Generate mandate.** On a lead at Prospect, Generate mandate collects the legal details plus both fee inputs and sends them to n8n, which runs the strategic advisory mandate letter skill through Claude, emails PC for approval, then sends the PDF to the client. The Anthropic API key lives only in n8n, never in this app.

**Automation settings.** Reports and export, Automation: n8n address, header name plus shared secret (same values as the Sample Advisory tracker webhook secret credential in n8n), plus the emails behind PC, DS, VR. In the desktop app the secret is encrypted with the operating system keychain.

## 6. Updating the source data

The original Investor_Tracker.xlsx snapshot is built into `app/index.html`; all work since then lives in the database. Reports and export, Download full workbook gives an up to date Excel copy including the Associates sheet in its original layout with every dated update column.

## 7. Checks

```
npm test
```

opens the desktop app with a temporary data folder, saves an entry to the database, reads it back, generates a PDF, then prints a summary.
