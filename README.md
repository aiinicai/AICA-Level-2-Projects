# GS Stock Audit Tracker
### *Lead Partner: CA Gaurav Chaudhary*

An enterprise-grade, secure Python & Streamlit application tailored for **CA Gaurav Chaudhary** and the audit team to monitor, track, allocate, and manage Bank Stock Audit assignments in real-time.

---

## 🚀 1-Line Quick Installation Command

Run this single command in Windows Command Prompt (`cmd`) or PowerShell:

```bash
pip install streamlit pandas plotly openpyxl fpdf2 reportlab requests
```

---

## ⚡ How to Run the Application

### Option 1: 1-Click Launch (Double Click Batch File)
Double click **`Start_Application.bat`** in the folder.

### Option 2: Run in Python IDLE or Command Prompt
```bash
python run_app.py
# Audit Sampling & Fraud Detection Tool

An AICA Level 2 capstone project: a single-file Streamlit application that helps a
statutory auditor draw a defensible audit sample, run automated fraud red-flag
checks, and screen for manipulated figures using Benford's Law — then export the
results as an Excel workbook and a PDF summary.

This is a **training / capstone tool**, not a certified audit product. Every
finding it produces is a *screening signal* that still needs to be corroborated by
a qualified auditor before being relied upon in a real statutory audit.

---

## 1. How to run it

You only need Python 3.9+ installed. Nothing else.

**Option A — double-click (Windows):**
Double-click [`run.bat`](run.bat). A command window will open, install anything
missing on first run, and open the app in your browser.

**Option B — command line (any OS):**
```bash
python app.py
```
That's it. The script auto-installs every library it needs (only on the first
run — instant on every run after that) and launches the app in your browser.
No virtual environment, no manual `pip install`, no `streamlit run` needed.

### Option 3: Run with Streamlit
```bash
streamlit run app.py
```

---

## 🔐 Default Login Credentials

| Role | Username | Password | Full Name | Access Scope |
| :--- | :--- | :--- | :--- | :--- |
| **Partner (Admin)** | `partner` | `admin123` | **CA Gaurav Chaudhary (Partner)** | Full firm visibility, assignment creation, user management, export reports, reminders |
| **Team Member** | `priya` | `priya123` | Priya Verma (Audit Senior) | View assigned audits, update audit status & dates, upload working papers |
| **Team Member** | `amit` | `amit123` | Amit Gupta (Audit Executive) | View assigned audits, update audit status & dates, upload working papers |
| **Team Member** | `sneha` | `sneha123` | Sneha Patel (Semi-Qualified) | View assigned audits, update audit status & dates, upload working papers |
If you'd rather manage the environment yourself:
```bash
pip install -r requirements.txt
streamlit run app.py
```

**No file handy?** Click **"Use Built-in Sample Data"** inside the app — it
generates a realistic 500+ row synthetic transaction population with a handful of
deliberately planted anomalies, so every check has something genuine to catch. A
static copy of that same dataset is also bundled as
[`sample_data.csv`](sample_data.csv).

### Column names for your own file — no fixed format required

Your file's column headers **do not need to match ours**. Real exports (Tally,
SAP, QuickBooks, or a plain accounts spreadsheet) almost never do — one real
file used to test this feature had `Transaction_ID`, `Transaction_Date`,
`Approved_By`, `Department`, and no "raised by" column at all. After upload,
the app shows a **"Confirm column mapping"** panel that has already guessed
which of your columns corresponds to each field the tool understands (via a
large alias list — e.g. `Transaction_ID`/`Invoice_Number`/`Voucher No` are all
recognised as a voucher/ID column — with a fuzzy-text fallback for anything
that isn't a known alias). You just review/correct the guesses; nothing is
analysed until you've confirmed them.

Only four fields are strictly required for the tool to run at all:

| Field | Meaning |
|---|---|
| `Voucher_No` | Unique transaction/voucher/invoice reference |
| `Date` | Transaction date |
| `Vendor_Name` | Payee / vendor / supplier |
| `Amount` | Transaction amount (numeric) |

Three more are optional and simply unlock extra functionality when present —
if your file doesn't have them (or you leave them unmapped), the app doesn't
block you, it just quietly skips whatever depends on them:

| Field | Meaning | If missing |
|---|---|---|
| `Account_Head` | Ledger head / expense category / department | Display shows "N/A" instead |
| `Approver` | Person who approved the transaction | Segregation of Duties check is skipped |
| `Raised_By` | Person who raised/recorded the transaction | Segregation of Duties check is skipped |

If even one of the four required fields can't be mapped, the app tells you
exactly which one(s) before you can proceed.

---

## 2. What the tool does

The workflow follows five steps, shown in the sidebar so you always know where
you are: **Data → Sampling → Fraud Checks → Benford's Law → Reports.**

### Step 1 — Data
Upload a file or generate sample data. The file is validated (required columns
present) and cleaned (dates and amounts parsed; structurally unusable rows —
i.e. rows where the date or amount genuinely cannot be parsed — are dropped with
a count shown on screen). Unlike a first pass at this tool, **no row is ever
auto-deleted just because it looks like a duplicate of another row** — see
[§4 "Why duplicates are never auto-deleted"](#4-why-duplicates-are-never-auto-deleted) below.

### Step 2 — Audit Sampling (SA 530)
Four sampling methods, each with an on-screen explanation of when to use it:

- **Random Sampling** — every transaction has an equal chance of selection.
  Use for a homogeneous population with no known risk concentration.
- **Systematic Sampling** — pick every k-th transaction after a random start.
  Fast to execute by hand, but risky if the population has a hidden periodic
  pattern lining up with the interval.
- **Stratified Sampling** — split the population into value bands (strata)
  first, then sample within each band, so both small and large transactions are
  represented instead of a plain random sample being dominated by many small
  items.
- **Monetary Unit Sampling / MUS (PPS)** — a genuine implementation of the
  **Cumulative Monetary Amount** method (not a probability-weighted
  approximation labelled as MUS, which is a common shortcut). Every rupee in the
  population is treated as a sampling unit; evenly-spaced points are selected
  along the cumulative-amount number line, so a transaction's chance of
  selection is proportional to its rupee value. Any transaction whose own
  amount exceeds the sampling interval is a **"certain selection"** — it will
  always be picked regardless of the random start point — and the app tells you
  how many of those there were. This is the standard method when the audit
  objective is to detect material Rupee misstatement.

### Step 3 — Fraud / Red-Flag Detection (SA 240)
Six independently-selectable checks, each contributing to a combined
`Risk_Score` (= number of distinct checks a transaction triggered) with the
specific reasons shown per transaction:

| Check | What it looks for | Why it matters |
|---|---|---|
| **Duplicates** | Exact repeats of vendor + amount + date | Classic red flag for double payment or duplicate billing |
| **Threshold Dodging** | Amounts sitting just under an approval limit | Possible deliberate "structuring" to avoid a higher sign-off |
| **Round Numbers** | Suspiciously round amounts (e.g. exact multiples of ₹5,000) | Real invoices (rate × quantity + tax) are rarely exact round numbers |
| **Weekend Transactions** | Dated on a Saturday/Sunday | Outside the normal business cycle |
| **Segregation of Duties** | Same person both raised and approved the transaction | A broken control — the one person shouldn't be able to both create and authorise a payment unchecked |
| **Statistical Outliers** | Amounts unusually large/small vs. the rest of the population | Screens for amounts that don't fit the population's normal pattern |

**Outlier detection method** is selectable, and this matters more than it looks:

- **MAD (Median Absolute Deviation)** — *default, recommended.* Based on the
  median, not the mean.
- **IQR (Interquartile Range)** — also based on quartiles, not the mean.
- **Z-Score (classic)** — based on the mean and standard deviation. Kept for
  comparison/teaching purposes, **not the default.**

*Why not default to Z-Score?* Both the mean and the standard deviation are
calculated **from the same data that may contain the fraud**. A single very
large fraudulent transaction inflates the mean and — because standard deviation
is driven by *squared* deviations — inflates the standard deviation even more.
That can push the outlier's own Z-score back *under* the flagging threshold: the
outlier "masks" itself. This is a well-documented weakness of Z-score based
fraud screening. MAD and IQR are anchored to the median/quartiles, which barely
move even when a chunk of extreme values is added, so they resist this masking
effect — which is why they're the methods generally recommended in forensic and
audit analytics practice, and why MAD is the default here.

### Step 4 — Benford's Law
In many naturally-occurring numerical datasets, the leading digit is **not**
uniformly distributed — a leading `1` appears roughly 30% of the time, a leading
`9` only about 4.6% of the time. Fabricated numbers (people inventing amounts)
tend to spread leading digits far more evenly across 1-9, so a statistically
significant deviation from the expected Benford curve (tested with a chi-square
test at 95% confidence, critical value 15.507 for 8 degrees of freedom) is a
recognised screening signal for manipulated figures.

**Important caveat, shown in the app:** Benford's Law needs a reasonably large
population (the app requires at least 30 values, though 100+ spanning several
orders of magnitude is far more reliable) to mean anything. It is a *screening
tool*, not proof of fraud on its own — plenty of genuine datasets can look
unusual by chance, and plenty of manipulated ones can still pass.

### Step 5 — Reports
- **Excel workbook** (`.xlsx`) with three sheets: `Flagged_Transactions`,
  `Sampled_Transactions`, and a `Summary` sheet — styled headers, auto-sized
  columns, frozen header row.
- **PDF summary** (`.pdf`) with the population/sampling summary, fraud detection
  summary and top flagged transactions, and the Benford's Law verdict — safe for
  any Unicode content (₹ symbol, non-ASCII vendor names) without crashing (see
  below).

Both are generated **entirely in memory** — nothing is ever written to a
temporary file on disk.

---

## 3. Sensible handling of edge cases

- **A single unique amount value** (or too few distinct values for the
  requested number of strata) — Stratified Sampling progressively reduces the
  number of strata and falls back to one stratum (equivalent to random
  sampling) instead of crashing on `pandas.qcut`.
- **Empty results anywhere** — an empty flagged-transactions table, an empty
  sample, or a population too small for Benford's Law all render a clear
  on-screen message instead of a blank page or a stack trace.
- **Zero/negative amounts for Monetary Unit Sampling** — excluded from the MUS
  population (with the count shown), since a rupee-based sampling interval isn't
  meaningful for non-positive amounts; the app falls back gracefully rather than
  dividing by zero.
- **Non-ASCII / Unicode text anywhere that reaches the PDF** — see below.

---

## 4. Fixes made vs. the first working prototype

This app was rebuilt from an earlier working prototype (`app_v1_backup.py`,
kept in this submission for reference). Several issues in that version were
fixed rather than carried forward:

#### Why duplicates are never auto-deleted
The prototype called `drop_duplicates()` as part of "cleaning" the uploaded
file, and that ran **before** the duplicate-transaction fraud check — so exact
duplicate rows (a classic fraud/error red flag) were silently deleted and the
check could never find them. The fix here isn't to just reorder the two steps;
it's to stop silently deleting rows at all. Deciding that a repeated-looking
row should be removed from the population is an audit judgement call, not
something a "cleaning" step should do automatically before the auditor has even
seen it. So the same, type-coerced-but-undeduplicated dataset is now used for
**both** fraud detection and sampling/Benford's Law — duplicates are flagged,
never hidden.

#### Robust outlier detection
See "Statistical Outliers" above — MAD/IQR are now offered (MAD by default)
instead of only the mean/std-dev Z-score, which suffers from the "masking
effect."

#### True Monetary Unit Sampling
The prototype's "Monetary Unit Sampling" was actually probability-weighted
random sampling — a reasonable simplification, but not textbook MUS, and
mislabelling a method matters in an audit deliverable. This version implements
the real Cumulative Monetary Amount method (see Step 2 above) and labels it
**"Monetary Unit Sampling (PPS)"** for clarity.

#### Unicode-safe PDF export
The prototype used fpdf2's built-in `helvetica` core font, which is Latin-1
only and raises an exception on the first non-ASCII character it meets — a real
crash risk given vendor names or the ₹ symbol are exactly the kind of content
this tool handles constantly. This version looks for a Unicode-capable TrueType
font already present on the machine (Windows, macOS and Linux each ship at
least one common candidate — Arial/Segoe UI, Liberation Sans, or DejaVu Sans)
and registers that with fpdf2 at startup. If none is found (e.g. a minimal
headless environment), it falls back to the Latin-1 core font **plus** an
ASCII-sanitising text filter (₹ becomes "Rs."), so PDF export can never crash —
worst case it degrades formatting slightly instead. See
[§5 "Known limitations"](#5-known-limitations) for the trade-off this involves.

*(A second, unrelated PDF bug was also found and fixed during testing: fpdf2's
`multi_cell(w=0, ...)` leaves the cursor at the right margin rather than
resetting to the left margin, so several consecutive `multi_cell` calls with
`w=0` would compute an ever-shrinking width and eventually fail with "Not
enough horizontal space." The custom `AuditPDF` class now resets the x-position
before every `multi_cell` call.)*

#### Edge-case handling
See §3 above — none of these existed in the prototype.

#### Flexible column mapping (added after testing against a real export)
The prototype (and the first version of this rebuild) rejected any file that
didn't use its exact seven column headers. Tested against a real purchase
register, that immediately failed — its columns were named `Transaction_ID`,
`Transaction_Date`, `Approved_By`, `Department`, etc., and it had no
"raised by" equivalent at all. The fix, described in §1 above, is an
auto-detected, user-confirmed column mapping step, with only four fields
(voucher/ID, date, vendor, amount) treated as truly required — everything
else degrades gracefully instead of blocking the file.

---

## 5. Known limitations

- **PDF Unicode font is auto-detected, not bundled.** Rather than shipping an
  extra binary font file with the submission, the app looks for a system font
  at runtime. This keeps the submission smaller and avoids a licensing/binary
  dependency, and in practice Windows, macOS and mainstream Linux distributions
  all ship a suitable font — but on an unusual or stripped-down environment
  with none of the candidate fonts present, PDF export will silently fall back
  to ASCII-safe formatting (₹ → "Rs.", other non-Latin-1 characters replaced)
  rather than true Unicode rendering.
- **Benford's Law is a screening tool, not proof.** A significant chi-square
  result is a prompt for further enquiry, not a finding in itself — and it
  needs a reasonably large, naturally-varied population to be meaningful.
- **The six fraud checks are rule-based heuristics**, not a trained model. They
  will produce false positives (e.g. a genuinely round-number rent payment) and
  can be evaded by anyone who knows the rules — they're a first-pass screening
  layer for an auditor to follow up on, not a verdict.
- **No persistence.** Uploaded data, samples and results exist only for the
  current browser session (Streamlit's `session_state`) and are lost on
  refresh/restart — by design, since this tool never writes anything to disk.
- **Single-currency (₹) assumption.** The tool assumes all amounts are in
  Indian Rupees; it does not handle multi-currency transaction files.
- **This is a training/capstone tool**, explicitly not a certified audit
  product — see the disclaimer in the app's footer and in the PDF export.

---

## 6. Project files

| File | Purpose |
|---|---|
| `app.py` | The application (run this) |
| `app_v1_backup.py` | Untouched copy of the original prototype, kept for submission history |
| `requirements.txt` | Pinned dependency versions |
| `sample_data.csv` | A saved copy of the synthetic demo dataset (with planted anomalies) |
| `run.bat` | Windows double-click launcher |
| `.streamlit/config.toml` | App theme (colour palette) |
| `README.md` | This file |

## 7. Tech stack

Streamlit (UI/app framework) · pandas / numpy (data handling & statistics) ·
Plotly (interactive charts) · openpyxl (Excel export) · fpdf2 (PDF export).
