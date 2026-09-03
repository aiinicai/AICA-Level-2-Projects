# Bank Statement Converter
## ICAI AI Level 2 Capstone Project

## Problem Statement
Bank statements universally differ by institution, formatting, and layout structure. The manual conversion of these statements into standardized Excel formats is highly repetitive and prone to human error. Furthermore, utilizing OCR on scanned documents introduces uncertainty. Any financial data processed by machines must be rigorously validated, completely auditable, and intuitively reviewable by Chartered Accountants prior to use.

## Solution
Bank Statement Converter is a local-first, privacy-respecting Python application designed to intelligently parse digital PDFs, execute offline OCR on scanned imagery, normalize disparate bank layouts, and perform strict Decimal-based financial validations. It delivers an exception-first review workflow where humans supervise the AI's extraction, producing a trusted, standardized Excel audit trail.

## Technology Stack
- **Backend:** Python, Flask, SQLite
- **PDF Parsing:** pdfplumber, pypdf, pypdfium2
- **Offline OCR:** RapidOCR + ONNX Runtime
- **Frontend:** HTML/CSS/Vanilla JavaScript, local PDF.js
- **Excel Generation:** openpyxl
- **Testing Engine:** pytest

## Architecture
1. **PDF Intake:** Accepts encrypted/unencrypted PDF uploads securely.
2. **Digital Extraction:** Parses native text layouts.
3. **OCR Fallback:** Identifies rasterized (scanned) pages and routes them to a local ONNX vision model.
4. **Bank Detection & Profile Engine:** Dynamically matches document headers to saved reusable bank profiles.
5. **Normalization:** Standardizes tables into Date, Narration, Withdrawal, Deposit, and Balance columns.
6. **Validation:** Checks structural integrity and performs strict mathematical balance reconciliations using exact Decimal arithmetic.
7. **Review/Audit:** Highlights exceptions (failed reconciliations) for manual human correction.
8. **Excel Export:** Packages the finalized, audited data into a professional workbook.

## AI / OCR Component
The system employs an embedded **RapidOCR (ONNX Runtime)** vision model. When a scanned page is detected, it is rasterized and processed locally. Words are mapped back to their original coordinates, allowing the exact same parsing and profile logic to process both digital and scanned datasets without relying on cloud APIs.

## Privacy
By design, all processing occurs on the client's local machine (`127.0.0.1`). There are zero telemetry hooks, external AI API calls, or cloud OCR dependencies. Uploaded files, database artifacts, and generated workbooks remain permanently sandboxed in the local filesystem.

## Validation Controls
Financial integrity is enforced via:
- **Decimal Type Safety:** Complete eradication of floating-point arithmetic errors.
- **Balance Reconciliation:** Cross-verifying `Prior Balance + Deposits - Withdrawals == Current Balance`.
- **Exception Flagging:** Any row that fails mathematical proofs or is missing data is highlighted.
- **Review Audit:** A complete historical log of any human correction is persisted.

## Key Outcomes
A professional, multi-sheet Excel workbook containing:
1. **Transactions:** The standardized ledger.
2. **Summary:** Aggregated inflows and outflows.
3. **Exceptions:** Rows requiring attention.
4. **Audit Trail:** Complete lineage of machine extraction vs. human corrections.

## Testing
The core engine is backed by a robust regression suite.
Latest Verified Regression:
- 152 passed
- 0 failed

## Deployment
Distribution is facilitated by a Windows `.bat` bootstrap sequence. `START_BANK_CONVERTER.bat` seamlessly detects Python 3.12+ installations on Windows 10/11, establishes a local virtual environment, installs checksum-verified dependencies, migrates the SQLite schema, and launches the browser interface without manual command-line intervention.

## Limitations
- OCR output quality is inherently bound to the DPI/legibility of the source scanned document.
- Unrecognized bank layouts will require a one-time profile configuration by the user.
- Automated tests rely on `openpyxl` programmatic assertions; visual styling checks in Microsoft Excel require manual verification.
- Source-based deployment mandates a pre-existing Python 3.12+ runtime installation.

## Future Enhancements
- Integration of a lightweight local LLM (e.g., Llama 3) for zero-shot categorization of transaction narrations.
- Support for extracting native XLSX and CSV inputs.
