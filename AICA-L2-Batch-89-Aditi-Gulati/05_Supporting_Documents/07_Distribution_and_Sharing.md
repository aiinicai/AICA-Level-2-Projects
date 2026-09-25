# Running it without Python, and sharing it

Three ways to give someone this tool, from easiest for the recipient to
easiest for you.

---

## 1. The executable — no Python needed

This is the one to use when sending it to a school, a colleague or a judge.
They double-click a file and the app opens. Nothing to install.

### Build it

Double-click **`build_exe.bat`** in the project folder.

It runs the tests first and refuses to build if any fail, clears the previous
build, then produces **`dist\SurakshaScan.exe`**. Two to five minutes. When it
finishes, Explorer opens with the file selected.

From a terminal instead:

```powershell
pyinstaller SurakshaScan.spec
```

### Test it before sending it anywhere

**On a machine with no Python installed.** A build that works only on the
machine that built it is the standard first bug, and it is the one that bites
during a demo. Borrow a school office computer.

Check:

- the app opens, and the icon appears in the taskbar
- a scan runs and the score appears
- all three reports save and open
- the reports land in **Documents\SurakshaScan Reports** (the built app writes
  there, not beside the .exe, because the folder holding the .exe is often
  read-only)

If it does not open at all, look for `C:\Users\<name>\.surakshascan\last_error.txt`
— the build writes the full error there rather than failing silently.

### Sending it

The file is roughly 120–200 MB, so email will refuse it. Use Google Drive,
OneDrive or WeTransfer and share the link.

**Warn the recipient about SmartScreen.** Windows shows a blue "Windows
protected your PC" box for any executable without a paid code-signing
certificate. They click **More info**, then **Run anyway**. Tell them this
before they open it — an unexplained security warning is how a good tool ends
up in the recycle bin. Some antivirus products quarantine PyInstaller builds
for the same reason.

Signing it properly needs a code-signing certificate from a certificate
authority, renewed annually. Worth it if this becomes a service you sell; not
worth it for a capstone.

### What to send alongside it

- `README.md` — what the tool does
- `docs/TESTING.md` — how to check it works
- A line saying it scans public pages only, obeys robots.txt, never logs in,
  and that they should only point it at a site they are authorised to scan

---

## 2. The double-click launchers — for a machine that has Python

If the recipient already has Python, or you are moving between your own
machines, the project ships three batch files. No commands to type.

| File | What it does |
|---|---|
| **`Start SurakshaScan.bat`** | Opens the app. On first run it creates the virtual environment and installs everything, which takes a few minutes; after that it opens immediately. |
| **`Run self-test.bat`** | Scans the bundled fixture school and writes all three reports. Proves the installation works. |
| **`build_exe.bat`** | Builds the .exe. |

Right-click `Start SurakshaScan.bat` → **Send to** → **Desktop (create
shortcut)** for a desktop icon. Right-click the shortcut → Properties →
Change Icon → browse to `assets\surakshascan.ico` to give it the proper icon.

Zip the whole project folder — **minus** `.venv`, `build`, `dist` and
`__pycache__`, which are large and rebuild themselves — and send that.

---

## 3. Sharing the *result* rather than the tool

Usually what a school actually wants. They do not need the scanner; they need
the report.

`Sample_DPDP_Dashboard.html` and any dashboard the app produces is a single
self-contained file — the charts are embedded inside it, there is no external
script, and it needs no internet. Email it and it opens in any browser, on a
phone as well as a laptop.

The Word report is the one for a management committee. The Excel workbook is
the one for whoever has to do the work, because the Remediation sheet has
blank Owner, Target date and Done columns ready to be filled in.

---

## What NOT to share

The evidence files in `C:\Users\<name>\.surakshascan\evidence\`. They contain
the full scan record for every institution you have reviewed, including ones
that are not the recipient's. Secrets are redacted, but another school's
findings are not yours to pass on.

Send the evidence file for *their* scan if they ask for the audit trail —
that one is theirs.
