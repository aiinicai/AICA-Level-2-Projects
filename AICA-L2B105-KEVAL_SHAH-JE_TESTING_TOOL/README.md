# Journal Entry Testing Tool

> **Capstone Project · AICA Level 2 batch** · Author: **Keval Shah**

A simple, offline desktop tool that reads a full **SAP general-ledger extract**,
tests **every** journal entry against **12 easy-to-explain risk rules**, scores
each entry, picks an audit sample and writes a ready-to-file **Excel workpaper**.

It supports the auditor's response to the presumed risk of **management override
of controls** under **SA 240** (paras 32–33 and A43–A44). Sample selection
follows **SA 530**.

---

## Why this tool?

When the auditor tests journal entries by hand, a typical engagement goes like this:

1. Export lakhs of GL lines from SAP.
2. Filter them by hand in Excel for Sundays, month-end, round amounts and so on.
3. Pick a "judgemental" sample with no documented basis.

This tool runs all of those filters at once, on 100 % of the population. It turns
the results into a **risk score**, so every selection can be explained and
re-performed.

---

## The 12 risk rules

Every rule answers one of four simple questions.

| # | Question | Rule | Default weight |
|---|----------|------|:-:|
| 1 | **WHEN** was it posted? | Posted on a **Sunday** / non-working day | 10 |
| 2 | | Posted on a **public holiday** | 10 |
| 3 | | Posted in the **last 3 days of the month** | 10 |
| 4 | | **Back-dated**: entered > 5 days after the posting date | 15 |
| 5 | **WHO** posted it? | Posted by a **privileged / IT user** | 20 |
| 6 | | **Manual entry by a super-user** (e.g. CFO) | 25 |
| 7 | | **Manual journal** (SAP doc type `SA`) | 15 |
| 8 | **HOW MUCH?** | **Round-sum** amount (exact multiple of ₹1,00,000) | 10 |
| 9 | | **Large** amount (≥ ₹1 crore) | 15 |
| 10 | **WHAT** does the narration say? | **Missing** narration | 10 |
| 11 | | **Generic** narration ("adjustment", "jv", "misc"…) | 5 |
| 12 | | **Red-flag keyword** ("plug", "balancing figure", "as instructed"…) | 25 |

**Score** = sum of the weights of the rules a journal triggers.

| Band | Score |
|------|-------|
| 🔴 Critical | ≥ 60 |
| 🟠 High | ≥ 40 |
| 🟡 Medium | ≥ 20 |
| 🟢 Low | < 20 |

You can change all weights, bands, thresholds, user lists, keywords and holidays
from the **⚙ Settings** screen. You never need to edit code.

> *Deliberately left out to keep the tool simple:* Benford's Law, Z-score
> outliers, duplicate/reversal detection, dormant accounts and account-category
> rules.

---

## How it works

```
SAP GL extract (.xlsx / .csv)
        │
        ▼
1. Column mapping     auto-detects SAP headings (BELNR, BUDAT, USNAM, SGTXT…)
2. Data-quality check  Dr = Cr? each JE nets to 0? blank users / dates?
3. 12 risk rules       applied to every line
4. Scoring             line flags rolled up to the journal; weights summed
5. Risk band           Low / Medium / High / Critical
6. Sampling            Top-N by risk score  +  random pick from the rest
        │
        ▼
Excel workpaper (8 sheets)
```

### Excel workpaper sheets

| Sheet | What it shows |
|-------|---------------|
| **Summary** | Population totals, balance check, journals per risk band, top rules |
| **Methodology** | Purpose, approach, sampling basis, limitations (ready for the file) |
| **Data Quality** | Completeness checks on the extract |
| **Risk Register** | Every journal with its score, band and triggered rules |
| **Explainability** | For each High/Critical journal: score breakdown, assertion, SA reference, suggested audit procedure |
| **Samples** | Selected journals and the method used |
| **Rule Frequency** | How many journals each rule flagged |
| **Population by Month** | Lines / journals / value per month |

---

## Getting started

**Requirements:** Python 3.10+ on Windows. The desktop app uses Tkinter, which
ships with Python.

```bash
git clone https://github.com/aiinicai/AICA-Level-2-Projects.git
cd AICA-Level-2-Projects/AICA-L2B105-KEVAL_SHAH-JE_TESTING_TOOL
pip install -r requirements.txt
```

### Option A: desktop app

```bash
python je_testing_app.py
```

1. Click **Create sample GL** (or **Browse…** to your own SAP extract).
2. Optional: click **Check column mapping**.
3. Click **▶ Run JE Testing**.
4. Click **Open Workpaper**.

### Option B: command line

```bash
python je_testing.py --make-samples          # create demo data
python je_testing.py sample_data/sample_GL.xlsx
python je_testing.py "path/to/GL dump.xlsx"  # your own file
```

### Option C: build a Windows .exe

```bash
pip install pyinstaller
pyinstaller "JE Testing.spec"                # -> dist/JE Testing.exe
```

---

## Using it on a real SAP extract

1. In SAP, export the line items for the year (e.g. **FBL3N** / **FAGLL03**, or a
   **BKPF + BSEG** download). Include: Document Number, Company Code, G/L
   Account, User Name, Document Type, Entry Date, Posting Date, Amount in Local
   Currency, Text.
2. Open **⚙ Settings** and set the client's details:
   - **Users tab:** privileged/IT user IDs and super-user IDs, taken from the
     SAP access review (SU01 / SUIM).
   - **Thresholds:** large-amount and round-sum limits based on materiality.
   - **Keywords & Holidays:** the client's holiday list for the year.
3. Run the tool. Then review the **Explainability** sheet and test the
   **Samples**.

> ⚠️ A flag is a **prompt to investigate, not a conclusion**. Professional
> judgement remains with the engagement team.

---

## Project structure

```
├── je_testing.py         # engine + command line (rules, scoring, sampling, Excel)
├── je_testing_app.py     # desktop app (Tkinter) + Settings screen
├── sample_data/          # demo GL is created here by "Create sample GL" / --make-samples
├── input/                # put your own GL extracts here (git-ignored)
├── output/               # workpapers are written here (git-ignored)
├── JE Testing.spec       # PyInstaller recipe for a Windows .exe
├── requirements.txt
└── LICENSE
```

`je_config.json` (your settings) is created on first run. Git ignores it
because it may hold client user IDs.

---

## Data privacy

- The tool runs **100 % offline**. No data leaves the machine.
- `input/`, `output/` and `je_config.json` are git-ignored, so client data
  cannot be pushed by accident.
- The demo file `sample_data/sample_GL.xlsx` (created by **Create sample GL**) is
  **entirely fictitious** and is the same every time it is generated.

---

## Licence

MIT. See [LICENSE](LICENSE).
