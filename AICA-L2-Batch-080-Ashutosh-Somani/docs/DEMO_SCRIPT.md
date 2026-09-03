# Capstone Demonstration Script

*Target Duration: 5–10 minutes*

## Sequence

### 1. Introduction
* **Action:** Display the application directory.
* **Talking Point:** Introduce the Bank Statement Converter, emphasizing its core mission: transforming variable unstructured bank PDFs into standardized Excel files while ensuring total data integrity.

### 2. Privacy / Local Processing Architecture
* **Talking Point:** Highlight the local-first design decision. Emphasize that Chartered Accountants handle highly sensitive financial data, hence there is zero reliance on cloud APIs, external LLMs, or remote OCR servers. All processing is restricted to the host machine.

### 3. Launch Application
* **Action:** Double-click `START_BANK_CONVERTER.bat`.
* **Talking Point:** Explain the bootstrap process. The launcher automatically creates a virtual environment, installs dependencies, migrates the database, and binds to `127.0.0.1`.
* **Evidence:** The terminal output showing "[OK] Virtual environment found" and the browser launching automatically.

### 4. Upload Digital Sample
* **Action:** Use the UI to upload `samples/digital_statement_sample.pdf`.
* **Talking Point:** Walk through the initial intake validation and PDF rendering.

### 5. Preview Statement
* **Action:** Scroll through the PDF preview.
* **Evidence:** Show the built-in, secure PDF.js renderer that operates without external plugins.

### 6. Extract Transactions
* **Action:** Click "Extract".
* **Talking Point:** Explain the unified extraction pipeline using `pdfplumber` for digital text bounding boxes.

### 7. Bank Identification / Profile Matching
* **Action:** Show the system automatically matching the layout to the correct bank profile.
* **Talking Point:** Explain the Profile Engine, which avoids hardcoding rules and instead uses reusable JSON schemas.

### 8. Validate
* **Action:** Trigger the normalization and validation phase.
* **Talking Point:** Emphasize the shift to precise `Decimal` arithmetic instead of floating-point numbers, ensuring exact financial reconciliations across all rows.

### 9. Show an Exception
* **Action:** Navigate to the Exceptions view.
* **Talking Point:** Detail the "Exception-First" review paradigm. CAs do not have time to review 10,000 perfect rows; they only need to see where mathematical validation (prior balance + deposits - withdrawals != current balance) fails.

### 10. Review / Correct
* **Action:** Manually correct a flagged transaction in the Review UI.
* **Talking Point:** Explain that the original machine baseline is immutably preserved. User corrections are stored as an overlay, and validation rules instantly re-run upon saving.

### 11. Show Audit Trail
* **Action:** Switch to the Audit Log UI.
* **Evidence:** The history shows the exact timestamp, the original machine extraction, and the new user-supplied value.

### 12. Export Professional Excel
* **Action:** Export and download the `.xlsx` workbook.
* **Talking Point:** Note that `openpyxl` generates a professional spreadsheet.
* **Evidence:** Open the workbook to display the *Transactions*, *Summary*, *Exceptions*, and *Audit Trail* sheets.

### 13. Briefly Show Scanned PDF
* **Action:** Upload `samples/scanned_statement_sample.pdf`.
* **Talking Point:** Explain that the engine detects a lack of native text and seamlessly engages the OCR fallback pipeline.

### 14. Run Local OCR
* **Action:** Proceed with extraction.
* **Talking Point:** Emphasize the integration of `RapidOCR` and `ONNX Runtime` running locally.

### 15. Show OCR Confidence
* **Action:** Point out the OCR diagnostics.
* **Evidence:** Words below the confidence threshold are visually flagged, ensuring the CA knows exactly where the machine was uncertain.

### 16. Show Mixed PDF Support
* **Action:** Upload `samples/mixed_statement_sample.pdf`.
* **Talking Point:** Demonstrate page-by-page routing. Digital pages bypass OCR to save compute time, while scanned pages engage the ONNX model, merging perfectly in normalization.

### 17. System Diagnostics
* **Action:** Navigate to `/diagnostics`.
* **Talking Point:** Show the System Diagnostics screen, demonstrating deployment readiness, offline mode verification, and ZIP-slip protected Backup/Restore features.

### 18. Conclusion
* **Talking Point:** Summarize the successful synthesis of Python, offline OCR, and financial integrity checks into a production-ready desktop tool.

---

## Key Design Decisions & Talking Points

- **Local-First Privacy:** Client trust is paramount; cloud processing is disabled by design.
- **OCR Fallback, Not OCR-Everything:** Utilizing OCR only when strictly necessary dramatically improves processing speed and structural accuracy.
- **Unified Normalization Pipeline:** Output from both digital extractors and OCR engines normalize into the same intermediate schema, maintaining a single source of truth.
- **Decimal Precision:** Native float processing inherently introduces phantom pennies; strict Decimal typing solves this.
- **Immutability & Corrections:** The machine baseline is never permanently overwritten by a human. Overlays ensure complete forensic auditability.
- **Reusable Profiles:** New bank layouts are accommodated without changing core source code.
