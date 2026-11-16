# PDF Studio Pro 1.2.0

**Author:** Sandip Gupta  
**Programme:** AICA Level 2 – Capstone Project

PDF Studio Pro is a one-file, offline PDF toolkit for Windows offices, written in Python (PyQt5 + PyMuPDF). Every tool saves a *new* file; the original is never changed.

## What it does
- **Organise:** merge, split, extract, rearrange, page numbering, page tools (rotate/delete/crop/resize), compress (quality-first, "fit under N MB")
- **Edit:** click-to-edit text, add text/pictures/shapes/links, find & replace, annotations & forms, watermark/stamps, header/footer, metadata, bookmarks
- **Convert:** PDF ⇄ Image, PDF → Word / Excel / PowerPoint (editable slides) / Text / Markdown / HTML
- **Security:** passwords, redaction (PAN, Aadhaar, GSTIN, IFSC, phone, e-mail …), strip hidden data, digital signature (USB token / .pfx)
- **OCR:** searchable PDF, image OCR, scan clean-up, Indian-language support (Tesseract)
- **AI (optional):** local AI, office gateway, or internet AI service
- **Image tools:** resize, convert, compress to KB, EXIF strip, passport photo, QR/barcode, collage

## Files in this folder
| File | Purpose |
|---|---|
| `pdf_studio_pro.py` | The whole application (single file) |
| `build_exe.bat` | One-click Windows build script (PyInstaller) |
| `README_FIRST.txt` | How to build the .exe and what changed in 1.2.0 |
| `EDIT_PDF_GUIDE.txt` | Guide to the Edit PDF tool |
| `WHATS_NEW_1.2_GUIDE.txt` | Guide to the improved features in 1.2 |

## How to run
1. Install Python 3.9+ (tick "Add python.exe to PATH").
2. `python pdf_studio_pro.py` (missing libraries are installed on first run).
3. For OCR, install [Tesseract (UB-Mannheim build)](https://github.com/UB-Mannheim/tesseract/wiki) with the language packs you need.

## Build a Windows .exe
Keep `pdf_studio_pro.py`, `build_exe.bat` and `README_FIRST.txt` in one folder and double-click `build_exe.bat`. See `README_FIRST.txt` for details.

## Not included
The compiled `dist/` output (~500 MB) and the Tesseract installer (~26 MB) are not in this repository; both are regenerated/downloaded by following the steps above.
