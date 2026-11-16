# AICA Folder Storage Manager

Windows 10/11 x64 desktop app: index a folder, drive or network location per **project**, see storage usage,
track changes between scans, find exact duplicates, compare likely versions, and organize files after review.
Everything (index, OCR, reports) stays on this computer.

**Deliverable:** `dist\AICA Folder Storage Manager.exe` — a single file, no installation, no Python needed.

## Screens
Projects · Overview · Files · Changes · Duplicates · Compare Versions · Organize · History.
The active project name, its exact scan path and the snapshot being shown are always visible at the top.
Scan progress has its own strip under that header and never mixes with completed results.

## Project and scan isolation
* Each project has a unique ID and its **own SQLite database**:
  `%LOCALAPPDATA%\AICA Folder Storage Manager\projects\<project id>\project.db`
  (file index, snapshots, changes, duplicates, review queue, client names, settings, audit log).
  A project database refuses to open for a different project ID or path.
* A scan covers only the project path and its subfolders. If the path is unreachable the scan is **Failed** —
  no fallback to a parent folder, drive root or another project.
* Junctions and symbolic links are skipped (listed as "link skipped").
* Every scan is a new snapshot: **Completed**, **Incomplete** (some locations unreadable), **Cancelled**,
  **Failed** or **Interrupted**. Only Completed scans become the baseline (an Incomplete one can be accepted
  explicitly on the Changes page). Files in locations that could not be read are **Unverified**, never Deleted.
* Background scans write only to their own project; a scan finishing for another project never changes the
  screen you are looking at.

## Duplicates, versions, organize
* Duplicates: same size → full-file **SHA-256**. Choose KEEP, tick copies, review full paths, **Delete Selected
  Copies**. Kept and selected copies are re-fingerprinted right before deleting. Recycle Bin on local drives;
  network shares / removable drives are flagged as **permanent deletion** with a separate confirmation.
* Compare Versions: file-name patterns, extracted-text similarity (PDF/Word/text), image similarity. Older/newer
  is labelled with the evidence, or "Order uncertain". Exact duplicates never appear here.
* Organize: text from PDFs and Word; OCR (Windows built-in OCR engine) for scanned PDFs and images. Names come
  from your client list (with aliases) or from labels such as "Client:" (marked unconfirmed), each with an
  excerpt and page/paragraph reference. **Confirm Name** only records the name. **Move Selected Files** shows
  exact source → destination, flags conflicts (skip or keep both — never overwrite), and verifies cross-drive
  copies by SHA-256 before removing the source.

## Exports
File inventory, change report, duplicate report, action log, history — `.xlsx` or `.csv`, each with the project
name, project ID, scan path and snapshot IDs/dates at the top.

## OCR
Uses the OCR engine built into Windows 10/11 (`Windows.Media.Ocr`) with the languages installed in Windows
(English is present on standard installs). Add more OCR languages in Windows Settings > Language.

## Self-test (e.g. on a clean PC)
```
"AICA Folder Storage Manager.exe" --selftest C:\Temp\aica-selftest
```
Creates test files only inside that folder, runs scan / isolation / change detection / duplicates / OCR /
confirm + move / exports / reopen checks, and writes `selftest_report.txt` there.

## Development
```
pip install PySide6 openpyxl pypdf pypdfium2 python-docx pillow send2trash winrt-runtime ^
  winrt-Windows.Media.Ocr winrt-Windows.Graphics.Imaging winrt-Windows.Storage.Streams ^
  winrt-Windows.Foundation winrt-Windows.Foundation.Collections winrt-Windows.Globalization pyinstaller pytest pywinauto
python main.py                       # run
python -m pytest -q                  # unit + UI tests
powershell -File build_exe.ps1       # build dist\AICA Folder Storage Manager.exe
python tools\acceptance.py "dist\AICA Folder Storage Manager.exe" D:\aica-test\acc   # GUI acceptance run
```
