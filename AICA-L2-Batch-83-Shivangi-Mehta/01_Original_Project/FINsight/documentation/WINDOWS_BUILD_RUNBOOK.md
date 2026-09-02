# FINsight — WINDOWS BUILD KIT & RUNBOOK

**What this is:** the document to use on a real Windows 10/11 (64-bit) computer to create and test the first real `FINsight.exe`. It was prepared in a Linux development sandbox that cannot build or run a Windows `.exe` itself, so **nothing in it has been executed yet** — every command needs to actually be typed and run on Windows, and the real results recorded in the companion `FINsight_WINDOWS_BUILD_RESULTS.md`.

**Structure:** this runbook is organized into two clearly separated phases with a mandatory **STOP POINT** between them (see Section 20). Phase 1 (Sections 1–10) builds the EXE and audits the package. Phase 2 (Sections 11–18) is the full functional/LAN/persistence test pass ("UAT"). Do not move from Phase 1 into Phase 2 without pausing at the STOP POINT first.

Every "DO NOT" below is a hard boundary carried over from the approved project instructions — not a suggestion.

---

## 1. Exact Windows Prerequisites

- Windows 10 or Windows 11, **64-bit**.
- Internet access — needed only during setup (Sections 4–6), never needed to run FINsight itself afterward.
- About 2 GB of free disk space for the build tools and output, separate from whatever space FINsight's own data will use later.
- No other software needs to be pre-installed. You do **not** need Git, Visual Studio, or any IDE.

**DO NOT** install anything beyond what Sections 4–6 tell you to install — no extra packages, no newer PyInstaller than approved, no substitutions.

## 2. Exact Python Version

**Python 3.11 (64-bit)** — this matches the version the project was developed and tested against.

Download from the official source: `https://www.python.org/downloads/release/python-3119/` (any Python 3.11.x 64-bit build is fine — it doesn't need to be exactly 3.11.9).

During installation, **tick "Add python.exe to PATH"** on the first installer screen — every command below assumes `python` works from any folder.

**DO NOT** install Python 3.12/3.13 or any other version as the one used for the build — later steps assume 3.11.

## 3. Where to Copy the FINsight Project

Copy the entire project folder (the one containing `finsight_app.py`, `build_exe.spec`, `requirements.txt`, `app/`, `frontend/`, `config.py`, etc.) to a short, simple path with no spaces:

```
C:\FINsight_Source
```

Confirm it copied correctly:

```
dir C:\FINsight_Source
```

You should see `finsight_app.py`, `build_exe.spec`, `requirements.txt`, `app`, `frontend`, and `config.py` listed.

Also confirm Python installed correctly before continuing:

```
cd C:\FINsight_Source
python --version
```

Expected: `Python 3.11.x`. If you instead see `'python' is not recognized...`, Python wasn't added to PATH — reinstall it with that box ticked, or use `py -3.11 --version` instead everywhere `python` appears below.

**DO NOT** build directly on a Desktop path, a path with spaces, or a deeply nested folder — long/odd paths occasionally cause obscure build-tool errors.

## 4. Exact Commands to Create the Build Environment

All commands below go in **Command Prompt** (press Windows key, type `cmd`, Enter) — not PowerShell.

```
cd C:\FINsight_Source
python -m venv .venv-build
.venv-build\Scripts\activate
```

Your prompt should now start with `(.venv-build)`. Keep this window open for every remaining command in Sections 5–10 — if you close it, reopen Command Prompt, `cd C:\FINsight_Source`, then run `.venv-build\Scripts\activate` again.

This virtual environment only affects this one build — it does not touch any other Python installation on the computer.

## 5. Exact Commands to Install Dependencies

Still inside the activated `(.venv-build)` window:

```
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

This installs Flask, SQLAlchemy, Alembic, pandas, openpyxl, reportlab, pydantic, waitress, and the other already-approved packages (see `requirements.txt`'s own comments — nothing here is new or unapproved). Watch for `Successfully installed` at the end with no red `ERROR` lines above it. `pandas` in particular can take a few minutes — that's normal.

## 6. Exact PyInstaller Installation Command

```
python -m pip install "PyInstaller>=6.5,<7.0"
```

This exact version range is the one already reviewed and approved (see `requirements.txt`'s commented entry and `build_exe.spec`'s own header comment) — **DO NOT** install PyInstaller 7.x or a version below 6.5.

Confirm it installed and record the exact version:

```
pyinstaller --version
```

## 7. Exact Command to Build Using the Already-Approved `build_exe.spec`

Still inside the activated `(.venv-build)` window, from `C:\FINsight_Source`:

```
pyinstaller build_exe.spec --clean
```

This is the **only** build command to run. The spec file already encodes every packaging decision that was reviewed and approved (`--onedir`, what gets bundled, what's excluded, the console window, the icon).

**DO NOT**:
- Add `--onefile` or any other flag not shown above.
- Edit `build_exe.spec` to "fix" or "improve" anything — if something in it looks wrong, stop and report it rather than changing it yourself.
- Run PyInstaller against any file other than `build_exe.spec`.

The build takes a few minutes and prints a lot of scrolling text — that's normal. Watch specifically for:
- Any line reading `WARNING: <path> exists at build time and must be removed or excluded before shipping this build` — this means Section 9's safety check below should have caught something first. If you see it, stop and report exactly what path it named.
- The build ending without an `ERROR`. (Assorted PyInstaller `WARNING` lines about specific optional third-party modules are normal and expected — only the specific warning above is a stop condition.)

## 8. Expected Output / Folder Structure

After a successful build:

```
C:\FINsight_Source\dist\FINsight\
├── FINsight.exe
└── _internal\        (bundled Python runtime, libraries, templates, static files — large, expected)
```

Confirm:

```
dir dist\FINsight
```

**Two files must be copied in manually** — this is an already-documented, expected step, not a build failure:

```
copy Start_FINsight_Local.bat dist\FINsight\
copy Start_FINsight_LAN_Host.bat dist\FINsight\
```

The final expected structure is:

```
dist\FINsight\
├── FINsight.exe
├── Start_FINsight_Local.bat
├── Start_FINsight_LAN_Host.bat
└── _internal\
```

## 9. Pre-Build Safety Checks

**Run this BEFORE Section 7's build command**, on the clean `C:\FINsight_Source` copy:

```
cd C:\FINsight_Source
dir database\finsight.db
dir logs
dir config
dir .env
```

**Expected result:** all four report "File Not Found" / "The system cannot find the file specified." That confirms there's no development database, no logs, no local secret-key file, and no `.env` file sitting in the source tree.

**If any of them ARE found:**
- **STOP. Do not run the build.**
- Note exactly which file(s) were found in the results template.
- Do not delete anything yourself if you're unsure what it is.
- Report it back before proceeding.

Also visually scan the project folder for anything that looks like a real client name, real financial figures, or an unrecognized `.csv`/`.xlsx` file — flag the same way if you see anything like that.

**DO NOT** proceed to Section 7 if this check finds anything unexpected.

## 10. How to Verify No Database/Client Data/Secrets Are Packaged

Run this **after** the build (Section 7) and the manual `.bat` copy (Section 8), before doing anything else:

```
cd C:\FINsight_Source
dir dist\FINsight\database
dir dist\FINsight\finsight.db
dir dist\FINsight\.env
dir /s /b dist\FINsight | findstr /i "secret_key finsight.db .env"
```

**Expected:** the first three report "not found"; the `findstr` line returns **nothing at all** (an empty result is correct). Also spot-check that real content made it in:

```
dir dist\FINsight\_internal\frontend\templates
dir dist\FINsight\_internal\frontend\static
```

— these should show real `.html`/`.css` files.

Record the package size:

```
dir dist\FINsight /s
```

(Also check via File Explorer → right-click `dist\FINsight` → Properties, for an easy MB figure — record both the `_internal` folder size and the total `dist\FINsight` size.)

**If Section 10's checks find anything unexpected** (a database, `.env`, or secret file inside the built package), **stop and report it** rather than proceeding to Section 11 — this would mean something bypassed Section 9's check.

---

## 20. STOP POINT — Read This Before Going Further

**Once Sections 1–10 are complete (the EXE is built and the package audit is clean), STOP here and check in before running the full test pass in Sections 11–17.**

This checkpoint exists so that:
- A structurally broken or unsafe package (missing files, a packaged secret, a failed audit) gets caught and reported before you spend time on the longer functional/LAN/two-computer testing pass.
- Nothing beyond "build it, audit it, confirm it's safe to actually run" happens without a chance to review the build itself first.

At this checkpoint, fill in and send back **just** the Section 0, Part 1, and Part 2 portions of `FINsight_WINDOWS_BUILD_RESULTS.md` (build environment + build + package audit). Once that's reviewed, proceed to Sections 11–18 below (the full UAT) as a separate pass.

**DO NOT** treat a clean build/audit as proof the application actually works — Sections 11–17 are what verify that, and they still need to happen. **DO NOT** skip straight from Section 10 to Section 18 (release packaging) without running Sections 11–17 first.

---

## 11. How to Start the EXE in Local Mode

**Testing happens in a clean copy, not inside `dist\FINsight` directly** — this is what actually proves the package is self-contained:

```
xcopy /E /I C:\FINsight_Source\dist\FINsight C:\FINsight_Test
```

From here on, work inside `C:\FINsight_Test`.

Double-click `Start_FINsight_Local.bat` (in File Explorer, at `C:\FINsight_Test`).

A console window opens showing "FinSight — Offline Financial Review & Compliance Assistant," then initialization messages, then a `[1]`/`[2]` mode prompt. Type `1`, press Enter.

Watch for:
- No red error text or traceback.
- A line like `Local: http://127.0.0.1:5000`.
- The browser opening automatically, or the address being clearly shown if it doesn't.
- The FINsight dashboard actually loading.

Leave the window open — closing it stops FINsight.

## 12. How to Start LAN Mode

Close the Section 11 window first (fully stops FINsight). Then, still in `C:\FINsight_Test`, double-click `Start_FINsight_LAN_Host.bat` and type `2` at the prompt.

**The first time, you'll be asked to set an access password** — choose one at least 8 characters long. **Never write the actual password into the results template, chat, or a screenshot** — just record that setup succeeded.

Watch for:
- A **Local** address line and a **LAN** address line (e.g. `LAN: http://192.168.1.23:8877`) both shown.
- No error/traceback.
- No indication of Flask's own debug mode — LAN mode runs via Waitress, not the local-mode dev server.

If Windows Firewall prompts you, allow access for **Private networks only** — never tick Public. If LAN testing later fails to connect from a second computer, see the Firewall Guidance appendix at the end of this document rather than disabling the firewall.

**DO NOT** enable this on a public/untrusted network, and **DO NOT** forward the port to the internet.

## 13. How to Perform the First-Run Database Test

This only proves itself on a genuinely fresh copy (like `C:\FINsight_Test`, before you've run it) — which is why Section 11 must happen on a fresh copy, not inside `dist\FINsight` itself.

After Section 11's first run, confirm these were created automatically, with no manual step from you:

```
dir C:\FINsight_Test\database
dir C:\FINsight_Test\data
dir C:\FINsight_Test\logs
dir C:\FINsight_Test\config
```

Expected: `database\finsight.db` exists, `data\input`/`data\processed`/`data\output` exist, `logs\` has a log file inside, `config\secret_key` exists. None of these existed before Section 11 (Section 10 confirmed the package shipped without them) — this proves they're generated on first run.

Also confirm the dashboard shows an empty/starter state, not an error.

**If this fails** (folders/database not created, or an error shown): **stop and report it** rather than manually creating the missing pieces or modifying anything — this would point to a real packaging problem that needs review, not a local workaround.

## 14. How to Perform the Local Functional Test

Using **only made-up, non-confidential test data** (never real client information):

1. Create a test engagement (e.g. "Test Engagement — Windows Build Verification").
2. Upload a sample CSV or XLSX with a handful of invented transaction rows.
3. Complete column mapping / validation.
4. Run **Accounting Review** — confirm it completes with results.
5. Run **Audit Review** — confirm it completes with results.
6. Run **Tax Review** — confirm it completes with results.
7. Open **Unified Findings** — confirm results from all three appear together.
8. In **Query Centre**, raise a test query against a finding and add a reviewer response.
9. Open the **Working Paper** view and confirm the query, response, and any evidence references appear correctly.

Record pass/fail per item — a single review type failing while others pass is useful detail, not a reason to mark everything failed.

## 15. How to Perform the Two-Computer LAN Test

Requires a second computer on the **same trusted network** (never public Wi-Fi). If unavailable, record "Not performed — no second computer available" rather than skipping silently.

On the second computer, open a browser and type the exact LAN address shown in Section 12 (e.g. `http://192.168.1.23:8877`).

Record:
- Whether the login/password page loads at all (if not, see the Firewall appendix).
- The **wrong** password is rejected with a clear message.
- The **correct** password logs in and the dashboard loads normally.
- The second computer does not end up with its own copy of `finsight.db`, uploaded files, or the FINsight application itself — it should only be using a browser.

## 16. How to Test Engagement Isolation

On the **second computer**, open **two genuinely different browsers** (e.g. Chrome and Edge — not two tabs of the same browser, since tabs share a session) and log in to the LAN address in both.

1. In Browser 1, open (or create) Engagement A.
2. In Browser 2, open (or create) a different Engagement B.
3. Switch back to Browser 1 — confirm it still shows Engagement A, not B.
4. Switch to Browser 2 — confirm it still shows Engagement B, not A.
5. Add a reviewer note in Browser 1 under Engagement A — confirm it does **not** appear in Browser 2 under Engagement B.
6. Back on the host computer, confirm the note added from Browser 1 IS visible there (proving the host database received it, while the two client sessions stayed isolated from each other).

This is one of the most important LAN tests. A failure here (sessions bleeding into each other) should be flagged clearly and immediately, not worked around.

## 17. How to Test Restart / Data Persistence

1. Close the LAN mode console window (stops FINsight entirely).
2. Reopen it via `Start_FINsight_LAN_Host.bat` (or `Start_FINsight_Local.bat`).
3. Confirm the engagement, findings, queries, and reviewer notes from Sections 14 and 16 are all still there.
4. Confirm the LAN password from Section 12 still works — you should not be asked to set it up again.

This reuses the same `C:\FINsight_Test` folder (now containing real test data) — it is a restart test, not a fresh install.

**Note on upgrade testing:** there is no second official Windows build to upgrade *from* yet, so a true upgrade (V1 → V2) test cannot be performed in this pass — that remains for a future stage. Do not describe this restart test as an upgrade test.

---

## 18. How to Create the Final Release ZIP

**Only do this after Sections 11–17 are complete and satisfactory.** Build the release from the original `dist\FINsight`, not from the now-test-data-containing `C:\FINsight_Test` copy:

```
cd C:\FINsight_Source
mkdir release
mkdir release\FinSight_V1_Windows_x64
xcopy dist\FINsight\FINsight.exe release\FinSight_V1_Windows_x64\
xcopy /E /I dist\FINsight\_internal release\FinSight_V1_Windows_x64\_internal
copy Start_FINsight_Local.bat release\FinSight_V1_Windows_x64\
copy Start_FINsight_LAN_Host.bat release\FinSight_V1_Windows_x64\
copy README_DEPLOYMENT.md release\FinSight_V1_Windows_x64\
```

Confirm the release folder contains **only**: `FINsight.exe`, `_internal`, `Start_FINsight_Local.bat`, `Start_FINsight_LAN_Host.bat`, `README_DEPLOYMENT.md`.

```
dir release\FinSight_V1_Windows_x64
dir release\FinSight_V1_Windows_x64\database
dir release\FinSight_V1_Windows_x64\config
dir release\FinSight_V1_Windows_x64\logs
dir release\FinSight_V1_Windows_x64\.env
```

The last four must all say "not found." **If any exist, stop — do not zip or send it — and report exactly what was found.**

Then, in File Explorer: right-click the `FinSight_V1_Windows_x64` folder inside `release` → **Send to** → **Compressed (zipped) folder** → rename to `FinSight_V1_Windows_x64.zip`.

**DO NOT** include: `database\`, `data\`, `logs\`, `config\` (or a `secret_key` file), `.env`, or anything containing your own test data or names from Sections 11–17.

---

## 19. What Screenshots/Results to Capture

Send back:

1. The fully filled-in `FINsight_WINDOWS_BUILD_RESULTS.md` — including anything that failed or wasn't tested, not just successes.
2. Screenshot of `dir dist\FINsight` (Section 8) showing `FINsight.exe` and `_internal` present.
3. Screenshot of the FINsight dashboard loading (Section 11), with only made-up test data visible.
4. Screenshot of the LAN startup banner (Section 12) showing the Local/LAN address lines — **not** showing the password.
5. If Section 15/16 were performed: a screenshot from the second computer's browser showing a successful connection.
6. For anything that failed: the exact on-screen text or error (a screenshot is fine), plus which section it happened in.
7. Optionally, `FinSight_V1_Windows_x64.zip` itself, for review.

**DO NOT send:** the actual LAN password (in text or visible in any screenshot), real client data, or the full `database\finsight.db` file.

---

## Appendix A — Windows Firewall Guidance (only if Section 15 fails to connect)

If a second computer can't reach the LAN address, this is usually a firewall prompt needing a response, not an application bug.

- Confirm the network type is set to **Private** (Settings → Network & Internet) — never **Public**.
- If a "Windows Defender Firewall has blocked some features of this app" popup appeared, allow it for **Private networks only**.
- If you missed the popup: Settings → search "Allow an app through Windows Firewall" → **Change settings** → **Allow another app...** → browse to `FINsight.exe` → tick only **Private**.

**DO NOT** enable the Public column, and **DO NOT** disable Windows Firewall entirely.

## Appendix B — Antivirus Guidance (only if a warning appears)

- **DO NOT disable antivirus** to get past a warning.
- Record the exact warning/detection name shown.
- If your organization has a review/allow-list process for flagged files, use that rather than working around it yourself.
- This gets documented honestly as-is — it will not be reported as "the EXE is proven malware-free," because this process can't actually prove that.

---

*This runbook does not authorize proceeding into Stage 18, redesigning the application, or adding new functionality. Work stops at the point specified when you send back results — first at the Section 20 STOP POINT, and again after Section 19's full results are sent, pending review.*
