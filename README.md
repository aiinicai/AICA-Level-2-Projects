# 📄 All Things PDF

A fully offline, professional PDF utility desktop app built with Python and tkinter.  
Inspired by iLovePDF. Green & white design based on DPS Family colour scheme.  
No internet required. No browser. No server. Just run and use.
# Ledger Reconciliation & Reporting Desktop App

## Files
- `reconciliation_app.py` - desktop application
- `requirements.txt` - Python dependencies
- `Install_and_Run.bat` - installs dependencies and opens the app

## Usage
1. Install Python 3.10+.
2. Double-click `Install_and_Run.bat`.
3. Select Company Books and Party Books.
4. Enter the reconciliation/cut-off date.
5. Select an output folder.
6. Click Run Reconciliation & Generate Reports.

## Supported input
Excel, CSV, PDF and JPEG/PNG images.

## Important OCR note
For image OCR, install the Tesseract OCR Windows engine separately and ensure it is available in PATH. The application does not fabricate unreadable transactions. Complex scanned PDFs may require manual review.

## Current matching logic
The app normalizes dates, references, narrations, debit/credit values and balances, then attempts evidence-based transaction matching. Ambiguous matches are flagged as review items rather than silently accepted.
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
