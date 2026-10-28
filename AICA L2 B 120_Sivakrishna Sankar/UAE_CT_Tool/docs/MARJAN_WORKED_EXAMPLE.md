# Worked example - Marjan Gulf Trading LLC (sample)

Fictional company. Trial balance in AED for the year ended 31 December 2025: `sample_data/marjan/Marjan_Gulf_Trading_TB_31Dec2025.xlsx`
(45 accounts + a balancing opening retained earnings line; debits = credits = AED 30,042,000.00; profit before tax AED 2,990,000).

Load it in the tool (Step 1: AED, period 2025-01-01 to 2025-12-31; Step 2: this file). To skip typing the questionnaire, use the CLI:

```
python -m ct_tool.cli analyse --tb sample_data/marjan/Marjan_Gulf_Trading_TB_31Dec2025.xlsx --currency AED ^
  --period-start 2025-01-01 --period-end 2025-12-31 --answers sample_data/marjan/Marjan_answers.json --out out
```
(add `--decisions sample_data/marjan/Marjan_decisions_ILLUSTRATIVE.json` to confirm the five proposals as in the example below; without it nothing is confirmed.)

## Assumptions I made (change them if wrong - they are in `Marjan_answers.json` / the questionnaire)
- Mainland LLC, subsequent tax period, IFRS, accrual basis, draft/unaudited, not part of an MNE group, no opening tax losses.
- No realisation-basis election; no Small Business Relief; not a Qualifying Free Zone Person.
- Dividend from Marjan Logistics FZE: 100% owned, cost AED 1.5m, held 36 months, subject to tax - so the participation-exemption conditions are *answered as met* (the tool does not verify them).
- Donations were not all to Qualifying Public Benefit Entities; no staff-only entertainment; no part of the fines is compensation for damages.

## What was planted, and what the tool does with it
| Account | AED | Treatment in the example | Status in the tool |
|---|---|---|---|
| 4200 Dividend income - subsidiary | 400,000 | exempt (participation exemption), deducted | proposed, then confirmed |
| 6020 Client entertainment | 140,000 | 50% restricted: add back 70,000 | proposed, then confirmed |
| 6030 Donations | 75,000 | not to a QPBE: add back | proposed, then confirmed (reviewer note needed) |
| 6040 Fines and penalties | 28,000 | add back | proposed, then confirmed |
| 6140 Director personal expenses | 42,000 | add back | proposed, then confirmed (reviewer note needed) |
| 4300 Unrealised FV gain 120,000 / 6090 impairment 95,000 | - | no election, so no adjustment (scope A election would deduct 120,000 and add back 95,000: taxable income 2,780,000) | information / technical review item |
| 6120 Management fee, 2200 shareholder loan, 6070 interest, 1200 due from related party | - | flagged as related-party items (arm's-length support needed); not adjusted | high-risk flag, open item |
| 6150 Marketing 220,000, 6050 Professional fees, 6100 Repairs | - | business-purpose / capital-nature review | information required |

## Hand calculation (done independently of the tool)
| | AED |
|---|---|
| Accounting profit | 2,990,000 |
| Less: exempt dividend | (400,000) |
| Add: 50% of client entertainment | 70,000 |
| Add: donations | 75,000 |
| Add: fines and penalties | 28,000 |
| Add: director personal expenses | 42,000 |
| **Taxable income** | **2,805,000** |
| Tax: 9% x (2,805,000 - 375,000) | **218,700** |

Net interest is 150,000 - 35,000 = 115,000, far below the AED 12m limit. Revenue (19.5m) exceeds the AED 3m Small Business Relief threshold.
Before anything is confirmed the tool shows taxable income AED 2,990,000 and tax AED 235,350 (all five proposals are *pending*, not applied).

`tests/test_marjan.py` checks all of the above, including variants (staff entertainment 50% -> 2,770,000; compensation element in fines -> 2,797,000;
all donations to QPBEs -> 2,730,000; dividend held only 6 months -> 3,205,000; AED 1m opening losses -> 1,805,000) and that the recalculated Excel formulas agree.

**These are figures produced by the configured rules, several of which are marked UNVERIFIED (see Help > Tax rules). Confirm each rule against the legislation before using the method on a client file.**
