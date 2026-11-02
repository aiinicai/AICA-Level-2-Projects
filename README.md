# FinSight AI — ICAI AI Level 2 Capstone

A runnable **Python 3.14 (64-bit) Streamlit application** combining financial statement validation, deterministic ratio analysis, explainable risk rules, optional OpenAI CFO commentary, approval workflow and Excel/PDF exports.

**For Python 3.14.8 on Windows, read `PYTHON314_SETUP.md` first. The `>>>` Python prompt is not the Windows command prompt.**

## Windows quick start
1. Install Python 3.14 (64-bit) from python.org, enabling **Add Python to PATH**.
2. Extract the ZIP to a writable folder (for example `Documents\FinSight_AI`).
3. Double-click `run_windows.bat`. The first run creates a virtual environment and installs packages (internet required).
4. Streamlit opens in your browser at `http://localhost:8501`.
5. Click **Download example workbook**, then upload `sample_data/sample_financials.xlsx`.
6. Review KPIs and risk flags, generate an offline advisory, enter a reviewer name and approve. Download PDF and Excel.

### Manual setup (PowerShell or Command Prompt)
```bat
cd FinSight_AI
py -3.14 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

### Optional OpenAI AI commentary
Set `OPENAI_API_KEY` in the environment before launching. In Command Prompt for the current session:
```bat
set OPENAI_API_KEY=your_api_key_here
run_windows.bat
```
Do **not** embed API keys in code, sample files or version control. Turn on **Use OpenAI commentary** in the sidebar. The app sends only calculated structured summary facts, **not** the original workbook, to the model. Use anonymised data and obtain permission before submitting client financial information to an external provider. API access may incur charges. If the model is unavailable, switch off the toggle for an offline deterministic draft.

## Workbook format
Sheet named `Financials`; first column `metric`; other columns are financial periods (at least two). All mandatory metrics must be present. All monetary amounts must use the **same scale**. Source statements are assumed to have positive revenue, costs and asset/liability amounts; negative net income/cash flow is permitted. See sample workbook.

The balance-sheet check assumes `current_assets + noncurrent_assets = current_liabilities + long_term_debt + equity`. Other noncurrent liabilities must be included in the provided `long_term_debt` amount for the sample simplified schema, or the schema must be extended. This is an educational simplified model, not a complete statutory statement mapping.

For days metrics, the first period is N/A unless opening balances are supplied. If credit sales/purchases are missing, revenue/COGS are used as **proxies**; interpret with caution. Capital employed uses average equity plus interest-bearing debt as a simplified proxy.

## Workflow
`DRAFT → VALIDATED → ANALYSED → PENDING_REVIEW → APPROVED / REJECTED`. Approval is mandatory for exports. The SQLite log is stored in the current user's home folder at `.finsight_ai/workflow.db`. Note: This proof of concept has no user authentication or tamper-proof audit log; do not deploy for confidential multiuser production use without hardening.

## Run tests
```bat
python -m pytest -q
```

## Scope and limitations
- Input: structured Excel (`.xlsx`), not arbitrary PDF/OCR. PDF **output** is supported.
- No trained machine learning model is claimed. Explainable deterministic risk and anomaly rules are used in the Standard edition.
- Ratio formulas depend on financial definitions and available schedules. Cross-check with professional accounting policies.
- Approval state is recorded, but commentary changes after approval are not separately versioned in this demo. Re-approval is recommended after changes.
- No automated email transmission. External notifications can be added later.
- Reports are educational and require independent Chartered Accountant review.

## Suggested demo
Upload synthetic workbook → show ratios → review cash flow divergence flag → generate commentary → approve → download CFO PDF and Excel analysis.
