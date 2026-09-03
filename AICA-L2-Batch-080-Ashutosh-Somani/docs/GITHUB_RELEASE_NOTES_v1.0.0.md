# Bank Statement Converter v1.0.0

## Highlights
This is the final ICAI Capstone submission release for the Bank Statement Converter. It brings a complete end-to-end, privacy-respecting financial analysis tool designed for Chartered Accountants to convert unstructured banking PDFs into standardized Excel workbooks.

## Features
- **Local-First Privacy:** Absolute zero dependency on cloud APIs or external telemetry.
- **Digital & Scanned PDF Support:** Intelligent routing processes native text via `pdfplumber` and engages a fallback offline OCR engine (`RapidOCR`) exclusively for scanned imagery.
- **Exact Financial Validations:** Mathematical reconciliations execute strictly using `Decimal` arithmetic, eliminating floating-point errors.
- **Exception-First Review:** Automatically flags mathematically invalid rows, requiring human review only where necessary.
- **Audit Trails:** Preserves the machine baseline immutably, documenting human corrections securely in the exported workbook.

## Privacy
By design, all document intake, database storage, OCR processing, and Excel generation occurs solely on `127.0.0.1`. No external network calls are made.

## Installation
Download the release ZIP and extract it to a directory on your Windows machine.
Run the startup script:
```
START_BANK_CONVERTER.bat
```
The script will automatically provision the local virtual environment, install dependencies, and launch your browser.

## Verified
Automated regression suite verified: **152 Passed / 0 Failed**.

## Release Integrity
**File:** `BankStatementConverter_v1.0.0.zip`
**SHA-256:** `304AF167A7D3BFD361CFA7092E8FA7B7F2D707F4E88D9F275D9329AEA55B5C83`

## Known Limitations
- Requires Python 3.12 or 3.13 pre-installed on the host system.
- OCR text fidelity is highly dependent on the DPI resolution of the source scanned document.
- New/unrecognized bank statement layouts will require a one-time profile configuration mapping in the application UI.
