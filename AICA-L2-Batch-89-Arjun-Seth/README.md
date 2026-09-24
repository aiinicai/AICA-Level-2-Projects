# LeaseIQ Pro

**AI-Powered Lease Accounting Tool - From Contract to Compliance, instantly!**

AICA Level 2 Capstone Project | Batch 89 | Arjun Seth

> This is a **training / capstone tool**. Its output is a working aid for a qualified accountant and is not a substitute for
> professional accounting, audit or legal judgement.

---

## 1. Purpose

Lease accounting under **Ind AS 116** and **ASC 842** is calculation-heavy: the terms are buried in long contracts, the present
values and schedules are usually built in spreadsheets, and a reviewer cannot easily see how a number was produced. One
60-month lease produces about 120 schedule rows and about 790 journal lines across the two standards.

LeaseIQ Pro takes a lease **from contract to compliance**:

1. an AI model reads the agreement and *proposes* the key terms;
2. a person **validates every field** (nothing is calculated before this);
3. a tested, plain-Python calculation engine works out the lease liability, the right-of-use asset, the classification, the
   schedules and the journal entries for **both standards** from the same validated input;
4. the lease is reviewed and approved, and disclosures and reports are produced.

**Design rule:** the AI reads and drafts; it never calculates. All arithmetic is done by a deterministic engine.

## 2. Main features

- **Three ways to add a lease:** upload a lease agreement (text-based PDF or Word) for AI extraction, upload a bulk Excel file, or
  enter a contract manually. All three use the same checks and the same engine.
- **Validation screen:** every extracted field is shown for confirmation; the AI's suggestion and the validated value are stored
  separately, so the audit trail shows what the AI said and what was approved.
- **Classification:** the five ASC 842 tests (with the computed value of each) and the Ind AS 116 treatment, including the
  short-term and low-value exemptions. The ASC 842 result can be overridden, with a visible warning.
- **Dual-framework results:** initial measurement, lease liability and right-of-use asset, amortisation schedules, and Day 1 and
  monthly journal entries (debits always equal credits) for Ind AS 116 and ASC 842.
- **Disclosures and AI technical memo:** disclosure notes, and a technical memo drafted from validated figures only, with a check
  that every amount in the memo appears in the results. A template memo works with no AI at all.
- **Workflow and control:** Draft, Pending Review, Approved; reject with a reason and correct; bulk approval; a full audit log; an
  Admin-only delete that keeps the lease's audit history.
- **Dashboard:** total leases, total lease liability, net right-of-use asset, monthly lease expense, status and classification
  charts, maturity profile, interest-versus-principal chart, and a future-payments view. One currency at a time - amounts in
  different currencies are never added together.
- **Reports:** a full disclosure report (portfolio summary, lease register, maturity analysis, lease liability and right-of-use
  movements, lease costs, consolidated technical memo, self-checking reconciliation checks) for Ind AS 116 or ASC 842, as **PDF,
  Word or Excel**. Each lease also exports its schedules and journal entries to Excel or CSV.
- **Display:** Indian (5,00,000) or international (5,000,000) number format, 36 currencies, three dashboard layouts in light and
  dark themes.

## 3. How to run it

**You need:** Python 3.10 or newer (developed on Python 3.14). Works on Windows, macOS and Linux.

**Windows (Command Prompt or PowerShell), from this folder:**

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

**macOS / Linux:**

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The application opens in your browser (normally http://localhost:8501) **directly on the Dashboard. There is no sign-in.**
If Streamlit asks for an email address the first time, just press Enter.

The local database file `leaseiq.db` is created automatically on the first run. To start again from a clean slate, stop the
app and delete that file.

### Optional: the AI reading of a lease document

Everything works **without any key** except the AI reading of an uploaded PDF or Word agreement, which shows a clear message if
no key is set. Manual entry, bulk upload, all calculations, results, journal entries, approvals, reports and exports need no key.

To try the AI extraction with your own free key:

1. Create a free key at https://aistudio.google.com/apikey
2. Copy `.env.example` to `.env` (`copy .env.example .env` on Windows, `cp .env.example .env` elsewhere).
3. Put your key in `.env` after `AI_API_KEY=`, then restart the app.

No key is included in this submission. The free tier sends the document text to Google's AI service, so please use only the
fictional sample lease provided.

## 4. Try it (about 5 minutes)

Sample files are in `samples/` (all fictional):

| File | Use |
|---|---|
| `sample_lease.pdf`, `sample_lease.docx` | The same fictional lease, for the AI extraction (needs a key). |
| `sample_bulk_upload.xlsx` | Five leases for **Bulk Upload**: three import and two are deliberately faulty (a discount-rate problem and an invalid date), to show the validation. |

Suggested path:

1. **Bulk Upload** the sample workbook, or use **Leases > Add contract manually**.
2. Open a lease from **Leases** and **Review and validate** it, then confirm. This is the control point.
3. On the **Results** screen, see the classification (the five-test table), the **Schedules** and **Journal entries** tabs, the
   **Disclosures** and **Technical memo** tabs, and the **Export** tab.
4. Open **Approvals** to approve it, and **Audit Log** to see who did what.
5. Open the **Dashboard** for the portfolio view and **Reports** to generate an Ind AS 116 or ASC 842 disclosure report.

## 5. Accuracy: how the numbers were verified

Before the application was written, the whole calculation was built as an independent Excel proof of concept. The engine was then
verified **cell by cell** against it. For the illustrative lease below, the two agree exactly:

| Measure | Excel proof of concept | LeaseIQ Pro |
|---|---|---|
| Lease liability at commencement | Rs 50,79,693.73 | Rs 50,79,693.73 |
| Right-of-use asset at commencement | Rs 55,88,083.82 | Rs 55,88,083.82 |
| Straight-line lease cost per month | Rs 1,15,652.46 | Rs 1,15,652.46 |

*Illustrative lease:* rent Rs 1,00,000 a month, 5% yearly escalation, 60 months from 1 May 2026, 9% borrowing rate, 2 months paid in
advance (Rs 2,00,000), deposit Rs 3,00,000, initial direct costs Rs 1,50,000, restoration Rs 50,000, asset fair value
Rs 1,00,00,000, economic life 480 months. **To reproduce it:** bulk-upload `samples/sample_bulk_upload.xlsx`; the first lease
(Alpha Traders) is this lease.

The generated disclosure reports also re-check themselves (for example, undiscounted payments less future interest must equal the
lease liability), and any check that fails is shown, never hidden. The automated test suite that guards these figures is kept in
the private development repository.

## 6. How it is built

```
app.py             entry point: opens straight on the Dashboard
auth_ui.py         page guard (built-in Evaluator profile) and message helpers
ui_theme.py        theme, navigation and footer shared by every page
theme_css.py       the look of the three layouts in light and dark
lease_ui.py        lease screens: validation, manual entry, results, export
dashboard_views.py dashboard cards and charts
pages/             the screens: Dashboard, Leases, Bulk Upload, Approvals,
                   Audit Log, Settings, Reports, Future Roadmap
core/              business logic - no screen code in here
  calculation_engine.py  present values, schedules, initial measurement
  classification.py      ASC 842 five tests; Ind AS 116 treatment and exemptions
  journal_entries.py     Day 1 and monthly journal entries
  extraction.py          the AI reading of a lease document (with fallbacks and timeouts)
  validation.py, bulk.py checks for a lease form and for a bulk file
  disclosures.py, memo_generator.py, reports.py   disclosures, technical memo, reports
  workflow.py, permissions.py   approvals, audit log, access rights, database access
  report_*.py, dashboard_*.py, lease_export.py    PDF, Word and Excel output
db/                database models and setup (SQLite through SQLAlchemy)
samples/           fictional sample files
```

**Architecture in one line:** screens, then a workflow layer (approvals, audit log, rights), then a pure-Python engine, then a
database. The AI sits at the edge: it proposes field values from contract text and drafts a memo from already-validated figures.

## 7. About this edition

This is the **evaluation edition**. It opens directly with no sign-in, running as a built-in "Evaluator" profile that can use every
feature. The full build additionally has user IDs and passwords, an Admin who creates users, and five access levels (View only,
Editor, Approver, Editor and Approver, Admin), with rights checked on every action. Those user-administration screens are not
part of this edition.

## 8. Limitations and future roadmap

The AI reading works on clean, text-based PDF and Word files (no OCR for scans yet). Planned or deferred, and **not** in this
build: OCR for scanned agreements; multi-currency FX translation; a side-by-side Ind AS 116 versus ASC 842 comparison mode; lease
amendments with version history; ERP posting (SAP, Oracle, Tally); and a production stack (React, FastAPI, PostgreSQL).

## 9. Copyright and licence

**Copyright © 2026 Arjun Seth. All rights reserved.**

Viewable for ICAI evaluation only. No permission to copy, modify, redistribute or use commercially without written permission.

See the `LICENSE` file for the full notice. The notice is repeated at the top of every source file, and the copyright line is shown in the application footer.
