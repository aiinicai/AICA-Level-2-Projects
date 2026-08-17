# Running / Installing The 45-Day Clock on Windows

The 45-Day Clock is designed to run locally on a Windows computer. Purchase ledgers, vendor details, Udyam evidence and computation results remain within the locally selected data folder as part of the application workflow.

---

## Option 1 — Run from Source
### Recommended for AICA Capstone Evaluation

### Requirements

- Windows 10 or Windows 11, 64-bit
- Python 3.11 or later
- Internet access only for the initial Python package installation, if the required packages are not already cached/installed

Microsoft Excel is not required merely to start the application, although Excel-compatible software is useful for opening exported `.xlsx` reports.

### Steps

1. Keep the complete project folder together.
2. Open **Command Prompt** in the project folder.
3. Create a fresh virtual environment:

```bat
py -m venv .venv
```

4. Activate it:

```bat
.venv\Scripts\activate
```

5. Upgrade pip:

```bat
python -m pip install --upgrade pip
```

6. Install the dependencies:

```bat
pip install -r requirements.txt
```

7. Start the application:

```bat
python app.py
```

The application should open as a native desktop window.

### Quick AICA Demonstration

After the application opens:

1. Create/open a demonstration analysis.
2. Go to **Load Ledger**.
3. Select **Load demonstration dataset**.
4. Review the control totals.
5. Continue through:
   - Vendors
   - Assumptions
   - Results
   - Exclusion Register
   - Export
6. Select **Export Complete Audit Pack** to generate the structured demonstration outputs.

The built-in demonstration dataset is synthetic.

---

## Optional Console Demonstration

Run:

```bat
python run_demo.py
```

Where applicable, also run:

```bat
python tests/test_rules.py
```

---

## Option 2 — Build the Windows Application with PyInstaller

A PyInstaller specification is included as:

```text
clock45.spec
```

Build it with:

```bat
pyinstaller clock45.spec
```

The build output is created under the normal PyInstaller `dist` directory.

The AICA source-code submission does not require the evaluator to build the Windows executable.

---

## Option 3 — Packaged Windows Installer

A commercial/release build may be distributed separately as a Windows installer such as:

```text
The-45-Day-Clock-Setup-1.2.0.exe
```

**The packaged installer is not required for evaluation of the source-code AICA capstone submission.**

If an installer is distributed commercially, it should come from an approved source and preferably be code-signed.

---

## First Opening / Data Folder

On **Home**, use **Choose data folder** to select a folder controlled by the user/firm.

That data folder may contain:

- the local SQLite database;
- vendor evidence;
- supporting local files; and
- the locally installed licence file, where applicable.

Use a dedicated project/client folder rather than a program-installation folder.

For the AICA demonstration, use a dedicated synthetic/demo data folder so that no real client material is mixed with the demo.

---

## Backup and Restore

On **Home**:

- use **Back up database** to create a backup; and
- use **Restore database** to restore from a selected `.sqlite3` backup.

Restoring replaces the current live database with the selected backup.

Keep production backups under the firm's normal backup and information-security controls.

---

## Licence Behaviour

The application supports local/offline licence verification.

Without a signed licence, the application may operate under the configured trial limits while the synthetic demonstration dataset remains available for demonstration purposes.

Private licence-signing material must **never** be committed to the public repository.

---

## Windows SmartScreen / Antivirus

Unsigned or newly built Windows applications can trigger SmartScreen or antivirus reputation warnings.

Do **not** disable SmartScreen or antivirus protection merely to run an unknown build.

For a distributed installer:

1. confirm the installer came from the approved source;
2. compare a supplied SHA-256 checksum if one is provided;
3. verify the application name; and
4. proceed only when the source is trusted.

Commercial distribution should use an appropriate Windows code-signing certificate.

---

## Files That Must Not Be Uploaded to the Public Repository

Do not commit:

```text
.venv/
test_env/
__pycache__/
*.pyc
*.sqlite3
*.sqlite3-wal
*.sqlite3-shm
.env
*.key
*.pem
licensing-private/
```

Also exclude real client ledgers, real Udyam evidence, passwords, API keys, private signing material and other confidential records.

---

## Troubleshooting

### `ModuleNotFoundError`

Activate the virtual environment and reinstall:

```bat
.venv\Scripts\activate
pip install -r requirements.txt
```

### Application does not open

Run from Command Prompt so any startup error remains visible:

```bat
python app.py
```

### Export files are not where expected

Check the folder selected in the application and the destination selected for the Complete Audit Pack.

### Build fails on `assets/clock45.ico`

Confirm that this file exists:

```text
assets\clock45.ico
```

---

## Uninstalling a Packaged Version

If a separately packaged installer has been used, uninstall it through:

**Settings → Apps → Installed apps → The 45-Day Clock → Uninstall**

Uninstalling the program should not be treated as a substitute for deleting or archiving the user-selected database folder.
