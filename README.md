# 📄 All Things PDF

A fully offline, professional PDF utility desktop app built with Python and tkinter.  
Inspired by iLovePDF. Green & white design based on DPS Family colour scheme.  
No internet required. No browser. No server. Just run and use.
# Ledger Reconciliation & Reporting Desktop App
# Ind AS 116 — Lease Accounting Suite

A modular, GUI-based lease accounting model for Chartered Accountancy
practices, covering **Day-0 measurement** of the Right-of-Use (ROU)
asset and Lease Liability under **Ind AS 116**, plus month-wise
liability amortisation and ROU depreciation schedules.

## Requirements
- Python 3.9 or later
- Tkinter (ships with standard Python installers on Windows/macOS; on
  some Linux distributions install via `sudo apt install python3-tk`)

All other third-party packages (`pandas`, `openpyxl`,
`python-dateutil`) are detected and installed **automatically the
first time you run the app** — you will see a live installation log
window while this happens. This only happens once per machine.

## Running the application
```
python main.py
```

## What it does
1. **Lease Inputs tab** — enter monthly rental, lease term, escalation,
   payment timing (advance/arrears), the Interest Rate Implicit in the
   Lease (or Incremental Borrowing Rate if not determinable), initial
   direct costs, incentives, restoration costs, etc.
2. **Run Model** computes:
   - Lease Liability at Day 0 = PV of unpaid lease payments
   - ROU Asset at Day 0 = Lease Liability + prepaid rentals + initial
     direct costs − incentives + PV of restoration costs
   - Month-wise lease liability amortisation (effective interest method)
   - Month-wise ROU depreciation (straight-line over the lease term)
3. **Export to Excel** — saves all schedules to a multi-sheet workbook
   suitable for client working papers.
4. **Save/Load Template** — save a lease's input set as a `.json` file
   so recurring engagements (e.g. annual re-runs, similar leases across
   branches) can be reloaded instantly instead of re-keyed.

## Project structure (for maintenance)
```
ind_as_116_suite/
├── main.py                  Entry point (run this)
├── README.md
└── ind_as_116/
    ├── __init__.py           Package metadata
    ├── bootstrap.py          First-run dependency detection & install
    ├── models.py             LeaseInputs / LeaseResult data structures
    ├── engine.py             All Ind AS 116 calculations (no I/O)
    ├── excel_export.py       Excel workbook export
    └── gui.py                Tkinter GUI (install log + main window)
```

The calculation engine (`engine.py`) is fully decoupled from the GUI —
it can be imported and run headlessly (e.g. from a script that batch-
processes many client leases from a CSV, or from a future web/CLI
front-end) without any Tkinter dependency:

```python
from datetime import date
from ind_as_116.models import LeaseInputs
from ind_as_116.engine import LeaseEngine
from ind_as_116.excel_export import export_to_excel

inputs = LeaseInputs(
    lease_commencement_date=date(2025, 4, 1),
    lease_term_months=60,
    monthly_rental=100000,
    incremental_borrowing_rate_annual=0.10,
)
result = LeaseEngine(inputs).run()
print(result.summary)
export_to_excel(result, "lease_model.xlsx")
```

## Key accounting reference
Ind AS 116 (Leases) — lessee recognition and initial measurement:
the Right-of-Use asset is measured at cost, and the lease liability
at the present value of lease payments not paid at the commencement
date, discounted using the interest rate implicit in the lease if
readily determinable, or otherwise the lessee's incremental
borrowing rate.

## Notes on assumptions built into this model
- Depreciation is charged straight-line over the full lease term. If
  the underlying asset's useful life is shorter and ownership does not
  transfer, adjust `build_depreciation_schedule()` accordingly.
- Variable lease payments (not based on an index/rate), sublease
  accounting, and lease modification/reassessment are **not** yet
  modelled — flagged here so future maintainers know the current scope
  boundary.
- All amounts are assumed to be in a single currency (no FX translation
  built in).

## Extending this suite
Because the engine, GUI, and export layers are separate modules,
common extensions are isolated to one file each:
- New calculation logic (e.g. lease modifications) → `engine.py`
- New input fields → add to `LeaseInputs` in `models.py` and to the
  `FIELDS` list in `gui.py`
- New export formats (e.g. PDF working paper) → new module alongside
  `excel_export.py`
# INNFLOW — Enterprise Hotel Operations & Management Ecosystem
**AICA Level-2 Capstone Project**  
**Author:** CA Ankit Tandon  
**Target Industry:** Hospitality, Hotel Property Management & Internal Financial Controls
# Upload Your Project Folder to the AICA Level 2 Projects Repository

**Target repository:** [aiinicai/AICA-Level-2-Projects](https://github.com/aiinicai/AICA-Level-2-Projects)

This guide explains how to contribute your complete project folder to the **AICA-Level-2-Projects** repository using GitHub’s **Fork + Pull Request** workflow.

View your app in AI Studio: https://ai.studio/apps/af3a28f1-b3e2-43c9-b427-5bc8f8761be0
View your app in AI Studio: https://ai.studio/apps/b49c013d-e05a-4bda-abc3-766b35b09cb9
Two methods are covered:

1. **Website-only method** — no software installation required.
2. **Git command-line method** — recommended for complete project folders and projects containing many files.

---

## 🚀 Quick Start

### Option 1 — Run as Python script (IDLE or CMD)
```cmd
python "All Things PDF.py"
```

### Option 2 — Build as .exe (no Python needed to run)
```cmd
pip install pyinstaller
pyinstaller --onefile --noconsole --name "All Things PDF" "All Things PDF.py"
```
Your `.exe` will appear in the `dist\` folder.

---

## 📦 Requirements

Install once in CMD before first run:

```cmd
pip install pypdf pymupdf pillow
```

| Library | Version | Purpose |
|---------|---------|---------|
| pypdf | latest | Merge, split, encrypt, decrypt |
| pymupdf | latest | Compress, watermark, redact, page numbers, grayscale |
| pillow | latest | Image processing for compression |
| tkinter | built-in | GUI (comes with Python) |

> **Python 3.9 or higher required.**  
> tkinter is included with all standard Python Windows installers.

---

## 🛠️ All Tools

### 📂 Organize PDF
| Tool | What it does |
|------|-------------|
| **Merge PDF** | Combine 2 or more PDFs into one, in the order you select |
| **Split PDF** | Split into individual pages, or by custom page ranges (e.g. 1-3, 4-6) |
| **Organise Pages** | Visual thumbnail grid — rotate ↺↻, delete ✕, drag to reorder |

### ⚡ Optimize PDF
| Tool | What it does |
|------|-------------|
| **Compress PDF** | Reduces file size using image downsampling + stream deflation. Low / Medium / High levels. Works on scanned PDFs |
| **Repair PDF** | Rebuilds corrupt xref table, removes damaged objects |
| **Remove Metadata** | Strips author name, creation date, software info and GPS data |
| **Grayscale PDF** | Converts all pages to black & white — reduces size 60–80% |
| **Flatten PDF** | Bakes annotations and form fields into static content |
| **Remove Blank Pages** | Auto-detects and removes empty or near-blank scanned pages |

### ✏️ Edit PDF
| Tool | What it does |
|------|-------------|
| **Rotate PDF** | Rotate pages 90°, 180° or 270° — all pages or specific ones |
| **Watermark** | Stamp text over pages — set position, opacity, font size, colour, rotation |
| **Image Watermark** | Overlay a PNG/JPG image as watermark |
| **Page Numbers** | Add page numbers with 3×3 position grid, colour swatches, from/to page range |
| **Crop PDF** | Draw a rectangle directly on a page preview — crop current page or all pages |

### 🔒 PDF Security
| Tool | What it does |
|------|-------------|
| **Protect PDF** | Password-protect with user and/or owner password. Set print/copy permissions |
| **Unlock PDF** | Remove password from an encrypted PDF |
| **Redact Text** | Permanently black out text by keyword — irreversible |
| **Redact Regions** | Permanently black out custom rectangular areas by page |

---

## 🖥️ How to Use

1. **Open the app** — run `All Things PDF.py` in IDLE (press F5) or in CMD
2. **Click a tool card** on the home screen — the app navigates to the tool page
3. **Browse your PDF** using the file picker (dropzone)
4. **Set options** as needed (compression level, rotation, passwords etc.)
5. **Click the action button** (e.g. "Compress PDF") — a Save As dialog appears
6. **Choose where to save** — processing starts immediately after
7. **Status bar** at the bottom shows progress and result

All output files are also saved to:
```
C:\Users\YourName\AllThingsPDF_Output\
```

---

## 📁 File Structure

```
All Things PDF.py     ← the entire app in one file
README.md             ← this file
```

All output files go to `~/AllThingsPDF_Output/`  
Temporary files go to `~/AllThingsPDF_Temp/` (auto-cleaned)

---

## 🔒 Privacy

- **100% offline** — no data leaves your computer, ever
- No telemetry, no analytics, no internet connection required
- Files are processed locally and saved wherever you choose

---

## ⚙️ Building the .exe

```cmd
pip install pyinstaller
pyinstaller --onefile --noconsole --name "All Things PDF" "All Things PDF.py"
```

| Flag | Effect |
|------|--------|
| `--onefile` | Everything bundled into a single `.exe` |
| `--noconsole` | No black CMD window on launch |
| `--name "All Things PDF"` | Names the output file |

The `.exe` will be at:
```
dist\All Things PDF.exe
```

Copy it anywhere — Desktop, Documents, USB drive. No Python needed to run it.

> **Note:** First launch of the `.exe` may take 5–10 seconds as it unpacks.  
> Windows Defender may flag it — this is a known PyInstaller false positive. Click "Allow" or add an exclusion.

---

## 🐛 Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: pymupdf` | Run `pip install pymupdf` |
| `ModuleNotFoundError: pypdf` | Run `pip install pypdf` |
| `ModuleNotFoundError: PIL` | Run `pip install pillow` |
| App opens but compress shows 0% smaller | The PDF is already fully compressed — try High level |
| Compress is slow / not responding | Normal for very large scanned PDFs (80MB+). Wait for it to finish |
| `.exe` flagged by antivirus | Known PyInstaller false positive — click Allow or add exclusion |
| Scroll doesn't work with trackpad | Known tkinter limitation on Windows — use the scrollbar on the right |

---

## 📋 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `F5` in IDLE | Run the script |
| Mouse wheel | Scroll within tool panels |
| `Esc` / Back button | Return to home screen |

---

## 🏗️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.9+ |
| GUI | tkinter (built-in) |
| PDF reading/writing | pypdf |
| Advanced PDF ops | PyMuPDF (fitz) |
| Image processing | Pillow (PIL) |
| Packaging | PyInstaller |

---

## 📄 License

Free to use for personal and professional purposes.  
Built with open-source libraries — pypdf, PyMuPDF, Pillow.
This is a practical starter version and should be validated against your accounting workflow before relying on it for statutory or final financial reporting.
