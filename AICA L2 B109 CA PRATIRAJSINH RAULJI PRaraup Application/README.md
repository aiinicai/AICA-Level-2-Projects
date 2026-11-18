# PRarup प्रारूप — Office Suite 1.0
Developed for Pratirajsinh Raulji and Co.

## Run the updated Windows app
Close the old PRarup application and run **PRarup_v1.0.exe**. This is a self-contained portable executable: no Python installation, installer or sibling _internal folder is needed. The first start can take longer while bundled files unpack. The build is unsigned and was tested on this Windows 11 x64 machine; no clean-machine certification is claimed.

Existing data remains under %LOCALAPPDATA%/PRarup. Version 1 databases are backed up before the additive version 2 migration. Do not delete that data folder when upgrading. Close older PRarup versions before using this release.

## Main workflow
Document library → Enter details → complete tabs → Review details → Prepare draft → edit → Save draft / Export Word / Export PDF / Preview and print.

Choose Classic legal (Times New Roman), Editorial serif (Georgia) or Contemporary (Calibri). Set 20/25/30 mm margins and optional 45/75 mm first-page stamp space. Review copy includes a draft notice; Clean execution copy removes only that notice, without asserting legal approval. Print preview and native PDF share exactly the same page renderer. Word remains editable and may paginate differently. Windows-installed fonts are used, not redistributed.

## Available library — 16 document types
Partnership Deed; LLP Agreement; Retirement Deed; Dissolution Deed; Rent Agreement; Rent Renewal Agreement; Business Premises NOC; Authority Letter; Bank Authorization; GST Authorization; Board Resolution for bank account opening; Designated Partner Consent; Proprietorship Declaration; Business Undertaking; Address Declaration; Name Correction Affidavit.

Every built-in template remains **Pending Legal Review**. These are drafting aids, not legal certification. Check current state-specific law, stamp duty, registration, tax and filing rules, authority and execution formalities. A clean copy does not change this status. The original brief's entire larger catalogue is not implemented; only the available 16 types are represented as functional.

## Completed office workspaces
- Clients: create/edit/search/delete, optional identifiers/contacts, partners/directors/signatory and questionnaire prefill. Deletion preserves existing drafts but removes the client association.
- History: all-document title search, client filter, open, duplicate, archive and restore.
- Templates: duplicate built-ins; edit custom metadata, JSON questionnaire and clauses; new categories and optional clauses; immutable versions, restore active version, enable/disable; import/export JSON packages; supported text-only DOCX import.
- Favorites: star documents and filter the library. Ctrl+F opens library search.
- Settings: themes, default print style/jurisdiction, database backup, full workspace recovery ZIP and restore, optional screen locking (Ctrl+L).

Supported DOCX import extracts paragraph text and simple {{ variable }} placeholders, then applies PRarup typography. It rejects tables, images, macros and external links. It does not preserve an arbitrary Word layout. The JSON questionnaire editor is an advanced configuration interface rather than a drag-and-drop designer.

## Data protection and recovery
SQLite uses transactions, foreign keys, WAL, busy timeout, integrity checks and migrations. User data, custom templates, logs and output documents stay outside installed program files. Daily startup backups preserve the day's first database snapshot. Workspace recovery packages include a consistent database snapshot and custom library, with SHA-256 checksums. Restore validates content and saves a pre-restore recovery package. Exported Word/PDF files are excluded from workspace packages and should be copied separately.

Database files, logs, templates, backups and generated documents are unencrypted. Screen locking protects the interface only; it is not Windows account control or file encryption. Password records use salted PBKDF2-HMAC-SHA256. Backups have no automatic retention cleanup. A single-instance lock protects v1 instances using the same workspace; older versions must be closed manually.

## Source install and tests
```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python main.py
```
Python 3.12+ is targeted; the tested host uses 3.15.2. Dependency installation needs internet. Normal app use is offline.

## Build
```powershell
.\.venv\Scripts\python build_windows.py --onefile
```
Output: dist/PRarup_v1.0.exe. Omit --onefile to create a folder build in dist/PRarup. Build on Windows. PyInstaller DLL discovery PATH is restricted to avoid third-party native-library contamination.

For packaged verification only, set PRARUP_DATA_DIR to a new empty scratch directory and run the EXE with --workflow-check. It creates illustrative records and outputs in that directory. Never point this opt-in diagnostic at a live workspace.

See documentation/TEST_REPORT_v1.0.md, RESEARCH_REFERENCES.md, User Manual and Developer Guide. PyQt6 is GPLv3/commercial licensed; review distribution requirements before proprietary distribution.


## Shareable installer
Send PRarup_Setup_v1.0.exe to another person. They run it and follow Setup; no Python, ZIP extraction or additional app files are needed. The default per-user installation is %LOCALAPPDATA%/Programs/PRarup, with Start menu and optional desktop shortcuts, manuals, source archive and uninstall support. Saved data remains in %LOCALAPPDATA%/PRarup after uninstall.

Installer target: Windows 10 build 19041+ or Windows 11 with x64 support. The installer is unsigned. Rebuild using Inno Setup 6.7+ and installer/PRarup.iss, passing /DDistributionRoot to the folder containing the EXE, manuals, source ZIP and PRarup source directory. installer/build_installer.ps1 wraps that compiler invocation in the original distribution layout.
