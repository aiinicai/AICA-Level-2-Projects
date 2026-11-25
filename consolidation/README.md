# Workforce Analytics – Consolidation Engine
AICA Level 2 Capstone · Multi-country workforce consolidation, workforce walk and budget variance

## How the solution fits together

```
Country SPOCs ──email──▶ Gmail ──▶ n8n "Workforce Data Intake" workflow
                                    • checks subject, country, month, attachment
                                    • saves Workforce_<Country>_<Mon-YYYY>.xlsx to Google Drive (WF_Inbox)
                                    • logs every submission, replies to the SPOC
                                    • 6 PM on days 1–10: emails FP&A a received / pending status
                                              │
                    Google Drive for desktop syncs WF_Inbox to your laptop
                                              ▼
                     consolidate.py  (this folder)
                                    • validates content of every file
                                    • builds the workforce walk, cost in INR, mixes
                                    • compares to budget (volume vs rate/mix split)
                                              ▼
            output/Consolidated_Workforce_<period>.xlsx  +  dashboard_data_<period>.json
                                              ▼
                                       CFO dashboard
```

## One-time setup (Windows)
1. Install Python 3.10+ from python.org (tick **Add Python to PATH**).
2. Open Command Prompt in this folder and run: `pip install -r requirements.txt`
3. Put these two reference files in this folder (already included in the sample pack):
   `Workforce_Budget_FY26.xlsx` and `Workforce_Assumptions_and_Control_Totals.xlsx` (FX rates and billing assumptions).
4. Point the `inbox` folder at the files n8n saves – either:
   * install **Google Drive for desktop** and pass the synced WF_Inbox path with `--input`, or
   * download the month's five files from Drive into `inbox\`.

## Monthly run
Double-click `run_consolidation.bat` and type the month (e.g. `Nov-2026`), or:

```
python consolidate.py --period Nov-2026 --input .\inbox --output .\output
```

The console prints every check, and the headline numbers:
`Total HC 2,773 (budget 2,667, +4.0%) | Monthly cost INR 178.9 Cr (budget 179.8 Cr, -0.5%)`

## Checks performed on each country file
| Check | Severity |
|---|---|
| File missing for a country | ERROR – country excluded, budget compared like-for-like |
| Required sheets / columns missing | ERROR |
| Duplicate employee or consultant codes | ERROR |
| Invalid grade, hire type, engagement type, bill frequency | ERROR |
| Exit date without exit type; contract ended without end reason | ERROR |
| Hire date after exit date; contract start after end | ERROR |
| Zero / missing salary or bill rate | ERROR |
| Someone active at last month-end is missing this month (roll-forward break) | ERROR |
| Location not the file's country; salary currency not local | WARN |
| CTC ≠ Fixed + Bonus | WARN (recomputed) |
| Opening + movements ≠ closing at group level | ERROR |

## Definitions
* **Opening** = active at previous month-end · **Closing** = active at this month-end
* **Hires** = Regular hires in month · **Project hires** = Project hires in month
* **Leavers** = resignations (internal) / contracts completed (external)
* **Terminations** = involuntary exits (internal) / early terminations and conversions (external)
* **Monthly cost** = internal CTC ÷ 12, external bill rate × billable units (160 hrs / 20 days / 1 month), converted at the month's FX rate to INR, for the population active at month-end
* **Variance** = Actual − Budget. Cost variance split: **Volume** = HC variance × budget cost per head; **Rate / mix** = (actual − budget cost per head) × actual HC

## Outputs
`Consolidated_Workforce_<period>.xlsx` – Summary, Workforce_Walk, Cost_by_Country, Budget_Variance, Grade_Mix, Location_Mix, Function_Mix, Project_Resources, Detail_Internal, Detail_External, FX_Used, Validation_Log

`dashboard_data_<period>.json` – the same numbers in one file for the dashboard, plus `index.json` listing every month in the output folder (copy both to `docs/data/`).

## Testing
The sample pack's control totals were reproduced exactly (walk) and to within INR 10 per line (cost, per-person rounding).
A negative test with a duplicate code, invalid grade, missing exit type, a dropped employee and a missing country raised all seven expected errors.
