# Example files (all synthetic)

| Folder / file | What it is |
|---|---|
| `Input_Examples_Synthetic/day1_2026-11-24/` | One day's input files as the ERP / bank would give them: bank balances, facility, category list, receivables, additional collections, vendor PDC register, payment plan, bill discount / LC, other & recurring items (long and wide layouts), payment history. Upload them in the app (Uploads) or load them with `scripts/seed_demo.py`. |
| `Input_Examples_Synthetic/day2_2026-11-25/` | The next day's files, to show that re-uploading keeps every user change (overrides). |
| `Input_Examples_Synthetic/acceptance/` | A synthetic month with about 70 PDCs and the lot totals worked out by hand (acceptance test 1). |
| `Output_Examples/Checked_Excel_Export_2026-11-24.xlsx` | A real export from the demo data: Forecast, Items, Holds, Bank and About sheets. Every forecast figure is a live formula; LibreOffice recalculated all 359 formula cells and each matched the app before release. |
| `Output_Examples/CFO_Layout_Draft.xlsx` | The CFO-style layout draft agreed before building the screens. |

No real company data is included.
