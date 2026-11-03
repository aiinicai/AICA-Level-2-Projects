# ExpenseIQ – AICA L2 B121 – Shabbir Telwala

AICA Level 2 Capstone Project (Batch 121) submitted by **Shabbir Telwala**.

**ExpenseIQ** is a Python desktop application for sales and travel expense management. It reads receipts and invoices automatically, turns them into structured expense data and produces Excel reports.

## Key features

- **Desktop app**: PySide6 GUI over a local SQLite database.
- **Receipt and PDF reading**: OCR with RapidOCR (ONNX Runtime). PyMuPDF extracts PDF text and rasterises scanned pages.
- **Structured data extraction**: rule-based parsers and a table extractor capture the vendor, invoice number, dates, VAT/GST and totals, plus each invoice's line items.
- **Multi-invoice handling**: splits files that contain several invoices into separate records.
- **Duplicate detection**: flags invoices that have already been recorded.
- **Mobile uploads (optional)**: a token-secured FastAPI server accepts receipts from a phone.
- **Excel reporting**: expense reports generated with openpyxl.
- **Standalone Windows app**: packaged as an EXE with PyInstaller, so no Python installation is needed.

## Tech stack

Python · PySide6 · SQLite · FastAPI · RapidOCR (ONNX Runtime) · PyMuPDF · openpyxl · PyInstaller · pytest

## Development and testing

Developed iteratively with AI assistance. Verified with pytest unit tests and end-to-end OCR tests.

## Download the full project

The complete project is about 465 MB. That is larger than GitHub's file-size limit, so it is hosted as a GitHub Release:

**[Download AICA.L2.B121.Shabbir.Telwala.Expense.Tracker.zip](https://github.com/Shabbirtelwala/AICA-Level-2-Projects/releases/download/v1.0/AICA.L2.B121.Shabbir.Telwala.Expense.Tracker.zip)** (465 MB)

Release page: https://github.com/Shabbirtelwala/AICA-Level-2-Projects/releases/tag/v1.0

## How to use

1. Download the ZIP file from the link above.
2. Extract it to a folder on your Windows computer.
3. Run the ExpenseIQ EXE, or follow the instructions included in the extracted project folder.
