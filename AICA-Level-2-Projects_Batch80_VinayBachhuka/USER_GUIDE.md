# 📄 PDF Processing Suite — User Guide

### ICAI AICA Level 2 — Capstone Project

![Version](https://img.shields.io/badge/Version-2.0-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Local%20Web%20App-green)

---

## 📌 Table of Contents

1. [Introduction](#1-introduction)
2. [Getting Started](#2-getting-started)
3. [Interface Overview](#3-interface-overview)
4. [Feature 1 — Process PDF](#4-feature-1--process-pdf)
5. [Feature 2 — Merge PDFs](#5-feature-2--merge-pdfs)
6. [Feature 3 — Page Numbers](#6-feature-3--page-numbers)
7. [Password-Protected PDFs](#7-password-protected-pdfs)
8. [Output Settings](#8-output-settings)
9. [Settings Persistence](#9-settings-persistence)
10. [Processing Log](#10-processing-log)
11. [Troubleshooting](#11-troubleshooting)
12. [FAQ](#12-faq)
13. [Glossary](#13-glossary)

---

## 1. Introduction

**PDF Processing Suite** is a locally-running web application that helps you:

- 🖼️ **Flatten** PDFs (convert pages to images — great for making documents print-safe and non-editable)
- 📦 **Compress** PDFs (reduce file size while keeping text searchable)
- 🔗 **Merge** multiple PDFs into one
- 🔢 **Add page numbers** to any PDF
- 🔒 **Unlock** password-protected PDFs

Everything runs **100% locally** on your computer — no files are ever uploaded to the internet. Your documents stay private.

---

## 2. Getting Started

### Option A — Using the Launcher (Recommended)

1. Double-click **`run.bat`** (Windows)
2. Wait for the automatic checks to complete
3. Your browser will open automatically at `http://127.0.0.1:5000`

### Option B — Using the Standalone .exe

1. Double-click **`PDF_Processing_Suite.exe`**
2. Wait a few seconds for the server to start
3. Your browser will open automatically

### First-Time Checks

On first run, the app automatically:
- ✅ Checks your Python version (if running from source)
- ✅ Installs any missing libraries
- ✅ Creates `uploads/` and `outputs/` folders
- ✅ Checks for Ghostscript (optional — improves compression)

> 💡 **Tip:** If Ghostscript is not installed, the app still works perfectly using its built-in Python compression engine.

---

## 3. Interface Overview

The application has **3 main tabs** at the top:

| Tab | Purpose |
|-----|---------|
| ⚡ **Process PDF** | Flatten, compress, or both — with smart recommendations |
| 🔗 **Merge PDFs** | Combine multiple PDF files into one |
| 🔢 **Page Numbers** | Add page numbers to any PDF (single file or batch folder) |

A status indicator in the top-right corner always shows what the app is currently doing:

| Status | Meaning |
|--------|---------|
| ● Ready | Idle, waiting for your action |
| ● Working | Currently processing |
| ● Done | Task completed successfully |
| ● Error | Something went wrong |

---

## 4. Feature 1 — Process PDF

This is the main tab for flattening and/or compressing a single PDF.

### Step 1 — Upload

1. **Drag and drop** your PDF onto the upload area, **or**
2. Click **Browse File** to select it manually

Supported: `.pdf` files up to 100 MB.

If your file is password-protected, a password prompt will appear automatically — see [Section 7](#7-password-protected-pdfs).

### Step 2 — Analyze

Click **🔍 Analyze PDF**. The app will:

- Scan sample pages of your document
- Classify it (e.g., *Scanned PDF*, *Text-Heavy*, *Image-Heavy*, *Mixed*)
- Show a detailed breakdown:

| Info Shown | Description |
|-----------|-------------|
| **General Info** | File name, size, page count, PDF version, orientation |
| **Content Analysis** | % of text, images, vector graphics; scanned detection; forms/annotations present |
| **Classification** | Overall content type with reasoning |
| **Recommendation** | Suggested best mode for this specific file |
| **Comparison Dashboard** | Estimated output size, reduction %, processing time, and quality impact for all 3 modes |

> 📊 The dashboard estimates are based on **actually processing sample pages** — not guesswork — so they are quite accurate.

### Step 3 — Choose Mode

Three processing modes are available:

#### 🖼️ Flatten Only
Converts every page into a rendered image and rebuilds the PDF from those images.

**Use when:**
- The PDF has forms, annotations, or editable fields you want removed
- You need a "print-safe" non-editable version
- The document is a scanned image already

**Settings:**

| Setting | Range | Description |
|---------|-------|-------------|
| **Render DPI** | 72–600 (presets: 72, 100, 150, 200, 300) | Higher = sharper but larger file |
| **JPEG Quality** | 1–95 (presets: 40, 55, 65, 75, 85, 95) | Higher = better quality but larger file |
| **Color Mode** | Color / Grayscale / Black & White | Grayscale/B&W further reduce size |

> 💡 You can click a preset button OR type any custom number directly into the input box.

#### 📦 Optimize / Compress Only
Recompresses embedded images and strips unnecessary data — **keeps your text searchable and selectable**.

**Use when:**
- The PDF is mostly text and you want to keep it searchable
- You just need moderate size reduction without changing the document structure

**Settings:**

| Profile | Best For |
|---------|----------|
| **Light** | Minimal changes, best quality retained |
| **Balanced** ⭐ | Good size/quality trade-off (recommended default) |
| **Aggressive** | Stronger compression |
| **Maximum** | Smallest possible file size |

**Engine:**
- **Python** (built-in, always available)
- **Ghostscript** (if installed — generally gives stronger compression on images)

#### ⚡ Flatten + Optimize
Combines both — flattens first, then compresses the result. Gives the **maximum size reduction** but text is no longer selectable (since it's now an image).

### Step 4 — Output Settings

Before processing, you can customize:

| Field | Behavior if Left Blank |
|-------|----------------------|
| **Output Folder** | Saves to the default `outputs/` folder next to the app |
| **Output Filename** | Auto-generated as: `originalname_flatten_150dpi.pdf` (or similar based on mode/settings) |

> ⚠️ If you type a custom folder path that doesn't exist or isn't writable, the app automatically falls back to the default `outputs/` folder and lets you know.

### Step 5 — Refresh Estimates (Optional)

If you change any setting **after** analyzing (like DPI or compression profile), a yellow reminder bar appears:

> ⚠️ Settings changed — 🔄 Refresh Dashboard Estimates

Click this to re-calculate the comparison dashboard with your new settings — **without re-uploading the file**.

### Step 6 — Process

Click **⚡ Process PDF**. A live progress bar shows:
- Current step (e.g., "Step 1/2 — Flattening pages...")
- Percentage complete
- A scrolling log of what's happening

You can click **✕ Cancel** at any time to stop.

### Step 7 — Download

Once complete, you'll see:
- **Original Size**, **Reduction %**, and **Output Size**
- The exact folder path where the file was saved
- **⬇️ Download Processed PDF** button
- **🔄 Process Another File** button to start fresh

---

## 5. Feature 2 — Merge PDFs

Combine two or more PDF files into a single document.

### Step 1 — Add Files

1. **Drag and drop** multiple PDFs, **or** click **Browse Files** and select multiple files at once
2. Each file appears in a list showing its name and size

### Step 2 — Reorder Files

The merge order matters! You can reorder files by:
- **Dragging rows** up or down in the list
- Using the **↑ / ↓** buttons next to each file
- Removing a file with **✕**

### Step 3 — Handle Locked Files

If any uploaded file is password-protected, it will show a **🔒 LOCKED** badge with an inline password box right in the file list:

1. Type the password directly in that file's row
2. Click **🔓 Unlock**
3. Once unlocked, the badge disappears and the file becomes ready to merge

> ⚠️ **Important:** You cannot merge until **all** locked files are unlocked. The app will block the merge and show a clear error if any file is still locked.

### Step 4 — Output Settings

Same as Process PDF — leave folder/filename blank for automatic defaults:

Default filename: merged_YYYYMMDD_HHMMSS.pdf
Default folder:   outputs/ folder next to the app

### Step 5 — Merge

Click **🔗 Merge PDFs**. Progress is shown live, file by file.

### Step 6 — After Merging

You'll see the merge results:
- Number of files merged
- Total pages in the combined document
- Output file size

Three buttons are available:

| Button | Action |
|--------|--------|
| ⬇️ **Download Merged PDF** | Downloads the combined file |
| 🔢 **Add Page Numbers to This File** | Jumps directly to the Page Numbers tab with this file pre-loaded — no need to re-upload! |
| 🔄 **Merge More Files** | Clears the list to start a new merge |

> 💡 Page numbering is **not** done automatically during merge — it's a separate step so you have full control over numbering style, and can add numbers to *any* PDF, not just merged ones.

---

## 6. Feature 3 — Page Numbers

A fully independent feature for adding page numbers to any PDF — whether it came from a merge, or any PDF on your computer.

### Choose Your Mode

| Mode | Use When |
|------|----------|
| 📄 **Single File** | You want to number one specific PDF |
| 📁 **Batch Folder** | You want to number every PDF inside a folder automatically |

### Single File Mode

1. Upload your PDF (drag & drop or browse)
2. If password protected, unlock it first (same as other tabs)
3. Configure your numbering options (see below)
4. Set output folder/filename (optional)
5. Click **🔢 Add Page Numbers**
6. Download the result

### Batch Folder Mode

1. Type the **full path** to a folder containing the PDFs you want numbered
Example: C:\Users\YourName\Documents\Invoices

2. Optionally specify an output folder
Default: creates a "numbered_output" sub-folder inside your input folder

3. Configure numbering options
4. Click **🔢 Add Page Numbers**
5. A results table shows the outcome for **each file**:

| File | Status | Pages Numbered |
|------|--------|-----------------|
| invoice_jan.pdf | ✔ Success | 12 |
| invoice_feb.pdf | ✔ Success | 8 |
| invoice_locked.pdf | ✘ Password protected | — |

### Numbering Options (Both Modes)

| Setting | Options |
|---------|---------|
| **Position** | Bottom Center / Bottom Left / Bottom Right / Top Center / Top Left / Top Right |
| **Format** | `1, 2, 3...` / `Page 1 of 10` / `- 1 -` / `1 / 10` |
| **Start From** | Any starting number (default: 1) |
| **Font Size** | 6–36 pt (default: 12pt, black text) |
| **Apply To** | All Pages / Page Range / Odd Pages Only / Even Pages Only |
| **Skip First N Pages** | Useful for skipping a cover page before numbering starts |

A **live preview** shows exactly how your page numbers will look before you apply them, e.g.:
Preview: Page 1 of 10

---

## 7. Password-Protected PDFs

Any tab that accepts a PDF upload (Process, Merge, Page Numbers) automatically detects if the file is encrypted.

### How It Works

1. Upload your password-protected PDF
2. A yellow **🔒 password box** appears automatically
3. Type the PDF's password
4. Click **🔓 Unlock**
5. If correct — the file becomes usable immediately, without saving a separate unlocked copy anywhere permanent
6. If incorrect — a clear error message tells you to try again

> 🔐 **Privacy note:** Passwords are never saved, logged, or stored anywhere. They exist only in memory for the moment of unlocking.

> ✅ The final processed/merged/numbered output file will **never** have a password — it's always saved as a regular, open PDF.

---

## 8. Output Settings

Every processing feature (Process, Merge, Page Numbers) lets you control where your file is saved.

### If You Leave Fields Blank

| Field | Default Behavior |
|-------|------------------|
| **Output Folder** | Saves inside the app's `outputs/` folder |
| **Output Filename** | Auto-generated based on original name + settings used |

### If You Specify a Custom Folder

- Type the **full path** (e.g., `C:\Users\YourName\Documents\Processed`)
- The folder will be **created automatically** if it doesn't exist
- If the path is invalid or not writable, the app **automatically falls back** to the default `outputs/` folder and lets you know

### Auto-Generated Filename Examples

| Mode | Example Output Name |
|------|---------------------|
| Flatten Only (150 DPI) | `document_flatten_150dpi.pdf` |
| Compress Only (Balanced) | `document_compress_Balanced.pdf` |
| Flatten + Optimize | `document_flatten_compress_150dpi.pdf` |
| Merge | `merged_20240115_143022.pdf` |
| Page Numbers | `document_numbered.pdf` |

---

## 9. Settings Persistence

The app remembers your last-used settings automatically between sessions:

- Last selected processing mode
- Last DPI / JPEG quality values
- Last compression profile / engine choice
- Last color mode

This is stored in a small local file called `pdf_suite_config.json` next to the app — no internet connection involved.

---

## 10. Processing Log

Every file you process, merge, or number is recorded in a CSV log file:

outputs/pdf_suite_log.csv

This log includes:
- Timestamp
- Input/output file names
- Mode used and settings applied
- Original and output file sizes
- Reduction percentage
- Success or failure status

You can open this file in Excel or any spreadsheet program to review your processing history.

---

## 11. Troubleshooting

### The browser shows a blank/loading page

- Check the terminal window for red error messages
- Make sure `templates/index.html` and `static/` folder exist next to the app
- Try refreshing the browser (Ctrl+F5)

### "Not enough image data" error during compression

- This usually resolves itself with the latest version of the app
- Try using **Compress Only** mode instead of **Flatten + Optimize** to isolate the issue
- Try switching the compression **Engine** from Python to Ghostscript (if installed), or vice versa

### Dashboard shows "No data available"

- Make sure you clicked **Analyze PDF** before expecting dashboard results
- Try clicking **🔄 Refresh Estimates**

### Merge is blocked with a password error

- Check the file list for any 🔒 LOCKED badges
- Unlock each locked file individually before trying to merge again

### Custom output folder isn't being used

- Verify the folder path is typed correctly (use full paths, not relative ones)
- Check that you have write permission to that folder
- The app will automatically fall back to the default `outputs/` folder if there's an issue

### The .exe won't start on another computer

- Make sure you're using the version built with `PDF_Suite.spec` (not a raw `pyinstaller app.py` command)
- Antivirus software sometimes flags new .exe files — check your antivirus quarantine/logs

---

## 12. FAQ

**Q: Does this app send my files to the internet?**
A: No. Everything runs locally on `127.0.0.1` (your own computer). No files ever leave your machine.

**Q: Can I process a PDF larger than 100 MB?**
A: The current limit is 100 MB per upload. Very large files may also take longer to process.

**Q: What happens to my uploaded files after processing?**
A: They remain in the local `uploads/` folder. You can safely delete files from this folder periodically if you want to free up space — it doesn't affect already-downloaded results.

**Q: Can I flatten a PDF without losing quality?**
A: Use a higher DPI (e.g., 300) and higher JPEG quality (e.g., 95) — this preserves visual quality but results in a larger file size than lower settings.

**Q: Is Ghostscript required?**
A: No — it's optional. The built-in Python engine works well on its own. Ghostscript can give stronger compression results for certain files.

**Q: Can I add page numbers to a merged PDF automatically?**
A: Not automatically during merge — but right after merging, click **"🔢 Add Page Numbers to This File"** to jump straight to the Page Numbers tab with your merged file already loaded.

---

## 13. Glossary

| Term | Meaning |
|------|---------|
| **Flatten** | Convert PDF pages into images, removing editable content |
| **DPI** | Dots Per Inch — resolution of the rendered image; higher = sharper |
| **Compression Profile** | A preset combination of quality/downsampling settings |
| **Ghostscript** | An external, optional tool for stronger PDF compression |
| **Dashboard** | The comparison table showing estimated results for all 3 modes |
| **Sample-based Estimation** | Estimating final output by actually processing a few sample pages first |
| **Batch Processing** | Processing every file in a folder automatically |

---

## 📞 Support

If you encounter an issue not covered in this guide, check the terminal/console window for detailed error messages — these usually indicate exactly what went wrong.

---

*PDF Processing Suite — ICAI AICA Level 2 Capstone Project*
*Built with Flask · PyMuPDF · pypdf · Pillow*

