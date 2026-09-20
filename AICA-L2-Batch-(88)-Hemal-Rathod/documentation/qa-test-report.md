# QA test report

**Application:** Tax Audit Applicability Decision System
**Law:** Income-tax Act, 1961 — FY 2025-26 / AY 2026-27, as amended up to the Finance Act 2025
**Run:** 18 September 2026

---

## Result

| Group | Assertions | Pass |
| --- | --- | --- |
| Sample cases (12) | 12 | 12 |
| Your test data — the case that failed before | 5 | 5 |
| s. 44AB(a) boundaries | 11 | 11 |
| First proviso — s. 44AD (Finance Act 2023) | 7 | 7 |
| s. 44AD deemed income (6% / 8%) | 6 | 6 |
| s. 44AB(e) and the s. 44AD(4) bar | 7 | 7 |
| Profession — s. 44AB(b), (d), 44ADA, first proviso | 17 | 17 |
| s. 44AD exclusions and s. 44AB(c) | 6 | 6 |
| Flow and validation | 4 | 4 |
| Forms and due dates | 5 | 5 |
| Visual modes | 3 | 3 |
| **Total** | **83** | **83** |

| Document check | Result |
| --- | --- |
| Executive one-pager, all 12 cases | 12 / 12 on one A4 page |
| Detailed working paper | 6 pages |
| Word document — page setup, header, footer, page fields, 10 sections, statutory source | Present |
| Console errors | None |

---

## How to run it

1. Open `app/index.html` in a browser.
2. Open the developer console.
3. Paste the contents of `tests/boundary-suite.js` and press Enter.

Expected values were worked out from the provisions — the Finance Act 2023 Gazette text and
the consolidated s. 44AB — not recorded from the engine.

---

## Your test data

The screenshot case: turnover ₹1,00,00,000; total and cash receipts and payments all ₹0;
profit and total income ₹5,00,000.

| Step | Before (earlier engine) | Now |
| --- | --- | --- |
| As entered | REVIEW REQUIRED — "limbs could not be concluded" | **One question**: is the year within a s. 44AD(4) bar? |
| Nil receipts / payments | Cash test "not computable" | Cash test met — nil does not exceed 5% of nil |
| Bar = No | — | One question: was s. 44AD used in AY 2021-22 to AY 2025-26? (profit 5% is below the 6% floor; income exceeds ₹4 lakh) |
| Prior use = No | — | **NOT APPLICABLE** |
| Prior use = Yes | — | **APPLICABLE — s. 44AB(e) with s. 44AD(4)** |

---

## Boundaries — every limit at, one rupee above and one rupee below

| Limit | At | +₹1 | −₹1 |
| --- | --- | --- | --- |
| ₹1 crore (s. 44AB(a)) | Not applicable | Applicable where cash > 5% | — |
| ₹10 crore (s. 44AB(a)) | Not applicable | Applicable | Not applicable |
| 5% cash receipts / payments | 5.00% keeps ₹10 crore | 5.01% drops to ₹1 crore | — |
| ₹3 crore (s. 44AD) | Declaring → not applicable | Outside 44AD → applicable | — |
| 5% of turnover (s. 44AD ceiling) | — | 5.01% → ₹2 crore ceiling | — |
| 6% / 8% deemed (s. 44AD) | Exactly 8% meets without split | — | ₹1 below 6% fails without split |
| ₹50 lakh (s. 44AB(b)) | Not applicable | Asks whether declaring under 44ADA | — |
| ₹75 lakh (s. 44ADA) | Declaring → not applicable | Applicable | — |
| 50% (s. 44ADA) | Exactly 50% → not applicable | — | Below → s. 44AB(d) |
| ₹4,00,000 exemption | Barred, income exactly ₹4L → not applicable | ₹4,00,001 → applicable | — |

---

## Regression tests for the errors found by legal verification

| Error | Test | Result |
| --- | --- | --- |
| E1 First proviso not modelled | ₹2.5 crore trader declaring under 44AD → not applicable | Pass |
| E2 44AD ceiling on both cash limbs | Cash payments 12% do not block the ₹3 crore ceiling | Pass |
| **E3 s. 44AB(d) gated on prior use** | Professional below 50%, no prior use → **applicable** | Pass |
| E4 HUF allowed s. 44ADA | HUF below 50% → not applicable (no 44ADA) | Pass |
| E5 Single deemed rate | Deemed = 8% × non-banking + 6% × rest | Pass |
| **E6 s. 44AD(4) bar not modelled** | Barred, ₹40 lakh turnover, income over exemption → **applicable** | Pass |
| E7 TP audit report date | 31 October 2026 | Pass |
| E8 Nil receipts stalled | Nil receipts → cash test met | Pass |

---

## What these tests do not establish

- **That the parameters are the law.** The suite proves the engine applies `ruleset.js`.
  The law behind `ruleset.js` is recorded in `legal/sources.md`, and CA sign-off is pending.
- **That the conservative reading of the s. 44AD(4) bar is the only reading.** See L-01.
- **Anything about s. 44AA**, which is not evaluated.
