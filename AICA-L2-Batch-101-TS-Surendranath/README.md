# AI-Assisted Year-End Adjustment Tracker with Automatic Income Tax Recomputation

**AICA Level 2 — Capstone Project**
Author: CA T S Surendranath · Batch AICA-L2B101, Chennai (Online 10–11 Oct 2026, Physical 12–14 Oct 2026)

▶️ **Video presentation:** https://youtu.be/NVxZDCeZm5c

---

## The problem
During year-end finalisation, many adjustments are passed after the draft accounts are ready: management entries, audit observations and final closing entries. Each one changes profit, and so it changes:
- the income tax computation (disallowances u/s 43B, 40(a)(ia), 36(1)(vii), 37),
- current tax and the provision for tax,
- deferred tax under AS 22.

When all of this is redone manually, much time is lost, and the final financial statements often do not agree with the final tax computation.

## The solution
A single Excel model in which **each adjustment is entered once**. Everything else updates automatically:

```
Trial Balance → Adjustment Register → Adjusted TB → P&L & Balance Sheet
                       │                                  │
                       └──► Tax Computation ◄──── PBT ────┘
                                  │
                       Current tax + Deferred tax ──► back to P&L & BS
                                  │
                         10 Reconciliation Checks → ALL OK
```

## How AI was used
| Stage | AI tool used for |
|---|---|
| Tax classification | Classifying each entry as Allowable / 43B / 40(a)(ia) / Provision / Permanent / Book depreciation |
| Ledger mapping | Mapping ledgers to Schedule III lines |
| Formula building | SUMIFS, INDEX-MATCH and the impact-on-profit formula |
| Check design | Listing the reconciliation checks between the accounts and the tax computation |
| Communication | Plain-language notes explaining changes to clients |

All prompts are in the `AI_Prompts` sheet. Every AI suggestion was verified by the author.

### Live AI demonstration
The video shows four last-minute entries being classified **live by two different models in the ICAI AI Agent (GPT-6.1 Sol and Gemini 3.8 Flash)**, including two that test the AI's judgement (interest on late GST, and a political donation by a company under s.115BAA, where s.80GGB is not available). Both models answered correctly; the CA verified each answer against the Act, the entries are switched on in the register (Include = Y), and the whole model recomputes instantly. See the `AI_Live_Demo` sheet.

> **AI assists; the CA decides.**

## Results (dummy company, 12 adjustments, 3 versions)
| Item | Amount (₹) |
|---|---|
| PBT before adjustments | 72,00,000 |
| PBT after adjustments | 47,75,000 |
| Total income | 63,70,000 |
| Current tax @ 25.168% (s.115BAA) | 16,03,200 |
| Deferred tax credit | (3,24,667) |
| Reconciliation checks | 10 / 10 OK |
| Time per revision | ~160 min → ~16 min (illustrative) |

## Files
| File | Description |
|---|---|
| `YearEnd_Tax_Recompute_Model.xlsx` | Working model: 11 sheets, including AI_Live_Demo |
| `Project_Report.pdf` / `.docx` | Full project report |
| `check_model.py` | Python script: independent recomputation of profit and tax, compared with Excel |
| `Video_Script.md` | Script for the video presentation |

## How to try it
1. Download `YearEnd_Tax_Recompute_Model.xlsx` and open it in Excel.
2. Go to **Adjustments** and change *Include?* for any entry from `Y` to `N`.
3. Watch **Financial_Statements**, **Tax_Computation** and **Checks** update instantly.

## Responsible AI
No confidential, personal or client information was entered into any AI platform. All data is dummy data, as required by ICAI.

Claude (Anthropic) was used as an AI assistant to help design the Excel model, write the Python script and draft the report; all output was reviewed and finalised by the author.

## Python cross-check
```
pip install openpyxl
python check_model.py
```
Recomputes PBT, total income, current tax and deferred tax independently and prints MATCH / MISMATCH against the Excel model.

## Note
The figures are for FY 2025-26 (AY 2026-27) under the Income-tax Act, 1961. From FY 2026-27 the Income-tax Act, 2025 applies with new section numbers. All data is dummy. AI output must always be verified by a qualified professional.
