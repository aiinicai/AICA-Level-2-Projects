# Decision engine architecture

## Layers

```
ruleset.js     every threshold, rate and date for AY 2026-27, with its source
calc.js        arithmetic — including cashWithin(), the statutory 5% test
validation.js  arithmetic impossibilities (errors) and unusual figures (cautions)
engine.js      one path for business, one for profession; each limb a test record
reasoning.js   reasoning chain, conclusion, reference cards (statutory text + source)
workingpaper   one document model → screen, PDFs, Word, audit trail
ui.js          DOM only
```

No numeric legal limit exists outside `ruleset.js`.

---

## Outcomes

| Status | When |
| --- | --- |
| **APPLICABLE** | A limb of s. 44AB triggers, and the first proviso does not apply |
| **NOT APPLICABLE** | No limb triggers, or income is declared under s. 44AD(1) / 44ADA(1) (first proviso) |
| **INFORMATION REQUIRED** | A fact needed on this path is missing, or a figure is impossible |

There is no "cannot conclude" outcome. Every fact the law turns on is asked as a question, so
once the answers are in, a decision follows.

---

## Asking only what matters

Each requirement is raised only where it can change the answer. The shortcuts are strict
bounds:

| Field | Asked only when | Why the bound holds |
| --- | --- | --- |
| Cash receipts / payments and totals | ₹1 cr < turnover ≤ ₹10 cr | At or below ₹1 cr neither limit is crossed; above ₹10 cr both are |
| Cash received (44AD ceiling) | ₹2 cr < turnover ≤ ₹3 cr, and eligible | Below ₹2 cr within either ceiling; above ₹3 cr outside both |
| Non-banking turnover | 6% ≤ profit / turnover < 8% | Deemed income always lies between 6% and 8% of turnover |
| Prior s. 44AD use | Profit below deemed and income above the exemption | Otherwise s. 44AB(e) cannot trigger |
| Declaring under the scheme | The limit is crossed and the scheme is available with profit meeting the deemed income | Otherwise the choice does not change the result |
| Profession cash received | ₹50 lakh < receipts ≤ ₹75 lakh | Same logic as the 44AD ceiling |

**Decisive grounds.** Once a limb triggers and nothing unanswered could bring in the first
proviso — the scheme is unavailable, or profit is below the deemed income — the result is
APPLICABLE at once. Unanswered questions become a note ("further grounds not examined").

---

## Business path

1. s. 44AB(a) — cash test decides ₹1 cr or ₹10 cr limit; turnover compared.
2. s. 44AB(c) — ticked condition.
3. s. 44AD eligibility — constitution, residence, exclusions.
4. s. 44AD ceiling — ₹2 cr, or ₹3 cr where cash received ≤ 5% of turnover.
5. s. 44AD(4) bar — if barred, s. 44AB(e) where income exceeds the exemption.
6. Deemed income — 8% × non-banking turnover + 6% × rest.
7. Opt-out — profit below deemed, prior use in AY 2021-22 to 2025-26, income over exemption → s. 44AB(e).
8. First proviso — declaring under s. 44AD(1) → s. 44AB does not apply.

## Profession path

1. s. 44AB(b) — gross receipts over ₹50 lakh.
2. s. 44ADA eligibility — resident individual or non-LLP firm, s. 44AA(1) profession.
3. s. 44ADA ceiling — ₹50 lakh, or ₹75 lakh where cash received ≤ 5% of gross receipts.
4. s. 44AB(d) — profit below 50%, income over exemption. **No prior-year condition.**
5. First proviso — declaring under s. 44ADA(1) → s. 44AB does not apply.

---

## Test record

```js
{ id, kind: 'limb' | 'condition', label, provision, inputValue, thresholdLabel,
  status,   // limb: triggers | clear | excluded | na | pending
            // condition: met | not-met | na | pending
  reason, detail }
```

The reasoning chain, matrix, reference cards, working paper and audit trail are all rendered
from these records — no output can disagree with another.

---

## Boundary conventions

- "Exceeds" is strictly greater than: a figure equal to a limit does not exceed it.
- "Does not exceed 5%": exactly 5.00% passes. Compared as cash ≤ 5% × total in integer paise,
  so a nil total with nil cash passes.

Both are covered by tests at the limit, one rupee above and one rupee below.
