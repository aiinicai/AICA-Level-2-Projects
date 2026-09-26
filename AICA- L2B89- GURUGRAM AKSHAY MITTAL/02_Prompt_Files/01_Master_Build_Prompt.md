# Prompt File 1: Master Build Prompt

**Project:** BRMCo Accounting Hub (Excel-to-Tally Accounting Automation Tool)
**AI tool used:** Claude (Anthropic), in the Claude desktop app's Code mode, an agentic AI coding assistant
**Prompting technique:** role prompting ("Act as a senior Python full-stack architect…"), a detailed requirement specification, explicit constraints (a "DO NOT" list), a staged development sequence, and a request for design before code.

The prompt below was given to the AI in a single message. Its content is reproduced in full. Only the layout has been tightened (long bullet lists joined into sentences, and the section 24 folder tree summarised) to keep it readable.

---

BRMCo ACCOUNTING HUB — PHASE 1
Two-Host Source-Code Architecture

Act as a senior Python full-stack architect and developer with expertise in accounting automation, TallyPrime integration, Excel automation, REST APIs and scalable software architecture.

I am a Chartered Accountant and want to develop a long-term accounting automation platform called:
BRMCo Accounting Hub

The system will eventually automate accounting entries, TallyPrime integration, GST data preparation, invoice extraction using AI, reporting and other CA-office workflows.
For Phase 1, do NOT build the entire platform. Build a strong and clean foundation for the accounting entry engine only.

## 1. VERY IMPORTANT ARCHITECTURE REQUIREMENT
I do NOT want an EXE-based application.
I want TWO SEPARATE SOURCE-CODE PROJECTS:

**PROJECT 1 — LOCAL HOST**
This project will run on the client's Windows computer. It will communicate with:
* Microsoft Excel
* Local TallyPrime installation
* Local SQLite database
* The BRMCo Server Host through HTTPS in future phases

The Local Host must run as a local web application/service and be accessed through a browser, for example `http://127.0.0.1:8000`.
The Local Host is responsible for all operations that require access to the user's computer or locally installed TallyPrime.

**PROJECT 2 — SERVER HOST**
This project will run on my remote server/cloud server. It will expose REST APIs and will eventually handle:
* User authentication
* Client authentication
* API keys
* AI APIs
* MongoDB/database
* Central configuration
* Subscription/licensing logic
* Cloud processing
* Other future services

For Phase 1, keep the Server Host deliberately lightweight. It should primarily establish the correct server architecture and API contract so that future features can be added without redesigning the Local Host.

## 2. ARCHITECTURE
Use the following architecture:

```text
                    BRMCo ACCOUNTING HUB
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
       LOCAL HOST PROJECT           SERVER HOST PROJECT
       Client Computer             Remote Server
       ┌──────┼────────┐          ┌───────┼────────┐
      Excel  Tally   SQLite      REST    Future   Future
              │                  API     AI       MongoDB
              ▼
          TallyPrime
```

More specifically:

```text
CLIENT COMPUTER
Browser
   ▼
BRMCo Local Host  http://127.0.0.1:8000
   ├── Web UI
   ├── Excel Engine
   ├── Validation Engine
   ├── Accounting Engine
   ├── Tally Connector
   ├── XML Generator
   ├── Import History
   └── SQLite Database
            ▼
        TallyPrime (localhost)

                    HTTPS
BRMCo Local Host ───────────────────► BRMCo Server Host
                                      ├── REST API
                                      ├── Authentication (future)
                                      ├── AI APIs (future)
                                      ├── MongoDB (future)
                                      └── Central Services (future)
```

The Server Host must never attempt to directly access TallyPrime installed on the client's computer. TallyPrime remains local.

## 3. TECHNOLOGY STACK
Use Python.

**Local Host.** Recommended stack: Python 3.x, FastAPI, Uvicorn, HTML/CSS/JavaScript for the web interface, openpyxl for Excel processing, lxml or Python XML libraries for Tally XML, requests/httpx for HTTP communication, SQLite for the local database, and Pydantic for data validation.
Do NOT use PyInstaller. Do NOT create an EXE. The application should be runnable from source code using a command such as `uvicorn app.main:app --host 127.0.0.1 --port 8000`.

**Server Host.** Use Python 3.x, FastAPI, Uvicorn, Pydantic, an HTTP client such as httpx, and a database layer designed so MongoDB can be added later. Do not make MongoDB mandatory for Phase 1 unless genuinely required. The Server Host should be capable of running independently from the Local Host. Development example: `uvicorn app.main:app --host 0.0.0.0 --port 8001`. Production deployment should later support HTTPS and a proper domain.

## 4. PHASE 1 SCOPE
Phase 1 is ONLY the Accounting Entry Engine. Implement these four voucher categories:
1. Sales Voucher
2. Purchase Voucher
3. Journal Voucher
4. Bank Entries (Receipt, Payment)

Do not implement AI invoice extraction, GSTR-1 JSON generation, OCR, advanced reporting or subscription/payment systems in Phase 1. The architecture should, however, be modular enough that these features can be added later.

## 5. PRIMARY USER WORKFLOW
Select Voucher Type → Generate Structured Excel Template → User fills Excel → Upload Excel → Validate Excel → Display Errors / Warnings → Preview Accounting Entries → Generate Tally XML → Send XML to Local TallyPrime → Receive Tally Response → Show Success / Failure → Save Import History.
Also provide an option "Download Tally XML". This is important for testing and troubleshooting even when direct posting to Tally is available.

## 6. LOCAL HOST — MAIN MODULES
Dashboard showing: Sales, Purchase, Journal, Bank Receipt, Bank Payment, Tally Connection, Import History, Settings.

## 7. COMPANY AND TALLY CONFIGURATION
Allow the user to configure: Company Name, Financial Year, Tally Company Name, Tally Server/Host, Tally Port and Server Host URL. The default Tally connection can be `http://127.0.0.1:9000`, but the port must be configurable. Provide a "Test Tally Connection" button. Clearly display Connected / Not Connected / Error message. Do not assume that Tally is always running.

## 8. TALLY MASTER DATA
Create a mechanism to retrieve/cache Tally masters: Ledgers, Groups, Stock Items, Units and Voucher Types. Maintain a local cache.
Excel → Validation → Does the ledger/item exist in Tally? Yes → continue; No → show a validation error.
Do not silently create incorrect ledgers or items. Design the module so master synchronization can be expanded later.

## 9. SALES EXCEL TEMPLATE
Columns: Voucher Date, Invoice Number, Customer Ledger, Customer GSTIN, Customer State, Place of Supply, Reverse Charge, Sales Ledger, Item/Description, HSN/SAC, Quantity, Unit, Rate, Discount, Taxable Value, CGST Rate, CGST Amount, SGST Rate, SGST Amount, IGST Rate, IGST Amount, Cess Rate, Cess Amount, Round Off, Invoice Total, Narration. Include useful validation/dropdowns wherever practical.

## 10. PURCHASE EXCEL TEMPLATE
Columns: Voucher Date, Supplier Ledger, Supplier GSTIN, Invoice Number, Invoice Date, Supplier State, Place of Supply, Reverse Charge, Purchase/Expense Ledger, Item/Description, HSN/SAC, Quantity, Unit, Rate, Discount, Taxable Value, CGST/SGST/IGST/Cess Rates and Amounts, Round Off, Invoice Total, ITC Eligibility, Narration.

## 11. JOURNAL EXCEL TEMPLATE
Columns: Voucher Date, Reference Number, Ledger, Debit, Credit, Cost Centre, Narration. Total Debit must equal Total Credit, or the entry must not be posted.

## 12. BANK RECEIPT TEMPLATE
Columns: Voucher Date, Bank Ledger, Party Ledger, Amount, Instrument/UTR, Instrument Date, Reference Number, Narration. Logic: Bank A/c Dr, To Party A/c.

## 13. BANK PAYMENT TEMPLATE
Same columns, with Party/Expense Ledger. Logic: Party/Expense A/c Dr, To Bank A/c.

## 14. EXCEL VALIDATION ENGINE
- **File validation:** correct template, correct template version, required columns present, valid Excel format.
- **Date validation:** valid date, within the financial year.
- **Ledger validation:** the ledger exists in the cached Tally masters.
- **GST validation:** GSTIN format, CGST/SGST/IGST consistency, tax calculation, place of supply, taxable value, invoice total.
- **Journal validation:** Debit = Credit.
- **Duplicate validation:** voucher number, invoice number, date, ledger.
- **Numeric validation:** no invalid numbers, negative quantities, invalid tax rates or incorrect totals.

Return structured errors such as: Row 7, Column: Customer Ledger, Error: Ledger "ABC Traders" does not exist in Tally master data.

## 15. PREVIEW SCREEN
After successful validation, do NOT immediately post to Tally. Show a preview: Voucher Type, Voucher No, Date, Customer, Taxable Value, CGST, SGST, Invoice Total. Provide "Confirm & Post to Tally" and "Download XML" buttons.

## 16. TALLY XML ENGINE
Excel → Accounting Object → Validation → Tally Adapter → Tally XML → TallyPrime. Do not mix Excel parsing logic with XML-generation logic. Create separate modules/classes for Sales, Purchase, Journal, Receipt and Payment XML. The XML generator must be modular because Tally XML structures may evolve.

## 17. TALLY RESPONSE HANDLING
Capture and parse the response and display Created, Altered, Ignored, Errors and the response message. Never show "Success" merely because the HTTP request succeeded. Success must be based on the actual Tally response.

## 18. IMPORT HISTORY
SQLite storing: date/time, user/company, financial year, voucher type, voucher number, Excel file name, XML file name, number of records, Tally status, Tally response and error details. Provide a searchable, filterable Import History screen.

## 19. AUDIT LOG
Log: Excel uploaded, validation performed, validation failed, XML generated, XML downloaded, Tally posting attempted, Tally posting successful, Tally posting failed.

## 20. SERVER HOST — PHASE 1
No accounting engine yet. A clean FastAPI backend with `GET /health` and `GET /version` (`{"status":"ok","application":"BRMCo Accounting Hub Server","version":"1.0.0"}`) and minimal future placeholders for `/auth`, `/ai`, `/users`, `/clients` and `/settings`.

## 21. LOCAL HOST ↔ SERVER HOST CONTRACT
A configurable `SERVER_BASE_URL`, and a small server-client module that calls `/health` and `/version`. The Local Host must NOT contain AI API keys, MongoDB passwords, server database credentials or any other secret provider credentials.

## 22. SECURITY PRINCIPLE
Local Host → (HTTPS) → Server Host → AI Provider / MongoDB / other APIs. Never Local Host → AI Provider directly.

## 23. DATABASE ARCHITECTURE
SQLite locally for import history, audit logs, local configuration, cached Tally masters and application metadata. Do NOT use SQLite to replace Tally accounting data; Tally remains the system of record. Use a repository/service architecture on the server so MongoDB can be introduced later.

## 24. PROJECT STRUCTURE
*(A detailed folder tree for `brmco-accounting-local` and `brmco-accounting-server` was specified, covering the api, accounting, excel, tally, database, server_client, config, frontend, templates and tests folders.)*

## 25. CONFIGURATION
Use environment variables and a `.env.example`. No real secrets in source code.

## 26. USER INTERFACE
A professional but simple CA-office interface with navigation for Dashboard; Accounting (Sales, Purchase, Journal, Bank Receipt, Bank Payment); Tally (Connection, Master Sync); Import History; and Settings.

## 27. ERROR HANDLING
Never crash on ordinary user input errors. Handle invalid Excel, missing columns, invalid dates, invalid ledgers, invalid GSTINs, Tally not running, connection failures, invalid Tally responses, duplicate vouchers, invalid accounting entries and an unavailable server.

## 28. LOGGING
Log startup, Excel processing, validation, XML generation, Tally communication, server communication and exceptions. Never log secrets.

## 29. TESTING
Tests for accounting calculations, Excel handling (valid template, missing column, invalid value, invalid date, duplicate entry), Tally (XML generation, response parsing, connection failure) and the server (`/health`, `/version`).

## 30. DEMO MODE
Excel → Validation → Preview → XML Generation → Simulated Tally Response, clearly marked "DEMO MODE — No entry posted to Tally".

## 31. IMPORTANT DESIGN PRINCIPLE
INPUT → ACCOUNTING MODEL → VALIDATION → TALLY ADAPTER → TALLY.

## 32–33. FUTURE PHASES
Better master sync; GST and GSTR-1 JSON; AI invoice extraction and OCR; server authentication, MongoDB and multi-client support; AI-assisted accounting. AI invoice processing should flow Local Host → Server → AI → Server → Local Host → Human Review → Tally.

## 34. DELIVERABLES
Complete source code for both projects, with requirements.txt, README.md and .env.example for each, sample Excel templates, sample Tally XML, tests, setup and run instructions, an architecture explanation and API documentation.

## 35. DO NOT DO THESE THINGS
❌ No EXE ❌ No PyInstaller ❌ Don't combine the two projects ❌ No server secrets, AI keys or MongoDB credentials in the Local Host ❌ The Server Host must not connect to TallyPrime ❌ No AI extraction or GSTR-1 JSON in Phase 1 ❌ Don't replace Tally with the app database ❌ Never auto-post an unvalidated Excel file.

## 36. DEVELOPMENT APPROACH
Build incrementally: dashboard → Sales template, upload, validation and preview → Tally XML, connection and posting → Purchase, Journal and Bank → history, audit and master sync → Local ↔ Server link. At every stage, keep existing functionality working.

## 37. FINAL REQUIREMENT
Before writing code, first provide: overall architecture, Local Host responsibilities, Server Host responsibilities, folder structure, data flow, the API contract, database design, the Tally integration approach and the development sequence. Then generate the source code for both projects.
The priority for Phase 1 is: reliable accounting entry → validation → Tally XML → TallyPrime posting.
