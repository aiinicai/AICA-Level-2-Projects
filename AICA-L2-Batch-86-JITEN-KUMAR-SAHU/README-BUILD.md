# Building the ClientLedger India installer

*This document is for whoever builds/installs the app. New to this — starting from scratch on a fresh PC? See `INSTALLATION-GUIDE.md` for a complete beginner's walkthrough starting from installing Python itself. For day-to-day usage instructions once the app is installed, see `USER-MANUAL.md`.*

**Current confirmed-working build fingerprint:** `2026-08-31-d`
(Check this against the badge in the bottom-right corner of the running app, or `http://localhost:8765/health`, any time you need to confirm you're actually running the latest build — see [Verifying your build](#verifying-your-build) below.)

## What changed from your original files

| Before | Now |
|---|---|
| Client data stored in the browser's **IndexedDB** | Stored in a real **SQLite file** on disk, at `<your chosen folder>\Database\clientledger.db` |
| GSTR download folders hardcoded next to `gst_rpa.py` (`gstr1_downloads`, `gstr2a_downloads`, etc.) | Configurable — created inside **one base folder you pick during first run**, as `GSTR1`, `GSTR2A`, `GSTR2B`, `GSTR3B`, `TDS_TCS` |
| Run by typing `python gst_rpa.py` and opening a browser tab | A real installed desktop app (`ClientLedgerIndia.exe` / `ClientLedgerIndia.app`) with its own window |
| No installer | One `.exe` (Windows) / one `.dmg` (Mac) to hand to a client |
| Excel exports only downloaded to the browser's Downloads folder, untraceable | Every export also saves to disk in the matching `GSTR*/<gstin>/<FY>/` folder, path shown in the activity log |
| A worker crash (bad login, browser issue, etc.) could silently hang forever with zero explanation | Every background worker is wrapped so failures are always logged with a real error message |

The HTML/JS UI is otherwise untouched — every screen, workflow, and GSTR-1/2A/2B/3B/TDS-TCS automation works exactly as before. Only the two small blocks of code that talked to IndexedDB were rewired to talk to the local SQLite database instead (same function names, so nothing else in the ~16,000-line file needed touching).

## Verifying your build

Because rebuilds are cheap and easy to run without realizing an old copy is still what's actually launching, **check the build fingerprint before troubleshooting anything.** Two ways:

1. **In the app itself:** a small `Build: ...` badge sits in the bottom-right corner once the app loads. Click it to copy the full string.
2. **Via the API:** open `http://localhost:8765/health` in a browser while the app is running — look at the `"build"` field.

If it doesn't match `2026-08-30-a` (or whatever the latest fingerprint is after future changes), the running app is not the current build — rebuild before assuming anything is broken.

## Where the client's data lives

The **first time** the installed app is opened, it shows a one-time folder-picker ("First-Time Setup") asking where to keep data. Whatever folder is chosen gets this structure created inside it:

```
<Chosen Folder>/
├── Database/
│   └── clientledger.db        ← client master data (was IndexedDB)
├── GSTR1/        <gstin>/<FY>/...
├── GSTR2A/       <gstin>/<FY>/...
├── GSTR2B/       <gstin>/<FY>/...
├── GSTR3B/       <gstin>/<FY>/...
├── TDS_TCS/      <gstin>/<FY>/...
└── System/
    └── logs/
        └── gst_rpa_activity.log   ← check here first for any error
```

That choice is remembered in a small pointer file, **separate from the data folder itself**, so re-installing or upgrading the app never risks the client's data:
- Windows: `%APPDATA%\ClientLedgerIndia\config.json`
- macOS: `~/Library/Application Support/ClientLedgerIndia/config.json`

To pre-set the folder without showing the wizard (e.g. for a scripted/silent rollout), set the environment variable `CLIENTLEDGER_DATA_DIR` before first launch.

## Where Excel exports go

Every "Export to Excel" button saves a permanent copy to disk, inside the same `GSTR1` / `GSTR2A` / `GSTR2B` / `GSTR3B` / `TDS_TCS` folder (under `<gstin>/<financial year>/`) the raw downloaded data for that client and period already lives in. The browser will *also* still trigger its normal download, but that's now just a convenience copy — the authoritative one is on disk, and its exact path is written to that module's on-screen activity log ("📁 Excel saved to: ...") right after the export finishes.

## The activity log — your first stop for any problem

`<data folder>\System\logs\gst_rpa_activity.log` now reliably captures everything: every RPA flow's step-by-step log (`push_log`), the GSTIN Directory enrichment feature (`[GDIR]` lines), and the combined "Download All" feature (`[COMB]` lines). If any background worker fails for any reason, it will show up here as either:
- `✗ FATAL (uncaught): ...` with a full Python traceback, or
- `[UNCAUGHT] Thread '...' died with an unhandled exception: ...`

Every background worker (GSTR1/2A/2B/3B, TDS, GSTIN Directory enrichment, combined download) is wrapped so a crash always produces one of these two messages instead of silently hanging with zero explanation — this was **the single hardest thing to get right** in this whole build (see the changelog below), and it's the reason any future issue should now be immediately diagnosable from this one file rather than requiring guesswork.

## Known issues fixed along the way (changelog)

Kept here because several of these were genuinely subtle and worth knowing about if you're modifying this code further:

- **PyInstaller bundling Chromium in the wrong place.** Fixed by installing Chromium with `PLAYWRIGHT_BROWSERS_PATH=0` (puts it inside the `playwright` package itself, exactly where the frozen driver looks for it by default) and bundling that same folder in the `.spec` files.
- **`'charmap' codec can't encode character'` crashes.** Windows consoles default to `cp1252`, which can't display the ✓/✗/🚀/✅/❌ symbols used throughout the app's logging. Fixed with a two-layer approach: `sys.stdout`/`sys.stderr` get reconfigured to UTF-8 at startup, wrapped in a `_SafeStream` class that silently substitutes any character that still can't encode. Separately, several logging functions had **redundant raw `print()` calls** sitting after an already-safe `log.info()`/`log.error()` call — `print()` always re-fetches `sys.stdout` fresh, so if anything (e.g. pywebview's window init) reassigns it after startup, `print()` could still hit an unwrapped stream. Those redundant calls were removed entirely.
- **Race condition in "Download All" and "GSTIN Directory enrichment."** Both had a check-then-act gap: the "is a worker already running?" check happened under a lock, but the actual claim happened in a *separate* lock acquisition afterward — a fast double-click could get two workers running concurrently, corrupting shared state and producing duplicated log lines. Fixed by making the check-and-claim atomic in a single lock acquisition.
- **A genuine self-deadlock.** One code path called `_comb_log()` (which acquires `_comb_lock`) while `_comb_lock` was already held by the same thread. Python's `threading.Lock` isn't reentrant, so this would hang that thread forever if ever hit.
- **Logging never reached disk.** Several logging functions (`_gdir_log`, `_comb_log`, `tds_log`, `g3b_log`) only appended to an in-memory list and printed to console — invisible in a packaged windowed build, and wiped on every new run. All now write through the shared `logging.FileHandler`.
- **Repeated file opens under antivirus scanning.** An earlier fix had these same functions open/write/close `LOG_FILE` on every single call — a real-time-scanned file being reopened milliseconds later is exactly the kind of pattern that can hang under antivirus lock contention. Fixed by routing everything through one `FileHandler` opened once at startup.
- **Uncaught worker exceptions vanishing silently.** In a frozen windowed build, Python's default behavior of printing an uncaught thread exception to `stderr` goes nowhere (no real stderr exists). Fixed with a global `threading.excepthook` plus dedicated try/except wrappers on the two most complex workers, so any failure is now always logged with a real message.
- **`_gdir_log`/`g3b_log` missing a `level` parameter.** Both were called with a second `"error"` argument somewhere in the code despite only accepting one parameter — a `TypeError` waiting to happen the first time that error path was hit.
- **Excel export paths untraceable.** Exports were built in memory and handed straight to the browser's download mechanism with no record of where they landed. Now saved to disk first, in a predictable, documented location.
- **"Replace All" restore could abort entirely on one bad record**, or silently swallow failures with no way to tell what went wrong. Both the delete phase and the insert phase are now resilient per-record, and failures are reported with the specific reason (usually a duplicate PAN/Aadhaar/email in the backup data).
- **`requirements.txt` pinned to exact versions**, which broke on any Python version released after those pins went stale. Switched to minimum-version constraints (`>=`) so pip always resolves something compatible.
- **`build.bat` recreated the virtual environment (and re-downloaded Chromium) on every run.** Now incremental by default — reuses the existing environment unless you explicitly run `build.bat clean`.
- **The race-condition, unprotected-`sync_playwright().start()`, and silent-crash fixes were initially only applied to "Download All" and GSTIN Directory enrichment.** A full audit found all three bug classes present, unfixed, in every one of the other five worker flows too — the general RPA filing-status checker, GSTR-1, GSTR-2A, GSTR-2B, and TDS/TCS. All six now have: (1) an atomic check-and-claim on their `/start` route instead of a check-then-later-claim race (`/g3b/start` was the worst offender — it didn't even use a lock for the check at all), and (2) a thin wrapper function around the real worker logic that catches literally any exception, including ones thrown before `sync_playwright().start()` even runs, and reflects it in that module's state as a real error message instead of a silent, permanent hang. Verified with a real concurrency test (5 simultaneous requests to each of the 6 `/start` routes → exactly 1 accepted and exactly 1 worker started, every time) and a real crash-injection test (simulated failure in each of the 6 workers → each one correctly logged and reported as `status: "error"` instead of vanishing).
- **`g3b_worker` stored its browser profile in the user's home directory** (`~/.gst_rpa_profiles/`) instead of the user-chosen data folder like every other worker — an inconsistency from before this project's config/data-folder work began, caught during the audit above. Now uses `PATHS.profiles_dir` like everything else.
- **PyInstaller build failing with `Unable to find ...gdocs_script.js` on a fresh machine.** Newer Playwright versions download a second "chromium_headless_shell" Chromium variant alongside regular Chromium (used only for headless-mode performance) even though this app always launches with `headless=False` and never touches it. Playwright's own official PyInstaller hook tries to bundle every browser folder it finds under `.local-browsers`, and on some Chromium/headless-shell revisions that fails because a file the hook expects isn't actually present in that particular shell package. Fixed by deleting the unused `chromium_headless_shell-*` folder in both build scripts right after Chromium downloads, before PyInstaller ever runs.
- **"Error Saving client" with no useful detail when editing an existing client.** Both the add and update client-record error handlers were discarding the actual underlying error and always returning the same generic message, regardless of what actually went wrong (a real duplicate on a specific field, or something else entirely). Fixed to include the real detail (e.g. "UNIQUE constraint failed: clients.pan") in the response, shown directly in the app's inline error text, and logged to the persistent activity log. Verified: editing an unrelated field (address) on an existing client now succeeds normally, and a genuine duplicate now clearly names which field conflicts.
- **The above fix didn't fully explain a real "Error Saving client" report** — the activity log showed the browser sending a CORS preflight (`OPTIONS`) for the save request that succeeded, but the actual `PUT` request that should follow never reached the server at all. Root cause: every API call in the app was hardcoded to `http://localhost:8765`, but pywebview actually serves the page from `http://127.0.0.1:8765` — technically a different origin, even though it's the same server. This made every single API call cross-origin, relying entirely on a wildcard CORS header to work at all. GET/POST mostly tolerate that loosely; PUT/DELETE require a CORS preflight, and evidently something in this environment handled the actual request after that preflight more strictly, causing it to silently never be sent. Fixed by using the page's own origin (`window.location.origin`) instead of a hardcoded one, making every API call genuinely same-origin and never subject to CORS at all, regardless of method or browser engine. Also caught and fixed two other stray hardcoded-origin references (the activity-log download link, and the portal quick-login feature) that had the same latent issue.
- **After the origin fix, the same save still failed with "Failed to fetch"** — a generic browser network-layer error that gives zero detail on the real cause (CORS block, connection refused, blocked by local security software, and more all produce this exact same message). Since the backend logs can't see requests that never arrive, the only way to actually diagnose this is real browser DevTools. Enabled `webview.start(debug=True)` so DevTools is available in the packaged app (right-click anywhere in the app -> Inspect), and added explicit `console.error()` logging around the client-save fetch call showing the exact URL and page origin side by side, so a same-origin/cross-origin mismatch (or any other cause) is immediately visible in the Console/Network tabs instead of hidden behind a generic message.
- **This confirmed the origin fix above actually worked** — the DevTools Network tab showed the PUT request completing with a real `200` response, and the app showed "Client updated successfully." Confirmed the underlying bug is genuinely fixed, not just theorized.
- **`debug=True` turned out to auto-open a DevTools window on every single app launch** on this app's WebView2 backend, not just make Inspect available on request — fine for diagnosing the issue above, but not something a normal user should see every time they open the app. Made this opt-in instead: set the environment variable `CLIENTLEDGER_DEBUG=1` before launching if DevTools access is needed again for a future issue; otherwise the app opens cleanly with no DevTools window.

## Smart App Control (Windows 11)

An unsigned, freshly-built `.exe` will likely get blocked outright by Windows 11's Smart App Control, which — unlike SmartScreen — has no "Run anyway" override. Two options:
1. **Turn it off:** Windows Security → App & browser control → Smart App Control → Off. On most current Windows builds this is a one-way decision (permanent until a Windows reinstall) unless the PC has the March 2026 update (KB5079391/KB5086672), which made it reversible.
2. **Code-sign the executable** with a purchased certificate (~$70–300/year) for a more durable fix if distributing to many clients long-term — even then, a standard (non-EV) certificate still needs to build reputation over time.

This is a Windows-side decision, not something fixable in the app's code.

## Important limitation: builds are platform-native

PyInstaller (and macOS app bundling) cannot cross-compile — **a Windows `.exe` must be built on a Windows machine, and a macOS `.app`/`.dmg` must be built on a Mac.** This is true of every tool in this space (PyInstaller, py2exe, py2app), not a limitation of this project specifically.

---

## Building on Windows

**Rebuilding after a code change is fast and uses no internet.** `build.bat` reuses the existing virtual environment and the already-downloaded Chromium browser automatically — it only repackages whatever's currently in `app/`. Do **not** manually delete `build_venv`, `dist`, or `work` between rebuilds; that throws away the downloaded Chromium (~150–300MB) and forces a slow re-download next time for no benefit. Just run `build.bat` again, plain, with no arguments.

The only time you'd want a from-scratch environment is if you genuinely suspect it's corrupted (not just your app code) — for that, run `build.bat clean`, which wipes `build_venv` and re-downloads everything.

**Requirements:** Python 3.11+, [Inno Setup 6](https://jrsoftware.org/isinfo.php) (free).

```cmd
cd build\windows
build.bat
```

This will: create (or reuse) a virtual environment, install/verify dependencies, download Chromium if not already present, and run PyInstaller — producing `build\windows\dist\ClientLedgerIndia\`.

Then open `build\windows\installer.iss` in the Inno Setup IDE and click **Build** (or run `iscc installer.iss` from the command line). You'll get:

```
build\windows\Output\ClientLedgerIndia-Setup.exe
```

**That single .exe is what you send to the client.** Running it installs the app, Chromium browser, and creates a Start Menu / Desktop shortcut. No Python, no `pip install`, nothing else required on the client's PC.

**For day-to-day development/testing, just run `build\windows\dist\ClientLedgerIndia\ClientLedgerIndia.exe` directly** after `build.bat` finishes — you don't need to re-run the Inno Setup installer for every test, only when you're ready to hand off a new distributable.

## Building on macOS

**Same incremental behavior as Windows** — `build.sh` reuses `build_venv` and the downloaded Chromium automatically; run `./build.sh clean` only if you need a genuinely fresh environment.

**Requirements:** Python 3.11+, Xcode command line tools, [Homebrew](https://brew.sh) (the script auto-installs `create-dmg` via Homebrew if missing).

```bash
cd build/mac
chmod +x build.sh
./build.sh
```

This produces:

```
build/mac/dist/ClientLedgerIndia.app
build/mac/dist/ClientLedgerIndia.dmg   ← send this ONE file to Mac clients
```

**Note on Gatekeeper:** an unsigned `.app` will show a "can't be opened because it is from an unidentified developer" warning on the client's first launch (right-click → Open bypasses it once). To avoid that entirely, sign and notarize with an Apple Developer ID — instructions are printed at the end of `build.sh`. This requires a paid Apple Developer account.

---

## Testing before you build

You can run everything exactly as it will behave once installed, without building anything, straight from source:

```bash
cd app
pip install -r requirements.txt
python -m playwright install chromium
python launcher.py
```

This opens the same desktop window the final installer will produce, using whatever data folder you choose in the first-run wizard.

If you just want the old browser-tab workflow (e.g. for quick debugging), `python gst_rpa.py` still works unchanged and serves the UI at `http://localhost:8765`.

## Project layout

```
ClientLedgerIndia/
├── app/
│   ├── gst_rpa.py              Flask server + all GST automation (paths now configurable, workers now crash-safe)
│   ├── config.py                First-run folder picker + path resolution
│   ├── dbstore.py                SQLite layer replacing IndexedDB
│   ├── launcher.py               Desktop window entry point (pywebview)
│   ├── templates/
│   │   └── ClientLedger-India.html   Original UI, IndexedDB→SQLite swapped, build badge added
│   └── requirements.txt
├── build/
│   ├── windows/
│   │   ├── ClientLedgerIndia.spec
│   │   ├── build.bat            Incremental — safe to re-run anytime
│   │   └── installer.iss
│   └── mac/
│       ├── ClientLedgerIndia.spec
│       └── build.sh             Incremental — safe to re-run anytime
└── README-BUILD.md   (this file)
```

## Known open items (not yet addressed)

- **GSTIN name enrichment** was reported as "not working properly" early on, but specifics were never pinned down — worth a fresh look with the current build's improved error logging.

## If you'd rather I build the installer for you

I can't run Windows or macOS builds myself (this environment is Linux-only, and PyInstaller/Inno Setup don't cross-compile), but everything above is ready to hand to anyone with a Windows PC and/or a Mac — the two scripts do the entire build unattended.
