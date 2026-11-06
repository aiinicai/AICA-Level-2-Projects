**ICAI AI Certification Course (AICA) Level 2 - Module C Capstone Project**  
Submitted by CA Madhusudan Jain, Chartered Accountant, Pune · Batch 100, Pune  
Project: AI-Powered Statutory Audit Assistant for Co-operative Housing Societies  
Report: `docs/Capstone_Project_Report.docx` · Deck: `docs/Capstone_Presentation.pptx` · Run: `streamlit run app.py`  
Video walkthrough: [Google Drive video](https://drive.google.com/file/d/1qUlRMkr3Ff5G6ahdCm1TQvMkgRiyI1Fr/view?usp=drive_link)  
Note: the tool needs an Anthropic API key for live drafting (enter it in Data & settings); without one it runs on offline templates. No key is included in this repository.

---

# AI-Powered Statutory Audit Assistant for Co-operative Housing Societies

Capstone project for the ICAI **AI Certification Course (AICA) Level 2**.
The tool takes a housing society's accounting data (member bills, receipts,
bank statement, expenses, fund balances, meeting minutes) and performs the
statutory audit tests a panel auditor runs under the Maharashtra Co-operative
Societies Act, 1960, then drafts the audit observations, management letter,
member reminder letters, governance summary and tax note with an LLM.

Four integrated modules:

| Module | What it does |
|---|---|
| 1. Statutory audit assistant | Member ledger reconstruction, interest recomputation (bye-law 72), GST Rs 7,500 test (Circular 109/28/2019), sinking/repair fund compliance, bank reconciliation, expense anomaly tests (duplicates, split invoices, related parties, cash, Benford), TDS check |
| 2. Defaulter management | Ageing, defaulter classification, s.101 recovery candidates, AI-drafted reminder letters |
| 3. Compliance calendar and minutes analyser | Rule-driven statutory calendar with status as at the audit date; parses MC/AGM minutes for notice, quorum, resolutions and action items and cross-checks them against the books |
| 7. Tax computation | Mutuality analysis, s.80P(2)(d), normal slabs vs s.115BAD, TDS credit, s.234B/234C interest |

## Quick start - the application

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

The app opens at http://localhost:8501 with eight pages: Overview, Member ledger


### Firm profile and real society data

Drafts are issued in the name of the signing partner (default: CA Madhusudan Jain, Chartered
Accountant, Pune, jjaa.in). Edit the signing partner, membership number and address under
**Data & settings**; it is saved to `data/firm.json` and used in the header, the sign-off of
every draft and the model's system prompt.

For a demo without any file, press **Mock-up data upload** on the same page: a second synthetic
society (Green Meadows, Pune, `data/mockup/`, built by `chs_audit.mockup_data`) is validated and
loaded exactly as an upload would be, and every page re-runs on it.

To audit a real society, open **Import society data**, download the Excel template, fill
the nine sheets (plus a zip of minutes as .txt files), and upload. The file is validated
(sheet names, columns, dates, flat numbers, vendor codes) before the tests run.

### API key (keep it private)

Open **Data & settings** in the app and paste the key in the *API key* box, then click
*Save AI settings*. The key stays in the browser session's memory only and is never written
to disk by the app.

To avoid re-pasting on every start, copy `.streamlit/secrets.example.toml` to
`.streamlit/secrets.toml` and fill in `ANTHROPIC_API_KEY`. That file is git-ignored.
The `ANTHROPIC_API_KEY` environment variable works the same way. Never put the key in
`app.py`, the report, the slides, or a chat window.
& defaulters, GST check, Funds/bank/expenses, Compliance & minutes, Income-tax,
AI drafting studio and Data & settings. Paste your Anthropic API key under
**Data & settings** (held in memory for the session only) to draft documents and
chat with the audit; upload your own society workbook on the same page.

## Command line (batch run)

```bash
cd src
../.venv/bin/python -m chs_audit.generate_data ../data/raw      # synthetic 64-flat society
../.venv/bin/python -m chs_audit.run_audit --data ../data/raw --out ../output --as-of 2026-07-15
```

Add `--ai` to draft the narratives with Claude (set `ANTHROPIC_API_KEY` or log in
with `ant auth login`). Without it the tool uses deterministic templates, so the
whole pipeline runs offline.

## Outputs (`output/`)

- `CHS_Audit_Workbook_FY2025-26.xlsx` - 22 sheets: observations, every test schedule, and the drafted documents
- `dashboard.html` - self-contained static dashboard (the interactive version is the Streamlit app)
- `Draft_*.txt` - audit observations, management letter, governance summary, tax note, reminder letters
- `ai_prompt_log.md` - every prompt, response and guardrail flag
- `findings.csv`, `summary.json`

## Project layout

```
app.py               Streamlit application (interactive tool)
src/chs_audit/
  config.py          society master data, rates and thresholds
  generate_data.py   synthetic data with 19 seeded control failures (answer key in the workbook)
  loaders.py         reads the workbook and minutes
  audit_checks.py    modules 1-2: ledger, interest, GST, funds, bank, expenses, TDS
  compliance.py      module 3: calendar and minutes analyser
  tax.py             module 7: income-tax computation
  ai_writer.py       Claude drafting layer with offline fallback and citation guardrail
  report_excel.py    audit workbook writer
  dashboard.py       HTML/SVG dashboard
  run_audit.py       CLI entry point
data/raw/            generated input data and minutes
docs/                project report, presentation, prompt catalogue
```

## Data privacy

All data is synthetic. Member names and mobiles are invented, PANs are stored
masked, and the AI layer receives flat numbers and amounts only - never names,
mobiles or PANs - in line with the Digital Personal Data Protection Act, 2023.
