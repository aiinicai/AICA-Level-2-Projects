**Intercompany Invoice Consistency Checker - AICA Level 2 — Individual Capstone Project (Module C)**
An agentic audit-readiness tool designed for Chartered Accountants to automate the batch cross-examination of intercompany invoices against master agreements and certified Revenue Support Schedules. The system combines Computer Vision/OCR for unstructured extraction, deterministic Python logic for mathematical and contractual reconciliation, OpenRouter free-tier LLMs for constrained executive synthesis, and automated generation of auditable Word working-paper memorandums.
---
## 1. Professional Context & Problem Statement
Reconciling intercompany management service fees under transfer pricing regulations (e.g., Chapter X of the Indian Income-tax Act, 1961, and OECD Transfer Pricing Guidelines) requires rigorous documentation of the "benefit test" and arm's-length fee bases. Manual examination across large invoice batches is error-prone, particularly when identifying subtle discrepancies such as:
- Inappropriate inclusion of extraordinary/non-operating income in the fee base.
- Subtle application of incorrect fee rates across billing cycles.
- Currency denomination mismatches across jurisdictions.
- Entity name drift between legal agreements and billing templates.
This tool establishes an automated, auditable review pipeline: upload the master agreement once, provide the monthly certified Revenue Support Schedules, upload any batch of invoices (digital or scanned), and obtain deterministic consistency verdicts paired with an AI-generated working paper memo.
---
## 2. AICA Level 2 Module Coverage
This capstone integrates competencies across the AICA Level 2 curriculum:
| Course Module | Technical Implementation in Solution |
|---|---|
| **Module 3: Computer Vision** | `backend/extraction.py`: Dual-pipeline document processing. Direct digital PDF extraction via `pdfplumber` with fallback to rasterization (`pdf2image`) and optical character recognition via `pytesseract` for scanned or photographed documents. Includes confidence tracking where OCR-derived fields are flagged for mandatory auditor inspection. |
| **Module 6: Python Fundamentals for CAs** | `backend/reconciliation.py`: Pure deterministic cross-checking logic. Implements fuzzy string matching (`difflib.SequenceMatcher`) for legal entity names, date validation against agreement tenures, Indian Lakhs/Crores and Western number normalization, and mathematical rate-reconciliation algorithms. |
| **Module 2 & 10: Agentic AI & Connectors** | `backend/agent.py`: Agentic synthesis using OpenRouter's API router to access zero-cost models (`meta-llama/llama-3.3-70b-instruct:free`, `qwen/qwen-2.5-72b-instruct:free`). Strict guardrail engineering confines the model to summarizing verified findings without asserting new facts or altering extracted numbers. |
| **Module 7: Full-Stack Web App Development** | `frontend/index.html` + `manifest.json`: Single-page Progressive Web App (PWA) with drag-and-drop document upload. `backend/server.py`: Multi-threaded Flask REST API (`/api/reconcile`, `/api/download`) handling concurrent multipart uploads with UUID file-isolation. |
| **Module 4: Communication Automation & Data Visualization** | `backend/memo_builder.py`: Programmatic generation of professional audit working papers (`.docx`) utilizing `python-docx`. Builds severity-coded status tables, revenue reference schedules, and per-invoice finding breakdowns. |
| **Module 9: AI-Driven Workflow Automation** | `server.py (run_pipeline)`: End-to-end batch automation orchestrating extraction, deterministic reconciliation, LLM narrative synthesis, and document artifact generation without intermediate manual handling. |

---

## 3. System Architecture & Workflow

[Master Agreement] [Revenue Schedules] [Invoice Batch]
\ | /
\ | /
v v v
+---------------------------------------------------+
| Module 3: extraction.py (CV / OCR) |
| - Direct Text Parser / Tesseract OCR Fallback |
| - Lakhs/Crores & International Number Normalizer |
| - Dynamic Fee Formula & Entity Extractor |
+---------------------------------------------------+
|
v
+---------------------------------------------------+
| Module 6: reconciliation.py (Python Engine) |
| - Counterparty Fuzzy Matching (Threshold: 80%) |
| - Operating vs. Total Revenue Base Validation |
| - Contractual Fee Rate Diagnostic Engine |
| - Currency & Contract Effective Period Checks |
+---------------------------------------------------+
|
v
+---------------------------------------------------+
| Module 2/10: agent.py (OpenRouter Free Tier) |
| - Strictly Zero-Cost Model Routing (:free) |
| - Guardrailed Executive Summary & Next Steps |
| - Native JSON Sanitization & Resiliency Retry |
+---------------------------------------------------+
|
v
+---------------------------------------------------+
| Module 4: memo_builder.py (python-docx) |
| - Batch Audit Working Paper Generation (.docx) |
| - Certified Schedule Traceability Section |
+---------------------------------------------------+



---

## 4. Key Engineering Highlights

### A. Certified Revenue Base vs. Total Revenue Distinction
Agreements typically stipulate management fees as a percentage of *Operating Revenue* alone, excluding non-operating extraordinary income (e.g., asset liquidations, insurance proceeds). The reconciliation engine cross-checks billed amounts against certified monthly Revenue Support Schedules. If an invoice calculates fees against Total Revenue, the engine flags this as a `CRITICAL` finding and calculates the exact overcharge.

### B. Fee Rate Diagnostic Engine
When an invoiced amount differs from contractual terms, the engine reverse-calculates the applied effective rate:
$$\text{Implied Rate} = \left(\frac{\text{Invoiced Amount}}{\text{Certified Operating Revenue}}\right) \times 100$$
If an invoice applies an unauthorized percentage (e.g., billing 7% instead of the contractual 6%), the audit memo explicitly reports the applied rate versus the contractual rate and states the variance amount.

### C. Zero-Cost, Private LLM Orchestration
`agent.py` connects to OpenRouter via standard HTTP utilities (`urllib`), querying models on the `:free` tier. This design guarantees:
- **Zero Cost:** The account balance remains `$0.00`; no credit card is required.
- **Privacy:** Requests exclude identifying tracker headers.
- **Fault Tolerance:** If a free model experiences high traffic, the engine cycles through fallback free models automatically.

---

## 5. Directory Structure

invoice-checker/ ??? backend/ ? ??? agent.py # OpenRouter LLM narrative generation ? ??? extraction.py # Document extraction & OCR parsing ? ??? reconciliation.py # Deterministic auditing & rate checks ? ??? memo_builder.py # Word memo (.docx) assembly ? ??? server.py # Flask REST API backend ? ??? manual_export.py # Offline CLI prompt exporter ? ??? manual_build_memo.py # Offline memo builder ? ??? requirements.txt # Python dependencies ? ??? .env.example # Environment template ??? frontend/ ? ??? index.html # PWA user interface ? ??? manifest.json # PWA configuration ??? sample_docs/ # Demonstration agreements, schedules & invoices ??? output/ # Generated audit working papers 



---

## 6. Installation & Execution Guide

### Prerequisites
- Python 3.10 to 3.12 (Windows / macOS / Linux)
- System OCR utilities:
  - **Windows**: Install Tesseract-OCR and Poppler; add their `bin` directories to your system `PATH`.
  - **Ubuntu/Debian**: `sudo apt install tesseract-ocr poppler-utils`
  - **macOS**: `brew install tesseract poppler`

### Step 1: Environment Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install python-docx openai python-dotenv
Step 2: Configure API Key (Zero-Cost Free Tier)
1. Generate a free API key from OpenRouter.ai (leave credit limits blank or set to $0.00).

2. Create a .env file in the backend/ directory:

Code snippet
OPENROUTER_API_KEY=sk-or-v1-your-free-key-here
Step 3: Run the Application
Bash
python server.py
The Flask backend will launch at http://localhost:5002. Open frontend/index.html in any web browser to upload agreements, revenue support schedules, and invoices for automated reconciliation. 


7. Audit Logging & Verification Results
The pipeline has been validated across standard test scenarios:

Test CaseDocument ConditionVerification StatusSystem Finding1. Standard Clean InvoiceFully compliant with agreement and scheduleOKAll counterparty, currency, term, and fee checks pass.
2. Unauthorized Fee RateInvoice applies incorrect fee percentage (e.g., June cycle)CRITICALFlags Incorrect Fee Percentage Applied, diagnoses effective rate vs contractual rate.
3. Fee Base DistortionFee computed on Total Revenue instead of Operating RevenueCRITICALFlags Fee Computed on Total Revenue, calculates overcharge attributable to extraordinary income.
4. Entity Name DriftInvoice lists non-contracted counterparty variantCRITICALFlags Counterparty Name Mismatch via fuzzy similarity check.
5. Currency MismatchInvoice billed in foreign currency (e.g., USD instead of INR)CRITICALFlags Currency Mismatch and disables cross-currency numeric fee computation.
6. Degraded Scan / ImageScanned invoice processed via OCRREVIEWPasses extraction but flags OCR-derived fields for mandatory manual verification.
8. Professional Disclaimers
* Audit Working Paper: This software is designed as an internal audit-readiness and pre-check tool; it does not replace the statutory audit responsibilities or professional judgment of a Chartered Accountant.

* Data Privacy & Security: In accordance with ICAI guidelines for the use of AI platforms, synthetic data must be utilized for testing and demonstration. No client data or personally identifiable information (PII) should be submitted to external LLM APIs. 

Developed for the AICA Level 2 Certificate Course (Module C Capstone Submission), The Institute of Chartered Accountants of India (ICAI).



