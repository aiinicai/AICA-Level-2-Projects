ECL Stage Migration Matrix & Commentary Narrator
AICA Level 2 Capstone Project — Hitesh Bhadada, Financial Controller
**Prebuilt Windows executable:** [Download ecl_gui.exe](https://drive.google.com/file/d/1tC18DdHfVCi3tpNmVScdrHC3KtjwgRpt/view?usp=drive_link)
A desktop tool that takes loan-level data across period-ends and produces a Board/Audit-Committee-ready ECL stage migration analysis — with loan-level drill-down, an Ind AS 107 para 35H loss-allowance reconciliation, and an RBI IRACP vs Ind AS 109 comparison.
Two files, used together:
File	Role
`ecl_migration_matrix.py`	The calculation engine. All arithmetic, stage logic, and disclosure formats live here. Can also be run alone from the command line.
`ecl_gui.py`	A Tkinter desktop window on top of the engine. Adds no calculation logic of its own — it only lets you point at a folder, pick two periods, and click Run instead of using command-line flags.
Both files must be kept in the same folder. `ecl_gui.py` imports `ecl_migration_matrix.py` directly and will not run without it.
---
1. Requirements
Python 3.9 or later
Internet access only needed for installation (or for the optional AI commentary step below) — the tool itself runs 100% offline
Install the required packages from the official Python Package Index (PyPI) only — do not use a custom/unofficial index:
```bash
pip install pandas openpyxl
```
Optional, only if you need these specific features:
```bash
pip install xlrd        # only if reading legacy .xls files
pip install pyxlsb      # only if reading .xlsb files
pip install anthropic   # only if you want the AI-polished commentary (--ai)
```
You can verify any package on its official PyPI page first, e.g. `https://pypi.org/project/pandas/`.
---
2. Folder Setup
Keep one data file per period-end in a `data` folder next to the scripts:
```
your-project-folder/
  ecl_migration_matrix.py
  ecl_gui.py
  data/
    Q1FY25.csv
    Q2FY25.xlsx
    Q3FY25.csv
    Q4FY26.csv
```
Files may be CSV, XLSX, XLSM, XLS, or XLSB, freely mixed. Running the tool also creates:
```
  input_archive/    (a dated copy of the files used in each run)
  output/           (one timestamped sub-folder per run, containing the
                      Excel workbook, a text copy of the commentary, and
                      a run log with SHA-256 hashes of the source files used)
```
Required columns in each data file
Column	Notes
`Period`	e.g. `Q1FY26`. If missing, the file name is used instead.
`LoanID`	Unique loan identifier
`CustomerName`	Borrower name — mask/anonymise before sharing the file outside your organisation
`Stage`	`Stage 1` / `Stage 2` / `Stage 3`
`Outstanding_Cr`	Outstanding amount for that loan, that period (Rs. Cr)
`Provision_Cr`	ECL provision held for that loan, that period (Rs. Cr)
For the RBI IRACP disclosure, also add
Column	Notes
`DPD`	Days past due as at that period-end (integer). This alone is enough — the tool auto-classifies each loan (Standard/Sub-standard/Doubtful/Loss) and auto-computes its IRACP provision.
Fully optional refinements
Column	Notes
`Secured_Value_Cr`	Realisable value of security. If absent/blank, the loan is treated as fully unsecured (the prudent default — this can only overstate, never understate, the provisioning floor). Flagged on the auto-generated `IRACP_Assumptions` sheet.
`Loss_Flag`	`Y` where the asset has been identified as a loss asset by the NBFC, its auditor, or RBI on inspection. If absent, no asset is treated as a loss asset.
> **Regulatory scope:** IRACP thresholds and provisioning rates implemented are those for an NBFC in the **Middle Layer** under the RBI (NBFC – IRACP) Directions, 2025. Base Layer and Upper Layer rates are not implemented.
---
3. Running the Tool
Option A — Desktop window (recommended for non-technical review)
```bash
python ecl_gui.py
```
Data folder — browse to (or type) your `data` folder, then click Scan Folder. Every period found is listed with loan count and total outstanding.
Periods — pick a FROM and TO period (or tick "Run ALL pairs" to analyse every consecutive pair at once).
AI commentary (optional) — tick "Include AI commentary" and paste an Anthropic API key if you want an AI-polished narrative in addition to the deterministic one. Leave it unticked to skip this entirely — the tool still produces the full deterministic commentary and disclosures either way.
Click Run. Progress is shown in the log pane.
Click Open Output Folder once the run finishes.
Option B — Command line
```bash
# interactive — scans ./data, lists periods, asks which two to compare
python ecl_migration_matrix.py

# point at a specific data folder
python ecl_migration_matrix.py --data-dir /path/to/period_ends

# just list available periods, then exit
python ecl_migration_matrix.py --list-periods

# skip the prompt (for scheduled/batch runs)
python ecl_migration_matrix.py --compare Q4FY25:Q3FY26
python ecl_migration_matrix.py --compare Q1FY26:Q3FY26 Q2FY26:Q4FY26

# legacy: one file holding several periods
python ecl_migration_matrix.py --input-file all_quarters.csv

# with AI-polished narrative (needs internet + ANTHROPIC_API_KEY)
python ecl_migration_matrix.py --compare Q4FY25:Q3FY26 --ai
```
---
4. Output
Each run produces an Excel workbook with:
Sheet	Contents
`Summary`	Period-wise stage totals + commentary
`Mig_<P1>_<P2>`	Migration matrix per period pair — every number is a clickable hyperlink
`Det_<From>_<To>_<P1>_<P2>`	Loan-level detail behind each matrix cell
`IndAS107_35H_<P1>_<P2>`	Statutory disclosure: loss-allowance reconciliation (opening to closing), per Ind AS 107 para 35H
`RBI_IRACP_Comparison_<P>`	Statutory disclosure: IRACP vs Ind AS 109 comparison and Impairment Reserve requirement (produced whenever a `DPD` column exists)
`IRACP_Assumptions_<P>`	Where security data was missing, and what was assumed
`IRACP_LoanWorking_<P>`	Per-loan IRACP audit trail
Alongside the workbook, each run folder also contains a plain-text copy of the commentary and a run log recording exactly which source files (with SHA-256 hashes) fed that run.
---
5. What This Tool Does Not Do
It does not compute ECL provisioning itself — `Provision_Cr` is taken as given from your source systems, governed by Ind AS 109 and RBI norms there.
The optional AI step only drafts prose from already-computed aggregate figures — no customer names or loan IDs are ever sent to the AI API, and it never alters a stage, a provision, or an IRACP classification.
It does not substitute professional or regulatory judgement. Every run's commentary ends with a note to that effect — always verify against the latest RBI/ICAI notifications before relying on this for an actual filing or Board paper.
---
6. Regulatory Sources
Ind AS 107, para 35H (MCA-notified text) — opening-to-closing loss-allowance reconciliation requirement.
`https://www.mca.gov.in/Ministry/pdf/IndAS107_2020_10112020.pdf`
RBI (NBFC – IRACP) Directions, 2025 (effective 28-Nov-2025) — parallel IRACP computation, comparison disclosure, and Impairment Reserve requirement.
`https://www.rbi.org.in/`
---
7. Data Privacy
Everything runs 100% locally. No data leaves your machine unless you use `--ai` / tick the AI option — and even then, only aggregated stage totals are sent, never customer names or loan IDs.
