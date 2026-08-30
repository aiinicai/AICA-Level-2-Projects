# Bank Statement Converter

**Version:** 1.0.1
**Project Owner:** CA Ashutosh Somani

Built by CA Ashutosh Somani

Contact No.: 8108815175

Email ID: aiashutga@gmail.com

Made with ❤️ in India

A highly precise, offline-first tool for parsing, normalizing, and validating digital and scanned bank statements.

## Project Phases
- **Stage 0-1:** Foundation and UI Shell (Completed)
- **Stage 2:** Local PDF Intake & Preview (Completed)
- **Stage 3:** Digital PDF Extraction (Completed)
- **Stage 4:** Bank Detection & Normalization (Completed)
- **Stage 5:** Validation and Exception Engine (Completed)
- **Stage 6:** Bank Profile Engine (Completed)
- **Stage 7:** Advanced Review, Corrections and Audit Trail (Completed)
- **Stage 8:** Professional Excel Export (Completed)
- **Stage 9:** Local OCR Support for Scanned and Mixed PDFs (Completed)

## Current Features
- Upload digital or scanned PDF bank statements securely (no data leaves your machine).
- Reusable local bank/layout profiles with visual UI builder for geometry mapping.
- Extract raw text and word geometries robustly with `pdfplumber`.
- **Local OCR** for scanned and mixed digital/scanned PDFs using `rapidocr-onnxruntime`.
- Automatic scan detection per page with configurable word-count thresholds.
- OCR word bounding boxes mapped to PDF coordinate space with sub-pixel accuracy.
- OCR confidence scoring (0-100) per word with configurable minimum thresholds.
- Cooperative OCR cancellation and retry of failed pages.
- Parse standard and anomalous transaction rows into explicit Debit/Credit logic.
- Transaction-level exact `Decimal` balancing checks and statement reconciliation.
- Exception Engine routing discrepancies to an organized Exception Review queue.
- Exception-first side-by-side Advanced Review UI.
- Visual semantic source highlighting tracing anomalies to their PDF origin.
- Inline user correction of financial fields with exact `Decimal` precision.
- Merge, split, and non-transaction structural controls.
- Immutable machine baseline paired with an immutable Correction Audit Trail.
- Automatic profile-improvement suggestions based on repeated user corrections.
- Professional local Excel export using `openpyxl`.
- Comprehensive sheets including Transactions, Summary, Exceptions, and Audit Trail.
- Dynamic reviewed-data export fallback to machine-data.
- Safe, deterministic filename generation and spreadsheet formula injection protection.

## Strict Limitations & Stage Boundaries
- **No Cloud/AI:** All logic executes locally to protect PII.
- Machine extracted values are **never** overwritten; corrections are saved to an isolated review state.
- OCR runs entirely offline using local ONNX models — no network calls are made.

## 3. Requirements
- Windows 10/11
- Python 3.12 or higher (tested on Python 3.13.5)

### Python Version Compatibility
This application has been developed and tested on **Python 3.13.5** and targets **Python 3.12+**. All dependencies (including `rapidocr-onnxruntime==1.2.3` and `pypdfium2==5.13.0`) have been verified to install cleanly on both Python 3.12.x and 3.13.x.

## 4. First-time setup
No manual setup is required. The launcher script will automatically create a virtual environment, install necessary dependencies (via `pip install -r requirements.txt`), and create required directories.

## 5. How to start
Double-click `START_BANK_CONVERTER.bat` in the project root.
This will start the application and automatically open your default web browser to the application dashboard.

## 6. What the Stage 9 version currently supports
- Local PDF upload, decryption, and validation
- Deterministic extraction using local geometric constraints (Profiles)
- **Local OCR** for scanned PDFs using RapidOCR (ONNX Runtime)
- **Mixed PDF support**: automatic per-page scan detection and OCR routing
- **OCR confidence tracking** throughout the pipeline to Excel export
- Cooperative **OCR cancellation** and **retry of failed pages**
- Diagnostic visual verification and bounding box editors
- `Decimal`-safe strict arithmetic balancing
- Exception identification (Missing dates, anomalous balances)
- Human-in-the-loop Correction UI with full revision tracking
- Job-scoped immutable audit logging
- Professional Excel Export with strict auditing and OCR metadata

## 7. What it deliberately does NOT support yet
- Cloud APIs or External AI learning
- ERP integration (Tally)

## 8. Output/log/database locations
- Configuration: `config.ini`
- Database: `database/bank_statement_converter.db`
- Logs: `logs/application.log`
- Temp files: `temp/`
- Output files: `output/`
- OCR models: `models/ocr/` (auto-downloaded on first use)

## 9. How to stop application
Close the command prompt window that opened when running the `START_BANK_CONVERTER.bat` script, or press `Ctrl+C` in that window.

## 10. Basic troubleshooting
- If the browser does not open automatically, manually navigate to `http://127.0.0.1:8765` (or the port specified in `config.ini`).
- Check `logs/application.log` for any startup or runtime errors.
- Ensure Python 3.12+ is installed and available in your system's PATH.

## 11. Offline Runtime Verification
This application is designed to run completely offline. To verify:

1. **Enable Airplane Mode** (or disconnect from all networks).
2. Launch the application using `START_BANK_CONVERTER.bat`.
3. Upload a scanned PDF bank statement.
4. Trigger OCR processing.
5. Verify that OCR completes successfully with no network errors.
6. Export to Excel and verify OCR metadata columns are populated.

All OCR models are stored locally in `models/ocr/` and no network calls are made during processing.

## 12. OCR Coordinate Conversion
The OCR engine renders each PDF page as a raster image at the configured DPI (`ocr.render_dpi`, default 250). The rendering uses `pypdfium2` with `rotation=0`, which means `pypdfium2` returns the page raster in its natural orientation (after applying any `/Rotate` flag from the PDF metadata). The `GetPageSize` API already returns rotated dimensions.

**Coordinate mapping formula:**
```
scale_x = pdf_page_width / rendered_pixel_width
scale_y = pdf_page_height / rendered_pixel_height

pdf_x = image_x * scale_x
pdf_y = image_y * scale_y
```

All coordinates are clamped to `[0, page_width]` × `[0, page_height]` to prevent out-of-bounds values. The top-left corner of the PDF page is `(0, 0)`.

