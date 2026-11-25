# Forecast sheet layout (draft, CFO view)

Status: **draft for review**. The sample workbook `docs/Forecast_layout_draft.xlsx` shows this
layout filled with synthetic data, using live formulas. Rebuild it with:
`python scripts/make_layout_draft.py`.

The screen grid (Phase 6) and the Excel export (Phase 7) both follow this layout.

## Design principles
1. **Answer the CFO's three questions first**: Do we have enough cash? When is the tightest point?
   What can we move? So the sheet opens with a KPI strip, and funding position sits right under closing.
2. **One page per decision level**: summary on top, then the PDC and bill discount detail lists, then
   the bank tie-out and the memo items.
3. **Every number can be traced**: category rows are `SUMIFS` over the Data sheet, totals are formulas,
   and holds are shown as a memo, never silently added back.
4. **Consistent signs**: inflows and outflows are entered as positive figures. Only Net, Closing,
   Funding position and Gap can be negative, and negatives show as red figures in brackets.

## Header block
| Row | Content |
|---|---|
| 1 | Company name (synthetic) |
| 2 | Working Capital Cash Flow Forecast - OMR |
| 3 | As-of date - Scenario - Status (Draft / Final) - Prepared by - Reviewed by |

## KPI strip (row 5)
| Lowest funding position | Tightest lot | Closing at horizon | Lots with funding gap | First gap | Items on hold (memo) |

## Horizon: one to twelve months (setting)
The horizon is set in months (`horizon_months`, default **3**, so 2 or 3 is a settings change, not
a code change). It runs from the current lot to the end of the month `horizon_months - 1` after
the current one. With an as-of date of 23 Nov and 3 months, that gives 7 lots: 21-30 Nov,
three lots in Dec and three in Jan. With 2 months it gives 4 lots.

## Main grid
Columns: **A** line label, **B** source, then for each month **its lot columns followed by a
month-total column** (grey), and finally a **horizon total**.
- A month band above the lot headers names the month (for example "December 2026").
- The lot header shows the date range (for example `01-10 Dec`). The status row shows `ACTUAL - locked`,
  `CURRENT` (highlighted) or `FORECAST`. Locked lots are shaded grey.
- **Month totals**: flows are the sum of the month's lots. Opening is the first lot's opening.
  Closing, facility and funding position are the month's last lot. The gap is the worst lot of the month.
  If the current month starts mid-month, its total covers only the remaining lots and is marked `*`.
- **Horizon total**: flows are the sum of the month totals. The balances are the last month's figures,
  and the gap is the worst over the horizon.
- The month-total columns can be switched off with `show_month_totals`.
- When printed, the sheet is landscape (A3 when there are more than 6 lots), fits one page wide,
  and repeats the labels on every page.

| Section | Lines |
|---|---|
| **A. Opening cash** | Opening bank balance. The current lot takes the ERP total (other currencies at the manual rate). Each later lot takes the previous closing. |
| **B. Cash inflows** | One row per inflow category, in category display order and grouped by summary group, for example Customer collections, Additional collections, Bill discount proceeds, Other inflows. **Total inflows** |
| **C. Cash outflows** | One row per outflow category, for example Vendor PDCs, Vendor payment allocation, Bill discount / LC maturities, Payroll, Rent and utilities, VAT and taxes, Other outflows. **Total outflows** |
| **D. Net cash flow** | B - C |
| **E. Closing balance** | A + D |
| **F. Funding** | Bank facility available. **Funding position before holds** = E + facility. **Funding gap before holds** = MIN(0, funding position), shown in red. |
| **G. Cheque holds** | + PDCs put on hold (out of their cheque lot). - Held PDCs re-presented (in the lot of the next honouring date). = Net hold effect in the lot. Cumulative hold effect. **Closing balance after holds** = E + cumulative. **NET FUNDING POSITION AFTER HOLDS** = closing after holds + facility. **Shortfall after holds** = what is still to cover. **Are the holds sufficient?** shows *No gap*, *Covered by holds* or *NOT sufficient*. |
| **H. Memo (not in totals)** | Risk-adjusted collections excluded by the scenario, amounts deferred into the lot, and holds not re-presented within the horizon (open-ended, or dated after it). |

## Cheque holds
A hold is **our** decision to stop a PDC for a while. It is different from a defer, which is a
date agreed with the vendor and moves the cheque within the category rows.
1. In the PDC list, the user picks **Hold** from the Action drop-down. The app then asks for:
   - **Next honouring date**: required, unless *Open-ended* is ticked. It suggests cheque date + `hold_default_days` (10), plus quick picks for +10 days, the start of the next lot and the next month.
   - **Amount to hold**: the full cheque by default, or part of it.
   - **Reason**, for example "Await delivery note" or "Vendor dispute".
2. Rows B to F stay **as per ERP**, so the Vendor PDCs row still includes held cheques. Block G
   then takes the held amount out of the cheque's lot and puts it back in the lot of its honouring date.
   Funding is shown both before and after holds, so you can see whether the holds close the gap.
3. A hold can be **extended** (new date), **released** (the cheque is honoured on its own date)
   or **changed to part / full**. Each change keeps the previous version in the history and the audit log.
4. Warnings (advisory):
   - the honouring date is after the horizon
   - the honouring lot itself then goes into a gap (the problem has only moved)
   - the honouring date is more than `cheque_validity_days` (180) after the cheque date (the cheque may be stale, so confirm the period with your banks)
   - an open-ended hold has no date set
5. The **Hold register** lists vendor, cheque no, cheque date and lot, amount held, next honouring
   date and lot, days held, times extended, reason, who held it and any warning.

The category rows are never hard-coded. They come from the category table, so a newly mapped
category appears as a new row in its group.

## Bank position and ERP tie-out
| Bank | Account | Ccy | Balance (ccy) | Rate to OMR | Balance OMR |
Followed by:
- Total ERP bank balance (OMR)
- Model opening for the current lot, which equals the ERP total
- **Previous snapshot's forecast closing for today** compared with the ERP balance, giving a **variance** (forecast accuracy)
- Bank facility by bank: Limit, Utilised, Available

## Detail blocks
- **PDC detail**: Vendor, Lot, Cheque date, Cheque no, Voucher no, Amount, **Action** (Active / Hold / Deferred drop-down), and for held cheques **Hold amount, Next honouring date, Honour lot and Days held** (highlighted). Sorted by lot, then date. Each lot subtotal agrees with both the Vendor PDCs row and the "PDCs put on hold" row of the grid.
- **Bill discount / LC detail**: Lot, Maturity, Bank, Reference, Type (Discount proceeds / LC maturity), Amount, Status.
- **Commentary per lot**: template text such as "Lot 2 closes at X. The largest outflow is Y. The funding position is below the threshold by Z."

## Number format
`#,##0.000;[Red](#,##0.000);"-"`. Totals are bold with a top border. Closing and Funding position
have a double underline.
