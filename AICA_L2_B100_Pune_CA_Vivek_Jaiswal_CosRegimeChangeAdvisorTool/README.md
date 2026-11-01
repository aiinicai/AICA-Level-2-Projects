# RegimeWise

Group tax planning analyser: for each company, compares tax over five years under the
normal regime and the concessional regime under Section 200 (old 115BAA), tests every switch year, picks the option with
the lowest present value of tax, and drafts an advisory note.

## Setup (one time)

```bash
python -m venv venv
venv\Scripts\activate          # Windows  (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
```

Optional, for the AI-drafted note: create `.env` containing `ANTHROPIC_API_KEY=your-key-here`.
Everything else, including a template note, works without a key.

## Your data (sample files hold INVENTED figures)

Blank templates: use the **Templates** download buttons in the app's sidebar, or copy
`data/templates/companies_template.csv` and `data/templates/projections_template.csv`.
Fill them in Excel, keep the column names unchanged, save as CSV and upload both.
Leave a cell blank or 0 if it does not apply. Commas in amounts are fine.
The app warns if a column is missing or a company appears in only one file.

`data/companies.csv` - one row per company, opening position:

| Column | Meaning |
|---|---|
| entity | Company name (anonymise: "Co A", "Co B") |
| bf_business_loss | Brought-forward business loss |
| unabsorbed_depreciation | Unabsorbed depreciation |
| mat_credit_bf | MAT credit brought forward |
| loss_not_allowed_concessional | Part of the losses that cannot be set off after opting for Section 200 (old 115BAA) |

`data/projections.csv` - one row per company per year:

| Column | Meaning |
|---|---|
| entity, year | Must match companies.csv; year like 2026-27 |
| turnover | Decides the 25% or 30% normal rate |
| income_before_setoff | Taxable income before loss set-off (negative = loss) |
| book_profit | For MAT |
| dividend_received, dividend_distributed | For the inter-corporate dividend deduction |

## Run

```bash
python engine.py        # prints results for the sample group
python test_engine.py   # checks the engine against hand calculations
streamlit run app.py    # opens the dashboard
```

## Simplifications (state these in your report)

- Rates in `RATES` (engine.py) are inputs, not law. Verify against the Income-tax Act, 2025 and the current Finance Act.
- No surcharge marginal relief; no expiry of losses or MAT credit within the horizon.
- Value beyond the last projection year is ignored: unused MAT credit at the end is shown, not valued.
- The new-manufacturing concessional rate and non-corporate taxpayers are out of scope.

## Files

| File | Purpose |
|---|---|
| `engine.py` | Tax rules, five-year simulation, optimiser |
| `test_engine.py` | Hand-calculated checks |
| `note.py` | Template and AI-drafted advisory note, Word export |
| `app.py` | Streamlit dashboard |
