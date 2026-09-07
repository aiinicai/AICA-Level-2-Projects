# GST IMS Reconciliation Tool

**Bridging GST Reconciliation with Munim IMS Portal Submission**

AICA Level 2 — Capstone Project Submission

Prepared by **CA Ravi Maan**
AICA | L2 | Batch 85

IJR & Co., Chartered Accountants | Panchkula, Haryana
The Institute of Chartered Accountants of India

---

## 01 | The Problem We Faced

Every month, after completing GSTR-2B vs Books reconciliation, our team had to manually copy matched invoice data row by row into the Munim GST software template — to push it to the IMS Portal. This was slow, repetitive, and error-prone.

**1. Manual & Time-Consuming**
Copy-pasting hundreds of invoice rows one by one from the reconciliation sheet to the Munim template every single month.

**2. Risk of Data Entry Errors**
Invoice numbers, dates, taxable values — any typo could lead to ITC mismatches, rejected invoices, or notices from the department.

**3. No Document-Type Split**
Invoices go to the b2b sheet; Credit Notes go to cdnr — these had to be manually identified and separated every month before entry.

**4. Cross-Month Invoice Misses**
Invoices from April/May sometimes matched in July. Since filtering was by the Month column, these were being silently missed every time.

---

## 02 | Understanding the GST IMS Portal

### Invoice Management System (IMS) — Introduced by GSTN

The IMS Portal lets GST-registered businesses review every inward supply invoice that appears in their GSTR-2B and take action on it — Accept, Reject, or keep Pending. Accepted invoices are auto-carried into GSTR-3B for ITC claim. This makes monthly IMS action a critical compliance step that directly affects cash flow.

| Status | Effect |
|--------|--------|
| **Accepted** | ITC auto-populated to GSTR-3B |
| **Rejected** | Supplier must amend the invoice |
| **Pending** | Deferred to the next period |
| **Deemed Accepted** | Auto-accepted by GSTN system |

### Why We Cannot Directly Access the IMS API

IMS actions must be submitted via a GST-licensed software using its own API key — a custom tool cannot connect to the GSTN API directly without separate certification. Our tool solves this cleanly: it prepares a perfectly formatted Munim upload template, and Munim handles all API communication with GSTN. No overlap, no compliance risk.

---

## 03 | AICA Level 1 — The Foundation This Tool Builds On

AICA Level 1 equipped CA Ravi Maan with the skills to build a fully functional Excel-macro based reconciliation tool — already in active monthly use at IJR & Co.

### AICA Level 1 Built

- Excel Macro-based GSTR-2B vs Books ITC Reconciliation Tool
- Automatically posts remarks such as "Matched in April", "Nil in 2B", "Not in Books", "Not Considered Pending"
- Processes IGST, CGST, SGST amounts at invoice-line level
- Output: Structured sheet — "2B vs Books ITC Reconciliation" — reviewed and signed off monthly
- Already deployed and used for every monthly GST cycle at IJR & Co.

### AICA Level 2 — This Tool

- Takes the Level 1 output as its primary input file — no re-entry of data
- Filters records using the Remarks column, data source (2B), and document type
- Correctly picks up cross-month invoices (April invoice matched in July)
- Splits output: Invoices → b2b sheet, Credit Notes → cdnr sheet
- Exports a timestamped Munim-ready .xlsx — ready to upload, no further editing needed

---

## 04 | Objective — What We Wanted to Build

### Objective 01: Auto-Extract Matched Invoices from the Reconciliation Sheet

Read the 2B vs Books recon file and filter rows where: Data From = '2B' AND Remarks = 'Matched in [selected month]' — crucially, by the remark month, not the invoice period column, so cross-month invoices are never missed. Also pick up 'Nil in 2B' rows for the relevant month.

### Objective 02: Split by Document Type and Assign Required Fields Automatically

Route Invoices → b2b sheet and Credit Notes → cdnr sheet without any manual sorting. Auto-assign GST Rate as 18% (where any tax exists) or 0% (where all taxes are nil), and convert state names to Munim Place of Supply codes — all mandatory fields Munim validates on upload.

### Objective 03: Produce a Clean Munim Upload Template — No Manual Work for the Team

Write all extracted and mapped data into a copy of the Munim GSTR-2 import template (.xlsx), in the exact column order Munim expects. Save with a timestamp. Any team member can take the file and upload it through Munim — no editing, no data entry, no possibility of error.

---

## 05 | End-to-End Workflow

```
Step 1            Step 2            Step 3            Step 4            Step 5            Step 6
2B vs Books  →   Python Tool   →   Munim         →   Munim         →   IMS           →   IMS Recon
Recon Sheet       (Level 2)        Template          Software          Portal            (2nd Level)
Level 1 Output    Filter,          b2b + cdnr        API push          Invoices          Verify
                  Split & Map      filled            to GSTN           Accepted          & Audit
```

### Why Munim handles the IMS API — not our tool

Munim (our GST software) holds a licensed API key for GSTN IMS communication. Replicating this in a custom tool would require separate software certification and GSTN approval — not practical or necessary. Our tool prepares the data in the exact format Munim expects; Munim handles the actual regulatory submission. This is the correct and practical separation of responsibility.

---

## 06 | Step-by-Step: How We Built the Tool

**Step 1: Analysed the Reconciliation Sheet**
Examined the 2B vs Books ITC Recon file: header row position (row 6), all column names, exact values in the Remarks column, date formats, and how Data From distinguishes 2B from Books entries.

**Step 2: Designed the Correct Filter Logic**
Defined three filters: (a) Data From = '2B', (b) Remark = 'Matched in [Month]' — using the remark text, not the Month column, to capture cross-month invoices — and (c) Document Type split for Invoice vs Credit Note.

**Step 3: Mapped Columns to Munim Template**
Matched each recon column to the exact Munim b2b and cdnr column positions. Handled GST Rate logic (18% if tax > 0, else 0%), Place of Supply name-to-code conversion, DD-MMM-YYYY date format, and abs() for credit note negative values.

**Step 4: Built the Python Tool with a GUI**
Coded the full solution in Python using pandas (filtering and data processing), openpyxl (reading Munim template and writing data), and tkinter (the user-friendly GUI with file browsers, month dropdown, and run button).

**Step 5: Created a BAT File for One-Click Use**
A Windows Batch (.bat) file auto-installs required Python packages on first run and launches the GUI tool. Works on any Windows laptop with Python installed — team members need zero technical knowledge to run it.

**Step 6: Tested Against Real Client Data**
Ran the tool against April–July 2026 reconciliation data (377 2B rows across four months). Verified b2b/cdnr split, cross-month pickup (3 invoices), date formatting, Place of Supply mapping, and tax values.

---

## 07 | Tools Used to Build This Solution

| Tool | Purpose |
|------|---------|
| **Claude AI (Anthropic)** | The AI backbone. Used to design the architecture, write all Python code, debug logic, and iterate the tool in real-time based on feedback — compressing what would be days of solo development into a few focused hours. |
| **Python 3** | Core programming language. Handles all data processing, filtering logic, column mapping, and Excel file generation. Runs 100% offline — no internet, no cloud, no data ever leaves the laptop. |
| **pandas** | Reads and filters the 2B vs Books reconciliation Excel file with precision. Handles auto-detection of header rows, data type normalization, and the multi-condition filtering logic at the heart of the tool. |
| **openpyxl** | Writes data into the Munim template while preserving all existing formatting, formula rows, and sheet structure. Handles date formatting, font application, and template-safe cell-by-cell writing. |
| **tkinter (GUI)** | Provides the user-friendly GUI — file browse dialogs, month dropdown, output folder selector, step-by-step status bar, and the summary popup. No terminal. No coding. Any team member can use it independently. |
| **Windows BAT File** | A one-line launcher that auto-installs required packages on first run and opens the GUI. Works on any Windows machine with Python installed. Eliminates all setup friction for non-developer users. |

---

## 08 | The Bridge — How the Tool Connects the Entire Workflow

The tool sits precisely between the reconciliation output and the Munim submission — transforming data so the team never has to touch it manually.

### INPUT
- 2B vs Books ITC Reconciliation sheet (Level 1 output)
- User selects the return period month
- Tool reads: Data From, Remarks, Document Type columns
- 377 source rows spanning Apr–Jul 2026

### THIS TOOL DOES
- Filters: 2B data + remark matches selected month
- Captures cross-month invoices via remark logic
- Splits: Invoice → b2b, Credit Note → cdnr
- Maps GST rate, POS codes, date format
- Writes to a timestamped copy of Munim template

### OUTPUT
- Munim-ready .xlsx with b2b and cdnr sheets filled
- Team uploads to Munim — no editing needed
- Munim API pushes to IMS Portal (GSTN)
- Invoices show as Accepted on IMS
- Original template is never modified

---

## 09 | 2nd Level — IMS Acceptance Reconciliation

After Munim pushes data to IMS, a second Python tool verifies every acceptance — closing the compliance loop completely.

**Step 1:** Our Matched Invoice List → Extracted via this tool
**Step 2:** Munim Pushes to IMS → Via licensed API key
**Step 3:** IMS Status Report → GST Portal / Munim export
**Step 4:** IMS Recon Tool → Python: compare & flag

### Reconciliation Outcomes

| Outcome | Meaning |
|---------|---------|
| **Confirmed Accepted** | Matched + Accepted on IMS — ITC can be claimed |
| **Pending on IMS** | Pushed but not actioned — follow up needed |
| **Rejected on IMS** | Needs investigation or supplier amendment |
| **Not Found on IMS** | In our list but absent from IMS — check Munim upload status |

This gives IJR & Co. a complete audit trail — matched, pushed, accepted, and verified — for every invoice in every return period.

---

## 10 | Key Features of the Tool

**1. Cross-Month Invoice Pickup**
Filters by the remark text (not the Month column) — so a 'Matched in July' remark on an April invoice gets picked up correctly when July is selected.

**2. Automatic Document-Type Split**
Invoices are written to the b2b sheet; Credit Notes to the cdnr sheet — zero manual sorting. Document Type is read directly from the source data.

**3. Smart GST Rate Assignment**
18% where IGST/CGST/SGST total is non-zero; 0% where all taxes are nil. Satisfies Munim's mandatory rate field without any manual decision-making.

**4. Place of Supply Code Mapping**
Converts full state names (e.g. 'Jammu and Kashmir') to Munim's required code format ('01-Jammu & Kashmir'). Falls back to GSTIN prefix if name is unclear.

**5. Template-Safe — Originals Intact**
The tool always copies the Munim template before writing. Your original template is never modified. Each run produces a new timestamped file, preserving every version.

**6. No-Code GUI for the Entire Team**
Tkinter GUI lets any team member — regardless of technical background — browse files, pick a month, and click Run. No terminal, no scripts, no manual steps.

---

## 11 | Impact on IJR & Co. Operations

| Metric | Value |
|--------|-------|
| Invoices processed (Apr–Jul 2026) | **335** |
| Time per month | **< 2 minutes** (vs hours of manual entry) |
| Manual data-entry errors possible | **Zero** |
| Team members who can run this independently | **6** |

### Before This Tool

- ✗ Copy-paste each invoice row from the recon sheet
- ✗ Manually identify invoices vs credit notes
- ✗ Risk of GSTIN/date/value copy errors
- ✗ Cross-month invoices frequently missed
- ✗ Senior team member spent hours each month

### After This Tool

- ✓ Select month and click Run — done in seconds
- ✓ Automatic split: b2b and cdnr, zero sorting
- ✓ All values read directly from source — no manual touch
- ✓ Cross-month invoices captured correctly via remark filter
- ✓ Any team member can run it independently

---

## 12 | Future Roadmap

**01 — Standalone EXE Distribution** `Planned`
Convert the Python tool to a .exe using PyInstaller — runs on any Windows computer without Python installed. Double-click, no setup, no dependencies. Distributable across the firm and to clients.

**02 — IMS Acceptance Reconciliation Tool** `Planned`
Build the 2nd-level reconciliation module: compare our Matched invoice list against the IMS Portal status report to verify every accepted invoice and automatically flag Pending, Rejected, or Missing ones.

**03 — Multi-Client Batch Processing** `Concept`
Tag records by client GSTIN and generate separate Munim templates per client in one run — enabling the tool to serve all of IJR & Co.'s GST clients without running the process separately for each.

**04 — Auto Return Period Population** `Concept`
Auto-detect and populate the Return Period column in the Munim template based on the selected month and financial year — removing the last remaining manual field in the upload template.

---

## Conclusion

### From Manual Entry to Intelligent Automation

- AICA Level 1 built the foundation — the Excel-macro GSTR-2B vs Books ITC Reconciliation tool, already running monthly at IJR & Co.

- AICA Level 2 extended that foundation into a Python-powered automation tool that extracts, transforms, and prepares data for Munim IMS submission — eliminating all manual steps.

- The tool is a practical bridge: it removes every manual step between reconciliation and Munim upload, saving significant time, eliminating data-entry risk, and empowering the entire team.

- It demonstrates how AI (Claude), programming (Python), and CA domain expertise combine to solve a real GST compliance challenge — without touching any regulated API or requiring any technical background from the user.

---

Prepared by **CA Ravi Maan**
AICA | L2 | Batch 85

IJR & Co., Chartered Accountants | Panchkula, Haryana
