# Master prompt: Cash Flow Forecast app

The specification prompt given to Claude Code (Opus) at the start of the project, unchanged.
It set the role, constraints, inputs, forecast rules, screens, export, security, AI layer,
build order (9 phases), acceptance tests and deliverables.

```text
ROLE
You are a senior Python developer and finance-systems analyst. Build the app below phase by phase. After each phase, show what was built and how I can check it, then wait for my review.

OBJECTIVE
Build a local web app that replaces a manual daily Excel cash flow review for a company finance team. It generates a working capital cash flow forecast in 10-day lots, lets users amend it on screen, and exports Excel with live formulas. The layout follows the sample sheet I will attach: three lot columns, category rows, PDC detail, bill discount detail, closing, ERP tie-out and funding position.

HARD CONSTRAINTS
1. Python 3.11+, FastAPI with Uvicorn, SQLite through SQLAlchemy, Jinja2, HTMX, Alpine.js and Bootstrap. Serve all assets locally, with no CDN.
2. Free, open-source libraries only. No paid API and no cloud service. The app must run offline on one PC or an intranet server.
3. Currency is OMR with 3 decimals. Support three OMR bank accounts. Other-currency accounts are allowed with a manually entered exchange rate. Forecast OMR flows only.
4. Several users. Roles: Admin, Preparer, Viewer. Include an Approver role in the data model, switched off by a setting.
5. Use synthetic data only. Never put real company data in the repository.

INPUTS
1. Bank balances: manual entry per account, taken from the ERP bank ledger, with an as-of date.
2. Customer collections: ERP Excel with invoice no, customer, project, due date, outstanding amount.
3. Additional collections: template with project, expected date, amount, note.
4. Vendor PDCs: ERP Excel with voucher no, vendor, cheque no, cheque date, amount.
5. Vendor payment allocation: ERP Excel with vendor, invoice, planned date, amount.
6. Bill discount and LC: bank Excel with reference, bank, maturity date, amount. New discounting proceeds are an inflow category. A bill-discounted invoice can be flagged so it is not counted again as a collection.
7. Other and recurring categories: template with category, description, date, amount, inflow or outflow.
8. Bank facility: amount available per bank, entered manually.
Categories are never hard-coded. Accept an uploaded category list with name, inflow or outflow, summary group, display order and default fixed or deferrable. Read the category from the column header, or from a Category column. Send unmatched headers to an exceptions screen with a rapidfuzz suggestion, so the user can map them or add a new category.

FORECAST RULES
- Lots: days 1-10, 11-20, 21 to month-end. Lot length and horizon are settings. Lots before the as-of date are locked actuals.
- The current lot opens with the total of the ERP bank balances, other currencies converted at the manual rate. Each later lot opens with the previous lot's closing.
- Place each line item in the lot of its planned date. Unpaid items dated before the as-of date go in the current lot.
- Closing = opening + inflows - outflows. Funding position = closing + bank facility available. A negative funding position is the gap.
- Hold removes an item from every lot and lists it in a hold register shown as a memo, not added back. Defer moves it to a chosen later lot. Re-date, reduce and exclude are also allowed.
- A scenario toggle excludes the collections flagged as risk-adjusted.
- Store line items exactly as imported. Keep every user change in an overrides table keyed by voucher or invoice number, so a daily re-upload keeps them.
- Compare the model's closing with the ERP bank balance and show the difference.
- Save a snapshot of the grid each day. Log every change in an audit table.

SCREENS
Login; balances and facility; uploads with exceptions screen; lot grid with hold, defer, re-date and toggles that recalculate at once; scenarios; hold register; export; user and category admin.

EXPORT
Write Excel with XlsxWriter: a Forecast sheet in the sample layout, a Data sheet of line items, a Settings sheet (lot dates, balances, rates, facility) and a Hold register sheet. All totals, closing balances and gaps are live formulas, and category rows use SUMIFS over the Data sheet. After export, recalculate with headless LibreOffice and compare with the engine. Block the export on any difference.

SECURITY
Argon2 password hashing, signed sessions, HTTPS on the network, upload checks (.xlsx and .csv only, size limit, no macros), file hash log, no secrets in code, encrypted backups, no outbound network calls.

AI LAYER (free, local, advisory only)
rapidfuzz for header and category matching. scikit-learn for collection delay when payment history exists, falling back to the due date. pandas rules for duplicates and overlaps between the PDC, allocation and bill discount lists. Template-based commentary for each lot. The forecast engine itself stays rule-based.

BUILD ORDER
1 Project structure and settings. 2 Database models. 3 Input templates and synthetic data. 4 Import and validation. 5 Forecast engine with tests. 6 HTML screens. 7 Excel export and formula check. 8 Users, roles and audit. 9 Tests, README and user manual.

ACCEPTANCE TESTS
- A synthetic month with about 70 PDCs reproduces the lot totals worked out by hand.
- Holding a PDC raises the closing balance of its lot and every later lot by exactly its amount.
- Deferring moves the amount to the chosen lot with no loss.
- Re-uploading the same files keeps all overrides.
- The exported workbook recalculates to the same figures as the screen.
- A new category in an Excel header appears in the report after mapping.

DELIVERABLES
Source code, requirements.txt, README with setup steps, input templates, synthetic data, tests and a short user manual.
```
