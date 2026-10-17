# Validation results — 16 October 2026

- `python -m unittest discover -s ITR_Regime_Assistant -v`: **35 test methods passed**, including parameterised subcases.
- Source compilation: passed.
- `app.py` import with customtkinter 5.2.2: passed.
- Excel working paper generated in a temporary directory, reopened and checked for eight sheets and literal treatment of formula-like input: passed.
- Optional API adapter: mocked completed response, incomplete response and missing-credentials cases passed. No live request was made.

Tests cover new slabs, resident age bands, old/new rebate edges, new marginal relief and its end, nearest-ten rounding including refund signs, salary deduction limits, HRA metro/nonmetro/no-rent cases, deduction caps, senior interest deductions, GTI restriction, property loss blocking, unsupported scope gates, invalid amounts/year/age/types, surcharge exclusion, credit independence, scenario immutability, anonymised prompts, and all five sample profiles.

A test expectation initially specified nine report sheets; the implemented and documented report has eight. The expectation was corrected and the full suite passed.

## Illustrative expected results

| Example | Old tax | New tax | Numeric preference |
|---|---:|---:|---|
| Salary rebate | 187,200 | 0 | New |
| HRA/deduction case | 202,800 | 295,100 | Old, difference 92,300 |
| Marginal relief | 190,320 | 10,400 | New |
| Senior pension/interest | 89,440 | 0 | New |
| Capital-gains declaration | Blocked | Blocked | Specialist review |

Amounts are rupees, before excluded interest/fees/reliefs. Examples are fictional and not a statutory certification.

## Still requiring user trial

The Linux environment has no graphical display, so interactive window layout/clicks and Windows batch installation were not run here. Run `install.bat`, then `run.bat`, open examples 01–05 and export a fictional workbook on Windows. Confirm the AI prompt and draft flow using your own approved account if desired. No live portal integration exists.
