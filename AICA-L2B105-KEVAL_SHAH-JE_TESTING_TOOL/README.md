# Journal Entry Testing Tool

> **Capstone Project · AICA Level 2 · Batch 105** · Author: **Keval Shah**

**▶ Demo video:** https://youtu.be/QhwX10tDqmM  ·  **Slides:** [Presentation - JE Testing Tool.pptx](Presentation%20-%20JE%20Testing%20Tool.pptx)

A simple, offline desktop tool for auditors. It reads a full **general-ledger (GL)
extract** from SAP or any other ERP and **links it to the Trial Balance (TB)**
to confirm the GL is complete. It then tests **every** journal entry against
**12 easy-to-explain risk rules**, scores each entry, selects an audit sample
and writes a ready-to-file **Excel workpaper**.

It supports the auditor's response to the presumed risk of **management override
of controls** under **SA 240** (paras 32–33, A43–A44). Sampling follows
**SA 530**. The completeness and accuracy of the data used are checked as
required by **SA 500**.

---

## What the tool does

| Step | What happens |
|------|--------------|
| 1. Read | Loads the GL extract (`.xlsx`, `.xls` or `.csv`). Recognises SAP column names automatically, including the offsetting account (GKONT), so both sides of every journal are shown even when the extract holds only one side. |
| 2. Check the data | 15+ checks: Dr = Cr, unbalanced journals, amounts typed as text, impossible dates (31-02), dates outside the financial year, duplicate lines, blank account / user / date, TB not balancing, accounts repeated in or missing from the TB. Each is marked **ok**, **ERROR** or **review**. |
| 3. **Link GL to TB** *(optional)* | For every account: **GL net movement** vs **TB movement (closing − opening)**. Any difference means the GL extract may be **incomplete**. Account names are taken from the TB. |
| 4. Test | Applies the 12 risk rules to every GL line. |
| 5. Score | Adds up the weights of the rules each journal triggers, then bands it Low / Medium / High / Critical. |
| 6. Sample | Selects the top 25 journals by score, plus 15 at random from the rest. |
| 7. Report | Writes a 9-sheet Excel workpaper. |

---

## Linking the GL to the Trial Balance

Before relying on journal-entry testing, the auditor must be sure the GL extract
is **complete**, with no journals missing. The tool checks this account by
account:

```
TB movement  =  TB closing balance  −  TB opening balance
Difference   =  TB movement  −  net total of that account in the GL extract
```

| Status | Meaning |
|--------|---------|
| **Agrees** | The GL extract fully explains the TB movement. |
| **Agrees (no GL movement)** | The account had no postings, and its TB balance did not change. |
| **DIFFERENCE** | The GL extract does not explain the TB movement. Some journals may be missing. Resolve this before relying on the testing. |
| **In GL but not in TB** | An account was posted to but is missing from the TB. Investigate. |

The TB needs an account column and a closing-balance column. An opening-balance
column is recommended. SAP-style TB layouts are recognised too: `G/L Acct`,
`G/L Account Description`, `TB - 1610`, `Derived TB - 1610`. The GL is compared
with the ledger balance (`TB - xxxx`), not the reclassified one, because
reclassifications never pass through the GL. If the TB has no opening balances,
the workpaper notes that balance-sheet differences may be opening balances.

With the **clean sample**, all 21 accounts agree. With the **flawed sample**, only
8 of 21 accounts agree, and the TB itself does not balance. The tool reports
both problems.

---

## The 12 risk rules

| # | Question | Rule | Default weight |
|---|----------|------|:-:|
| 1 | **WHEN** was it posted? | Posted on a **Sunday** / non-working day | 10 |
| 2 | | Posted on a **public holiday** | 10 |
| 3 | | Posted in the **last 3 days of the month** | 10 |
| 4 | | **Back-dated**: entered more than 5 days after the posting date | 15 |
| 5 | **WHO** posted it? | Posted by a **privileged / IT user** | 20 |
| 6 | | **Manual entry by a super-user** (e.g. CFO) | 25 |
| 7 | | **Manual journal** (SAP document type `SA`) | 15 |
| 8 | **HOW MUCH?** | **Round-sum** amount (exact multiple of ₹1,00,000) | 10 |
| 9 | | **Large** amount (₹1 crore or more) | 15 |
| 10 | **WHAT** does the narration say? | **Missing** narration | 10 |
| 11 | | **Generic** narration ("adjustment", "jv", "misc"…) | 5 |
| 12 | | **Red-flag keyword** ("plug", "balancing figure", "as instructed"…) | 25 |

**Score** = the sum of the weights of the rules a journal triggers.
**Bands:** Critical ≥ 60 · High ≥ 40 · Medium ≥ 20 · Low < 20.
You can change every weight, band, threshold, user list, keyword and holiday
from the **⚙ Settings** screen, without editing any code.

---

## The Excel workpaper (9 sheets)

| Sheet | What it shows |
|-------|---------------|
| **Summary** | Population, Dr = Cr check, **GL-to-TB result**, journals per risk band, sample count and random seed |
| **Methodology** | Purpose, completeness check, approach, sampling basis, limitations |
| **Data Quality** | Every data check on the GL and TB, with errors highlighted in red |
| **TB Reconciliation** | Every account: TB opening, closing, movement, GL movement, difference, status |
| **Risk Register** | Every journal with its accounts, narration, score, band and triggered rules |
| **Explainability** | For each High / Critical journal: score breakdown, assertion, SA reference, suggested audit procedure |
| **Samples** | The selected journals and the method used to select each one |
| **Rule Frequency** | How many journals each rule flagged |
| **Population by Month** | Lines, journals and value for each month |

---

## Login IDs and licence keys

The tool works like commercial software that has been sold to a customer.

**Two kinds of login ID**

| Role | What the role can do |
|------|---------------|
| **admin** | Run the testing, change **Settings**, open the **Users** screen (see licences, reset passwords) |
| **user** | Run the testing and open the workpaper only. Settings are locked. |

**Licence keys**

- Every login ID needs a **licence key** issued by the vendor. The key records
  the licence number, licensee, login ID, role and expiry date, and is
  **digitally signed** (Ed25519).
- The tool holds only the vendor's **public key**. It can check a licence but
  can never create one.
- On the first sign-in, the customer pastes their key to **activate** the login ID.
- The tool refuses a key that has been altered, belongs to another login ID, or has expired.
- The role is taken from the **signed licence**, so editing the user file to
  turn a normal user into an admin does not work.

**Passwords**

- Passwords are never stored. Only a salted **PBKDF2-SHA256** hash (600,000
  rounds) is kept in `users.json`.
- After 5 wrong attempts the program closes.
- The login screen does not reveal whether a login ID exists.

**Audit trail.** The Summary sheet records who ran the test, under which
licence, and when.

**For the vendor only.** `licence_generator.py` creates the key pair
(`init`), issues licence keys (`issue`) and adds login IDs (`add-user`). The
vendor's **private key** stays in `vendor/`. It is excluded from Git and from
the `.exe`.

Demo passwords and licence keys are **not** published here. They are given to
the evaluator separately.

---

## The Windows .exe

```bash
pip install pyinstaller
pyinstaller "JE Testing.spec"          # builds  dist/JE Testing.exe
```

To give the tool to a customer, put `JE Testing.exe` in a folder together with
their `users.json` (and, if wanted, `sample_data/`). Python does not need to be
installed on their computer. The `.exe` (about 75 MB) is **not** stored in Git,
which keeps the repository small.

---

## Getting started (from source)

**Requirements:** Python 3.10 or later on Windows. The desktop window uses
Tkinter, which comes with Python.

```bash
pip install -r requirements.txt
python je_testing_app.py               # sign in with your login ID
```

1. *(Admin, first time only)* Open **⚙ Settings** and enter the client's
   privileged / IT users and super-users. The tool ships with these lists blank.
2. Click **Browse…** to choose the GL extract and, optionally, the Trial Balance.
3. *(Optional)* Click **Check column mapping**.
4. Click **▶ Run JE Testing**, then **Open Workpaper**.

**Command line:**

```bash
python je_testing.py "GL dump.xlsx" "Trial Balance.xlsx"
python je_testing.py "GL dump.xlsx"          # GL only (completeness not checked)
```

---

## Sample data

All sample data belongs to a **fictitious company, Sunrise Engineering Pvt Ltd**
(FY 2025-26, company code 1000, 21 GL accounts). Every file is small and opens
instantly. In Git the files are kept as CSV; Excel copies come with the `.exe`.

| Folder | What it shows |
|--------|---------------|
| `INPUT_1_CLEAN DATA` | A clean GL (247 journals, 634 lines, with account names and the SAP offsetting account on every line) and TB. Every data check passes and all 21 accounts agree. Planted red flags include a CFO top-side entry on 31 March, a Sunday entry by an IT admin, a holiday posting and "balancing figure plug". |
| `INPUT_2_FLAWED DATA` | The tool still runs, but reports **14 data-quality issues**: amounts typed as text, 31-02-2026, dates outside the FY, duplicate lines, unbalanced journals, a TB that doesn't balance, an account repeated in the TB, accounts missing from the TB. It also contains extra red flags ("override", "do not record", "personal use"). |
| `INPUT_3_WRONG FILES (tool rejects)` | Missing Amount column, TB without a closing balance, a TB chosen as the GL, an empty file, a damaged Excel file, and a `.txt` file. Each one gets a clear message instead of a wrong workpaper. |

To rebuild the samples: `python make_sample_data.py` (developer script; it is
not part of the product).

---

## Security review

The code was reviewed manually and scanned with standard tools.

| Check | Result |
|-------|--------|
| **Bandit** (Python security scanner, all 4 code files) | **0 issues** after the fixes below. It found 10 low-severity items before. |
| **pip-audit** (known vulnerabilities in the libraries used) | **No known vulnerabilities** |
| Login and licence tests | Wrong password, unknown ID, another user's key, an altered key, a key edited to `role=admin`, and an expired key are **all refused** |
| Dangerous functions (`eval`, `exec`, `pickle`, shell commands) | **None used** |
| Network access | **None.** The tool runs 100 % offline. |

**Fixes made during the review:**

1. **Excel formula injection (fixed).** A narration such as
   `=HYPERLINK("http://…")` in the GL would have become a live formula in the
   workpaper. Every cell is now forced to plain text.
2. **Predictable random sample (fixed).** The random sample used a fixed seed,
   so it could be predicted. A new seed is now drawn for every run and recorded
   on the Summary sheet, so the selection can still be re-performed.
3. **Malicious Excel files.** `defusedxml` is now a requirement, which makes
   openpyxl reject booby-trapped Excel files ("XML bombs").
4. **Oversized or wrong files.** Only `.xlsx`, `.xls` and `.csv` files are
   accepted, up to 300 MB, with a clear message instead of a hang.
5. **Bad settings.** Non-numeric values in `je_config.json` are detected and
   replaced with defaults.
6. **Silent errors removed.** Failures are now reported instead of being ignored.

**Data privacy:** client data never leaves the computer. `input/`, `output/`,
`je_config.json`, `users.json` and the vendor's `vendor/` folder are excluded
from Git.

---

## Project structure

```
├── je_testing.py         engine + command line (TB link, rules, scoring, sampling, Excel)
├── je_testing_app.py     desktop window: sign-in, licence activation, Settings, Users
├── je_access.py          password hashing + licence-key verification
├── licence_generator.py  VENDOR tool: issue licence keys, add login IDs
├── make_sample_data.py   developer script that builds the sample data
├── sample_data/
│   ├── INPUT_1_CLEAN DATA/                   clean GL + TB
│   ├── INPUT_2_FLAWED DATA/                  GL + TB with data errors
│   └── INPUT_3_WRONG FILES (tool rejects)/   wrong / damaged files
├── input/                command line: put your own GL / TB here (not uploaded)
├── JE Testing.spec       recipe to build a Windows .exe (pyinstaller)
├── requirements.txt
└── LICENSE
```

> A flag is a **prompt to investigate, not a conclusion**. Professional judgement
> stays with the engagement team.

Licence: MIT. See [LICENSE](LICENSE).
