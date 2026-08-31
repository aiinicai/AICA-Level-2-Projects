# AICA-Level-2-Projects_Batch80_VinayBBachhuka
# 📄 PDF Processing Suite

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat&logo=flask&logoColor=white)
![PyMuPDF](https://img.shields.io/badge/PyMuPDF-1.23+-orange)
![License](https://img.shields.io/badge/License-MIT-lightgrey)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=flat&logo=windows&logoColor=white)

**A local, privacy-first web application for PDF flattening, compression, merging, and page numbering.**

**ICAI AICA Level 2 — Capstone Project**

[Features](#-features) •
[Installation](#-installation) •
[Usage](#-usage) •
[Screenshots](#-screenshots) •
[Documentation](#-documentation)

</div>

---

## 📖 About

**PDF Processing Suite** is a self-contained, locally-running web application built with Flask that provides intelligent PDF analysis and processing tools through a clean browser-based interface — **no internet connection or external servers required**.

The app analyzes any PDF, classifies its content (Scanned, Text-Heavy, Image-Heavy, Mixed), recommends the best processing mode, shows a comparison dashboard with real measured estimates, and then performs the selected operation — all while keeping your files 100% on your own machine.

---

## ✨ Features

### 🎯 Core Processing
- **🖼️ Flatten Only** — Renders each page as an image, removing forms/annotations for a print-safe, non-editable PDF
- **📦 Optimize / Compress Only** — Recompresses embedded images while keeping text searchable
- **⚡ Flatten + Optimize** — Combines both for maximum file size reduction
- **🧠 Smart Recommendation Engine** — Analyzes content and suggests the best mode automatically
- **📊 Comparison Dashboard** — Real, sample-measured estimates (not guesswork) for all 3 modes before you commit

### 🔗 Document Tools
- **Merge Multiple PDFs** — Combine files with drag-and-drop reordering
- **🔢 Page Numbering** — Standalone feature supporting:
  - Single file or entire folder (batch) processing
  - 6 position options (top/bottom × left/center/right)
  - 4 numbering formats (`1,2,3` / `Page 1 of 10` / `- 1 -` / `1/10`)
  - Odd/even/range page targeting
  - Skip-first-N-pages (for cover pages)

### 🔒 Security & Privacy
- **Password Detection & Unlock** — Automatically detects encrypted PDFs and prompts for password inline
- **No External Transmission** — Everything processes locally; nothing is ever uploaded anywhere
- **No Password Storage** — Passwords exist only in memory during the unlock operation

### ⚙️ Technical Features
- **Dual Compression Engine** — Built-in Python engine, or Ghostscript for stronger results (auto-detected)
- **Custom Output Location** — Choose your own output folder/filename, or let the app auto-generate sensible names
- **Auto-Refresh Estimates** — Re-calculate the dashboard instantly after changing settings, without re-uploading
- **Async Background Processing** — Live progress bar with cancel support
- **Processing Log** — CSV record of every file processed, kept in the output folder
- **Auto Dependency Setup** — Launcher checks and installs missing libraries automatically
- **Standalone .exe** — Packaged with PyInstaller — runs on any Windows PC without Python installed

---

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.8+, Flask 3.0 |
| PDF Rendering | PyMuPDF (fitz) |
| PDF Manipulation | pypdf |
| Image Processing | Pillow |
| Optional Compression | Ghostscript |
| Frontend | HTML5, CSS3, Vanilla JavaScript (no frameworks/CDN) |
| Persistence | JSON (settings), CSV (processing log) |
| Packaging | PyInstaller |

---

## 📦 Installation

### Prerequisites
- Python 3.8 or higher ([download here](https://www.python.org/downloads/))
- *(Optional)* [Ghostscript](https://ghostscript.com/releases/gsdnld.html) — for stronger compression

### Quick Start (Recommended)

```bash

The launcher automatically:

✅ Checks your Python version
✅ Installs any missing dependencies
✅ Creates required folders
✅ Checks for Ghostscript
✅ Starts the server and opens your browser

python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
python app.py

Windows One-Click
Just Flatten_PDF_B80_Vin_Utility.exe

🚀 Usage
Open the app — browser opens automatically at http://127.0.0.1:5000
Choose a tab:
⚡ Process PDF — flatten/compress a single file
🔗 Merge PDFs — combine multiple files
🔢 Page Numbers — add numbering to any PDF
Upload → Analyze → Configure → Process → Download
📘 For the complete step-by-step guide, see USER_GUIDE.md

🧪 Architecture Notes
All backend modules (pdf_analysis.py, pdf_flatten.py, pdf_compress.py, pdf_recommend.py, pdf_merge.py, pdf_password.py, pdf_config.py, pdf_log.py) are framework-agnostic — no Flask or Tkinter dependency — so they can be reused with any frontend.
Dashboard estimates are sample-measured, not formula-based: a few representative pages are actually processed at the target settings, and results are extrapolated — this is significantly more accurate than blind byte-per-pixel formulas, especially on real-world scanned documents.
Page numbering was deliberately separated from the Merge feature so it can be applied to any PDF, not just merged ones — while still offering a one-click shortcut from the merge result screen.
📋 Known Limitations
Only one file/job processes at a time (no parallel queue yet)
Processing log grows indefinitely — manual cleanup recommended for heavy use
1-bit Black & White flatten mode not suitable for documents with photos/color logos
Files over 100 MB may be slow to upload via browser
🔮 Roadmap (Phase 2)
 SQLite processing history with search/filter
 Charts & visualizations (size vs DPI, compression ratio by preset)
 RAM usage estimation before processing
 Log auto-rotation
 Parallel batch processing queue
📄 License
This project is submitted as a Capstone Project for ICAI AICA Level 2 and is provided under the MIT License.

🙏 Acknowledgments
PyMuPDF — PDF rendering engine
pypdf — PDF manipulation
Pillow — Image processing
Flask — Web framework
Ghostscript — Optional compression engine
<div align="center">
PDF Processing Suite — Built as a Capstone Project for ICAI AICA Level 2

</div> ```