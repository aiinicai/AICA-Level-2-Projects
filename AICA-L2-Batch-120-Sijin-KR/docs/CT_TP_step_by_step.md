# AuditSignOff Suite UAE - Partner/Manager Review Automation – CT and TP: step by step

## A. Corporate Tax (CT) – working sheet and review

| Step | Action | Where | Pass test |
|---|---|---|---|
| 1 | Use the CT working-sheet layout supplied as `samples/ct_demo_locked.xlsx` (blue cells are inputs; formulas are locked). Save a copy per client: `CT_<Client>_FY.xlsx` | Excel | Sheet names 01-14 and 22 present |
| 2 | Sheet 01–03: client, period, FS profit, free-zone/QFZP/SBR status | Excel | No blank mandatory cell |
| 3 | Sheet 04: enter exempt income and non-deductibles as **positive** amounts (the sheet takes the absolute value) | Excel | 04!D14 = sum of all items |
| 4 | Sheet 07 (TP schedule): per row enter related-party value (D), arm's-length value (I) and **Direction** (K: Income/Expense). Leave I blank if not benchmarked | Excel | Column L shows no ⚠ |
| 5 | Take the TP adjustment from the TP review paper (conclusion, TP-50) – it must be a **quantified AED figure** and equal the 07 total | Excel | 07 total = report figure |
| 6 | Save in Excel (so values are cached), close the file | Excel | – |
| 7 | App → **Corporate tax** tab: upload working sheet; optional: return figures, FS pack, TP adjustment, filing date → **Run** | Streamlit | – |
| 8 | Read the review paper: CT-01…CT-10 (recompute, bridge, TP carry-through, return tie-out, interest cap, losses 75%, late-filing penalty) | DOCX/XLSX | No High exception open |
| 9 | Fix the sheet, re-run until clean; keep the JSON audit trail (SHA-256 of inputs) | File | – |

## B. Transfer pricing (TP) – before CT

| Step | Action | Where | Pass test |
|---|---|---|---|
| 1 | Fact sheet (any format; or Pre-fill from licence/MOA): name, authority, shareholders, signatories, FY | Pre-fill tab | Conflicts resolved |
| 2 | **Transfer pricing** tab: upload report (Word preferred; PDF/scan accepted), benchmarking workbook (%-PLI cases), optional audited FS and CT sheet | Streamlit | – |
| 3 | Run. Read exceptions by severity. NOT RUN = input missing (never a pass) | DOCX/XLSX | – |
| 4 | Clear every High: unfinished text (TP-73), DRAFT (TP-75), year (TP-03), range recomputed (TP-46), funnel (TP-36), regions (TP-76), adjustment quantified (TP-50), annexures printed (TP-25) | Report | – |
| 5 | Partner decisions on grey areas: quartile method (INC vs EXC), adjust to median vs range edge, role/size comparability | Partner | Recorded in the paper |
| 6 | Carry the final adjustment to CT sheet 07 → section A step 5. Re-run TP with the CT sheet attached: TP-51 ties report ↔ CT | Both | TP-51 passes |

## C. New TP checks learned from the ABC COMPANY sample (KMP remuneration, PDF)

| ID | What it catches | Result on sample |
|---|---|---|
| TP-73 | XXXXXX licence no.; "issued on January" (no year) | Exception |
| TP-74 | "Mr. Mr. XYZ / SRK" | Exception |
| TP-75 | DRAFT watermark (also overprints headings) | Exception |
| TP-03 | Body FY 2024 vs engagement FY | Exception (depends on fact sheet) |
| TP-46 | Q1/median/Q3 and count recomputed from the report's own table (AED or %) | Pass – 1,103,333 / 1,525,809 / 2,775,669 agree (QUARTILE.INC) |
| TP-36 | Funnel 63−36=27 ok; but "search results of 36" vs 63; 27 executives from only 16 companies | Exception |
| TP-76 | Narrative says MENA/Turkey; all 27 are European listings | Exception |
| TP-37 | 9 CFO/secretary/division roles for an MD benchmark; 2 "Prior Board"; 577× revenue spread | Exception (Class B – judgement) |
| TP-50 | Actuals 20.4m each = 13× median; adjustment not quantified (excess to median 37.8m) | Exception |
| TP-11 | Three authority names (DIEZ / DSOA / IFZA); SRK not a signatory; corporate sole shareholder, UBO not stated | Exception |
| TP-25 | Annexures only as an embedded zip icon; "Annexure A" does not exist | Exception |
| TP-01/02/03 | Cover is a picture | Not run (needs Word or visual check) |

Manual (not automated): AI-generated cover picture with garbled text; Executive-summary header "Arm's Length Margin/Range" over AED salaries; "intentionally left blank" pages; TOC alignment.

Grey areas to settle: (1) quartile method; (2) median vs nearest range edge for the adjustment; (3) whether executive-pay benchmarks from listed multinationals are reliable for a small LLC; (4) characterisation of excess pay (salary vs distribution) – Arts. 28/34/36 CT Law.
