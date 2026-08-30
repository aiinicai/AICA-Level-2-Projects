# Technical Fact Sheet

**Application:** Bank Statement Converter  
**Version:** 1.0.0  
**Platform:** Windows 10/11  
**Python Runtime:** 3.12+  
**Execution Environment:** Local-First (Host: `127.0.0.1`)  

## Core Infrastructure
**Database:** SQLite (`sqlite3`)  
**Web Server:** Werkzeug (Flask built-in, local bind only)  
**Framework:** Flask (Python)  
**Frontend UI:** HTML5, CSS3, Vanilla JavaScript, local PDF.js integration  

## Processing Engines
**Digital PDF Parsing:** `pdfplumber`, `pypdf`  
**PDF Rendering/Rasterization:** `pypdfium2`  
**Optical Character Recognition (OCR):** `RapidOCR` + ONNX Runtime  
**Excel Generation:** `openpyxl`  
**Financial Arithmetic:** Python `decimal.Decimal`  

## Security & Privacy
**External AI Modules:** Disabled (by design)  
**Cloud OCR Engines:** Disabled (by design)  
**Telemetry:** None  
**Credential Storage:** N/A (Local application, no remote auth required)  

## Testing & Quality Assurance
**Testing Framework:** `pytest`  
**Latest Verified Regression Result:** 152 Passed / 0 Failed  

## Output Specifications
**Export Format:** Microsoft Excel (`.xlsx`)  
**Core Workbook Sheets:**
1. Transactions
2. Summary
3. Exceptions
4. Audit Trail  

## Deployment Architecture
**Bootstrap Automation:** `START_BANK_CONVERTER.bat`  
**Dependency Management:** Dynamic checksum validation (`requirements.txt`)  
**Instance Protection:** Localized socket binding collision detection and dynamic browser redirection.
