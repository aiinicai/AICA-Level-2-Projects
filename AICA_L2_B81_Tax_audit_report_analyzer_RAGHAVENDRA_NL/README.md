# Form 3CD Tax Audit Analyzer

An AI-assisted decision-support tool that reads a Form 3CA/3CD e-filing JSON export and
produces a clause-referenced financial summary, a full 44-clause dashboard, and a draft
income-tax computation — in Excel, HTML, PDF and Word.

Built as a capstone project for the ICAI Certificate Course on AI — Level 2.

## What it does

1. **Key Financial Summary** — cross-references the figures an auditor most often needs
   (turnover, depreciation, section 40(a) TDS disallowances, section 43B, MSME dues,
   gratuity, etc.) to their exact clause and sub-clause.
2. **44-Clause Dashboard** — every clause of Form 3CD in one table.
3. **Tax Computation Draft** — a PGBP build-up with the statutory disallowances applied
   automatically, and clearly flagged placeholders for the figures that can only come
   from the financial statements (not from Form 3CD itself).
4. **Four output formats** — a formatted Excel workbook, an HTML dashboard, a PDF report,
   and a Word report, each carrying a built-in Tax Head sign-off block and a compliance
   disclaimer.

## Important — read before use

This tool is a **decision-support and review aid only**. It does **not** constitute an
audit opinion and is not a substitute for the auditor's independent verification of Form
No. 3CD particulars under the Standards on Auditing (SAs) and the ICAI Guidance Note on
Tax Audit under section 44AB. All figures must be independently verified against the
books of account, supporting documents and management representations before being
relied upon for filing. This disclaimer is also embedded in every generated output file.

## Repository contents

| Path | Description |
|---|---|
| `analyze_form3cd.py` | Core engine — parsing, clause extraction, and all four report generators. Also runnable as a CLI. |
| `analyze_form3cd_gui.py` | Tkinter GUI front-end (purple/white theme) for the same engine. |
| `sample_data/demo_form3cd_synthetic.json` | A fully **synthetic** demo input — fictitious company, fabricated figures. Safe to run and share; contains no real client data. |
| `sample_data/build_synthetic_demo.py` | The script that generated the synthetic demo JSON above, for transparency/reproducibility. |
| `Form3CD_Capstone_Presentation.pptx` | Capstone presentation deck (architecture, before/after, sample output, build process). |
| `Text - Problem & Prompt.docx` | Written problem statement and a structured summary of the prompts used to build this tool. |
| `Form3CD_Analyzer_GUI.exe` | Standalone Windows GUI build — no Python installation required. Double-click to launch. |

## Running it

**From source:**

```bash
pip install -r requirements.txt
python analyze_form3cd.py sample_data/demo_form3cd_synthetic.json --formats xlsx,html,pdf,docx
```

Or launch the GUI:

```bash
python analyze_form3cd_gui.py
```

**Or, on Windows, without installing Python at all** — download `Form3CD_Analyzer_GUI.exe`
and run it directly. It was packaged with PyInstaller; a console build of
`analyze_form3cd.py` can be produced the same way if a command-line version is needed:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name Form3CD_Analyzer_GUI analyze_form3cd_gui.py
```

## Confidentiality note

Every sample input, output, and screenshot in this repository was generated from the
fully synthetic dataset in `sample_data/` — no real client, PAN, or financial figure
appears anywhere in this project.
