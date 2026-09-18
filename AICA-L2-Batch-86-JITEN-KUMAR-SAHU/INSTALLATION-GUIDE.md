# ClientLedger India — Installation Guide

This guide walks through everything needed to turn the project files into a working `ClientLedgerIndia.exe` you can install and run — starting from a completely bare Windows PC with nothing installed. If you're just using the finished app, see `USER-MANUAL.md` instead. If you already know your way around Python/build tools, `README-BUILD.md` is the faster reference.

**Total time:** roughly 20–30 minutes the first time (mostly waiting for downloads). Every rebuild after that takes under a minute.

---

## What you'll need

- A Windows 10 or 11 PC
- An internet connection (only needed for this initial setup — the finished app works offline)
- About 1.5 GB of free disk space (Python + Chromium + build tools)

---

## Step 1 — Install Python

1. Go to **[python.org/downloads](https://www.python.org/downloads/)**.
2. Click the big yellow **"Download Python 3.x.x"** button (any version 3.11 or newer works).
3. Run the downloaded installer.
4. **This is the single most important step in this whole guide:** on the very first installer screen, **tick the checkbox at the bottom that says "Add python.exe to PATH"** before clicking Install. If you miss this, Windows won't be able to find Python later, and every step from here on will fail with confusing errors.

   ```
   ☑ Add python.exe to PATH        ← MUST be checked
   [ Install Now ]
   ```

5. Click **Install Now** and wait for it to finish.
6. **Verify it worked:** open the Start Menu, type `cmd`, press Enter to open Command Prompt, then type:
   ```
   python --version
   ```
   You should see something like `Python 3.13.1`. If instead you see an error or it opens the Microsoft Store, the PATH checkbox wasn't ticked — uninstall Python (Settings → Apps) and repeat this step, making sure to check that box.

---

## Step 2 — Install Inno Setup

This is the free tool that packages everything into the final single `.exe` installer you'll hand to a client.

1. Go to **[jrsoftware.org/isinfo.php](https://jrsoftware.org/isinfo.php)**.
2. Download the latest **Inno Setup** installer (the "innosetup-X.X.X.exe" link).
3. Run it and click through the installer with default options — nothing special needed here.

---

## Step 3 — Get the project files

1. Download the `ClientLedgerIndia-Installer-Project.zip` file (the one provided alongside this guide).
2. Right-click it → **Extract All...** → choose a **short** location close to your drive root, for example `C:\CLI\` — **not** somewhere like `C:\Users\Your Name\Downloads\ClientLedgerIndia-Installer-Project\ClientLedgerIndia\`. **This isn't just a suggestion — treat it as required.** Windows has a hard 260-character limit on file paths, and this project's folder nesting combined with the bundled Chromium browser's own deeply-nested files can push some paths past that limit if you extract somewhere long. This has been confirmed — not just theorized — to break **two separate tools** in this build process the same way: PyInstaller (step 4 below) and Inno Setup (step 5), both failing with a confusing "path not found" / "cannot find the path specified" error that has nothing to do with anything you did wrong. Extracting directly to a short path like `C:\CLI\` has been confirmed to resolve both. Also avoid unusual characters like `&` in the path if possible.
3. Open that extracted folder. You should see:
   ```
   ClientLedgerIndia\
   ├── app\
   ├── build\
   ├── README-BUILD.md
   ├── USER-MANUAL.md
   └── INSTALLATION-GUIDE.md   (this file)
   ```

**Important:** if you ever get a newer zip in the future to pick up fixes or updates, **delete the old extracted folder completely and extract the new one fresh** — don't just copy individual files over, and don't keep multiple partial copies lying around. Mixing old and new files this way is the single most common source of confusing build problems.

---

## Step 4 — Run the build script

1. Open the `ClientLedgerIndia\build\windows\` folder.
2. Double-click **`build.bat`**.
3. A black command window opens and runs through four steps automatically:
   - Creating a Python environment
   - Installing required packages
   - Downloading the Chromium browser (~150–300MB — this is the only step that uses significant internet data, and only happens once)
   - Building `ClientLedgerIndia.exe`
4. This takes several minutes the first time (mostly the Chromium download). **Wait for it to finish** — the window stays open and shows either:
   ```
   ================================================================
    BUILD SUCCEEDED
   ================================================================
   ```
   or, if something went wrong, an `[ERROR]` message explaining what and why. Either way, press any key to close the window when you're done reading it.

5. If it says BUILD SUCCEEDED, you now have a working app at:
   ```
   ClientLedgerIndia\build\windows\dist\ClientLedgerIndia\ClientLedgerIndia.exe
   ```
   You can double-click this right now to try the app — the steps below just package it into a proper installer to hand off to someone else.

**Rebuilding later:** just double-click `build.bat` again — it reuses everything from before and finishes in under a minute. Never delete the `build_venv` folder it creates; that's what makes rebuilds fast.

---

## Step 5 — Build the installer with Inno Setup

1. In the `build\windows\` folder, right-click **`installer.iss`** → **Open with** → **Inno Setup Compiler** (if it doesn't show up in the right-click menu, open the Inno Setup Compiler app first, then use File → Open and browse to `installer.iss`).
2. Once it's open, click the green **▶ Compile** button (or press F9, or go to Build → Compile).
3. Wait for it to finish — a small window shows progress and closes automatically.
4. Your finished installer is now at:
   ```
   ClientLedgerIndia\build\windows\Output\ClientLedgerIndia-Setup.exe
   ```

**This one file is everything.** Copy it to a USB drive, email it, or send it however you like — it contains the app, Chromium, and everything needed. The person receiving it needs nothing pre-installed; no Python, no Inno Setup, nothing.

---

## Step 6 — Install and run

1. Run `ClientLedgerIndia-Setup.exe` on the target computer (yours or the client's).
2. Follow the install wizard (default options are fine) — this creates a Start Menu shortcut and optionally a Desktop shortcut.
3. Launch **ClientLedger India** from the shortcut.
4. **First launch only:** a "First-Time Setup" window appears, asking where to store data. Pick a folder you'll back up regularly, then click Continue.
5. The app opens in its own window, ready to use — see `USER-MANUAL.md` for how to use it.

---

## If something goes wrong along the way

- **`build.bat` or Inno Setup fails with "The system cannot find the path specified" or "path not found," mentioning a deeply nested file under `.local-browsers\chromium-...`:** this is Windows' 260-character path limit, triggered by extracting the project somewhere with a long path (see Step 3 above). **Move the entire project folder to a short path like `C:\CLI\` and rebuild from there** — this has been confirmed to fully resolve it.
- **`build.bat` shows an `[ERROR]` message:** read exactly what it says — the script is written to explain the specific problem (missing Python, failed download, etc.) rather than just failing silently.
- **Windows blocks the app with no way to run it ("Smart App Control")**: this is a Windows security feature unrelated to whether the build succeeded. See the "Smart App Control" section in `README-BUILD.md`.
- **Something related to the app's actual behavior misbehaves** (a download stuck, a feature not working): check `<your chosen data folder>\System\logs\gst_rpa_activity.log` — real errors show up there with a clear message. See `USER-MANUAL.md`'s troubleshooting section.
- **Still stuck:** `README-BUILD.md` has a detailed changelog of specific issues encountered while building this project and exactly how each was fixed — worth checking whether your exact symptom is already documented there.
