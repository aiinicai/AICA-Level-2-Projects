# GST IMS Reconciliation Tool

**Bridging GST Reconciliation with Munim IMS Portal Submission**

> AICA Level 2 — Capstone Project
> Prepared by **CA Ravi Maan** | AICA | L2 | Batch 85
> IJR & Co., Chartered Accountants | Panchkula, Haryana

---

## What This Tool Does

After completing GSTR-2B vs Books ITC reconciliation (built in AICA Level 1 using Excel macros), our team had to **manually copy-paste hundreds of matched invoice rows** into the Munim GST software template every month — to push them to the IMS Portal for acceptance. This was slow, repetitive, and error-prone.

This Python tool **automates the entire process**:

1. Reads the 2B vs Books ITC Reconciliation sheet (Level 1 output)
2. Filters matched invoices based on the selected return period month
3. Splits data by Document Type — **Invoices → b2b sheet**, **Credit Notes → cdnr sheet**
4. Maps all columns, GST rates, Place of Supply codes, and date formats
5. Writes everything into a **Munim-ready upload template** — no manual editing needed

The team uploads the output file to Munim, which uses its own licensed API key to push the data to the GST IMS Portal. **This tool never touches the GSTN API directly** — it acts purely as a data bridge.

---

## Key Features

- **Cross-Month Invoice Pickup** — Filters by the remark text (`Matched in July`), not the Month column, so invoices from earlier months matched later are never missed
- **Automatic Document-Type Split** — Invoices route to `b2b`, Credit Notes route to `cdnr` — zero manual sorting
- **Smart GST Rate Assignment** — 18% where tax exists, 0% where all taxes are nil
- **Place of Supply Code Mapping** — Converts state names to Munim's required `01-Jammu & Kashmir` format
- **Template-Safe** — Always writes to a timestamped copy; original template is never modified
- **No-Code GUI** — Any team member can browse files, pick a month, and click Run

---

## How to Run

### Option A: Python Script (requires Python installed)

1. Place `gst_2b_to_munim.py` and `GST_2B_to_Munim.bat` in the same folder
2. Double-click `GST_2B_to_Munim.bat` — it auto-installs dependencies and launches the GUI
3. Select your reconciliation file, Munim template, and month → click Run

### Option B: Standalone EXE (no Python needed)

1. Place `gst_2b_to_munim.py` and `BUILD_EXE.bat` in the same folder
2. Double-click `BUILD_EXE.bat` — it builds a standalone `.exe` using PyInstaller (one-time, ~3 min)
3. Copy the resulting `dist/GST_2B_to_Munim.exe` to any Windows computer
4. Double-click to run — no installation, no dependencies

---

## Tools & Technologies Used

| Tool | Role |
|------|------|
| **Claude AI** (Anthropic) | Architecture design, code generation, iterative debugging |
| **Python 3** | Core language — runs 100% offline, data never leaves the machine |
| **pandas** | Excel file reading, filtering, multi-condition data extraction |
| **openpyxl** | Template-preserving Excel writing with date/font formatting |
| **tkinter** | Built-in Python GUI — file browsers, dropdowns, status bar |
| **PyInstaller** | Bundles Python + all libraries into a single standalone `.exe` |
| **Windows BAT** | One-click launcher with auto-dependency installation |

---

## End-to-End Workflow

```
Level 1 Output          This Tool              Munim Software         GST Portal
┌──────────────┐    ┌─────────────────┐    ┌──────────────────┐    ┌────────────┐
│ 2B vs Books  │ →  │ Filter, Split   │ →  │ Upload template  │ →  │ Invoices   │
│ ITC Recon    │    │ & Map to Munim  │    │ API push to GSTN │    │ Accepted   │
│ Sheet        │    │ b2b + cdnr      │    │ (licensed key)   │    │ on IMS     │
└──────────────┘    └─────────────────┘    └──────────────────┘    └────────────┘
```

---

## AICA Level 1 → Level 2 Progression

| | Level 1 | Level 2 (This Project) |
|---|---------|----------------------|
| **What** | GSTR-2B vs Books ITC Reconciliation | 2B → Munim IMS Template Populator |
| **Built with** | Excel Macros | Python + Claude AI |
| **Output** | Reconciliation sheet with match remarks | Upload-ready Munim .xlsx (b2b + cdnr) |
| **Portability** | Works in Excel on one machine | Standalone .exe — runs on any Windows PC |
| **Status** | In production — used every month at IJR & Co. | In production — deployed for the same monthly cycle |

---

## Impact

| Metric | Before | After |
|--------|--------|-------|
| Time per month | Hours of manual copy-paste | < 2 minutes |
| Data entry errors | Risk of GSTIN/date/value typos | Zero — read directly from source |
| Cross-month misses | Frequent | Eliminated via remark-based filter |
| Who can run it | Senior team member only | Any of the 6 team members |

---

## Project Files

| File | Purpose |
|------|---------|
| `gst_2b_to_munim.py` | Main Python tool (GUI + processing logic) |
| `GST_2B_to_Munim.bat` | One-click launcher (auto-installs packages) |
| `BUILD_EXE.bat` | One-time script to build standalone .exe |
| `GST_IMS_Recon_AICA_L2.pptx` | Capstone presentation (14 slides) |
| `GST_IMS_Recon_AICA_L2.md` | Presentation content in Markdown |

---

## Author

**CA Ravi Maan**
AICA | L2 | Batch 85 | M No. 546270

IJR & Co., Chartered Accountants
SCO 323, Second Floor, Sector 9, Panchkula, Haryana
