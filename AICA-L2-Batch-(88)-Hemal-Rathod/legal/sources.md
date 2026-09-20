# Legal sources and verification record

**Period:** FY 2025-26 / AY 2026-27
**Governing statute:** Income-tax Act, 1961
**Research completed:** 18 September 2026
**Chartered Accountant sign-off:** pending — complete section 6

This file records where every legal parameter in `app/js/ruleset.js` came from, and what
was checked. Nothing in the engine rests on a language model's memory of the law.

---

## 1. Which Act governs FY 2025-26

The Income-tax Act, 2025 came into force on 1 April 2026 and applies from tax year 2026-27.
**Income of FY 2025-26 (AY 2026-27) remains governed by the Income-tax Act, 1961**, and
returns and audits for that year are made under the 1961 Act and its forms.

| Source | Type | What it confirms |
| --- | --- | --- |
| Income Tax Department e-filing portal — *Objective and scope of the new Act* | Official | New Act from tax year 2026-27; AY 2026-27 filed under the old Act; proceedings for earlier years continue under the 1961 Act (s. 536(2)(c) of the new Act) |

---

## 2. Primary sources read — Gazette text

### Finance Act, 2023 (Act 8 of 2023) — the last amendment to these sections

Read from the Gazette of India Extraordinary, pages 24–25. A copy used for the research
is in `_legal-research/Finance_Act_2023.pdf` beside this project.

| Section of FA 2023 | Amendment | In force | Effect in the engine |
| --- | --- | --- | --- |
| **s. 15** | Substitutes the **first proviso to s. 44AB**: *"this section shall not apply to a person, who declares profits and gains for the previous year in accordance with the provisions of sub-section (1) of section 44AD or sub-section (1) of section 44ADA"* | 1 April 2024 (AY 2024-25 onwards) | A presumptive declarant within the scheme is outside s. 44AB altogether |
| **s. 16** | Inserts provisos in **s. 44AD, Explanation, clause (b)**: ceiling ₹2 crore becomes **₹3 crore where cash received does not exceed 5% of total turnover**; non-account-payee cheques and drafts deemed cash | 1 April 2024 | Enhanced s. 44AD ceiling tested on **cash receipts against turnover only** |
| **s. 17** | Inserts provisos in **s. 44ADA(1)**: ₹50 lakh becomes **₹75 lakh where cash received does not exceed 5% of gross receipts**; non-account-payee cheques and drafts deemed cash | 1 April 2024 | Enhanced s. 44ADA ceiling tested on cash receipts against gross receipts |

### Finance (No. 2) Act, 2024

Full text searched. **No amendment to s. 44AB, s. 44AD or s. 44ADA.**

### Finance Act, 2025 (Act 7 of 2025)

Full text searched. **No amendment to s. 44AB, s. 44AD or s. 44ADA.** (Its only reference
to s. 44AB is in a search-assessment provision.)

It does fix the basic exemption used on the low-profit limbs:

| Provision | Rule | Used as |
| --- | --- | --- |
| s. 115BAC(1A)(iii), inserted by FA 2025 | Nil tax up to ₹4,00,000 for AY 2026-27 onwards | New-regime basic exemption — ₹4,00,000 |
| First Schedule, Part III | Nil tax up to ₹2,50,000 | Old-regime basic exemption — ₹2,50,000 |
| First Schedule, Part III | Higher nil slabs for resident individuals aged 60–79 and 80+ | ₹3,00,000 and ₹5,00,000 |

---

## 3. Consolidated statutory text — s. 44AB

Clauses (a) to (e) and the provisos to clause (a) predate 2023 and were not changed since.
Read from the consolidated Income-tax Act, 1961 (Indian Kanoon). This version still shows
the pre-2023 first proviso, which is why the Finance Act 2023 text above governs that
proviso.

| Clause | Rule | Engine parameter |
| --- | --- | --- |
| (a) | Business turnover exceeds ₹1 crore | `business44AB.baseLimit` |
| Provisos to (a) | ₹10 crore where cash received ≤ 5% of **all amounts received** AND cash paid ≤ 5% of **all payments**; non-account-payee cheques and drafts deemed cash | `enhancedLimit`, `cashReceiptPct`, `cashPaymentPct` |
| (b) | Professional gross receipts exceed ₹50 lakh | `profession44AB.limit` |
| (c) | s. 44AE / 44BB / 44BBB income declared lower than deemed | special condition |
| (d) | s. 44ADA applies, lower profit declared, **and income exceeds the maximum amount not chargeable** — **no prior-year condition** | `evaluateProfession` |
| (e) | s. 44AD(4) applicable and income exceeds the maximum amount not chargeable | `evaluateBusiness` |

Where the fetched text had gaps, the tool marks them `[...]` in the reference cards rather
than completing them from memory.

---

## 4. Other official and professional sources

| Source | Type | What it confirms |
| --- | --- | --- |
| e-filing portal — ITR-4 FAQ | Official | s. 44AD: resident individual, HUF, firm (not LLP). **s. 44ADA: resident individual or firm (not LLP) — an HUF is not eligible** |
| s. 44AD(1), as amended by Finance Act 2017 | Statute, via professional commentary | 6% on turnover received by account-payee cheque / draft / ECS during the year or before the s. 139(1) due date; 8% on the rest |
| ICAI Guidance Note on Tax Audit u/s 44AB (Revised 2026, 11th edition), as reported in professional commentary | Professional | During a s. 44AD(4) bar, audit applies in each barred year where total income exceeds the basic exemption, **whatever the turnover**. The 5% cash test under s. 44AB(a) uses total receipts and total payments, not turnover |
| Due-date reporting, 16 September 2026 | Commentary | Audit report due 30 September 2026 (31 October for transfer pricing cases); return 31 October (30 November for TP). **No CBDT extension reported as at 16 September 2026** |

**Not directly verified:** the ICAI Guidance Note itself (the PDF was not retrievable) and
the verbatim text of s. 44AD(4) and (5). The engine follows the reading those sources
describe, and the reference cards say where text was not reproduced.

---

## 5. Errors this verification found in the earlier engine

These were present in the version before 18 September 2026 and are now corrected. Each has
a regression test in `tests/boundary-suite.js`.

| # | Earlier behaviour | Correct position | Risk |
| --- | --- | --- | --- |
| E1 | First proviso to s. 44AB not modelled | 44AD / 44ADA declarants are outside s. 44AB (FA 2023 s. 15) | Said APPLICABLE where audit was not required |
| E2 | ₹3 crore s. 44AD ceiling gated on both cash limbs | Cash **receipts** against **turnover** only (FA 2023 s. 16) | Wrong ceiling |
| **E3** | **s. 44AB(d) required prior-year use of s. 44ADA** | **No such condition in clause (d)** | **Said NOT APPLICABLE where audit was required** |
| E4 | An HUF allowed to use s. 44ADA | Individual or non-LLP firm only | Wrong eligibility |
| E5 | 44AD deemed at a single 6% or 8% rate on all turnover | 6% on banking-channel turnover, 8% on the rest | Wrong deemed income |
| **E6** | **s. 44AD(4) five-year bar not modelled** | **Audit in every barred year where income exceeds the exemption** | **Said NOT APPLICABLE where audit was required** |
| E7 | Audit report date 30 Sep for TP cases | 31 October 2026 for TP cases | Wrong date |
| E8 | Nil receipts made the cash test "not computable" | Nil cash does not exceed 5% of nil — test met | Stalled instead of deciding |

**E3 and E6 matter most:** both could lead to advising a client that no audit was needed
when it was.

---

## 6. Chartered Accountant sign-off

Once you are satisfied with sections 1 to 5, complete this table and the `caSignOff` block
in `app/js/ruleset.js`. The application then shows your name as the signatory.

| Item | Checked by | Date | Remarks |
| --- | --- | --- | --- |
| Governing Act for FY 2025-26 | | | |
| s. 44AB clauses (a)–(e) and provisos | | | |
| First proviso to s. 44AB (FA 2023 s. 15) | | | |
| s. 44AD ceiling and deemed rates | | | |
| s. 44ADA ceiling, deemed rate, eligible persons | | | |
| s. 44AD(4) bar — interpretation adopted | | | |
| Basic exemption limits | | | |
| Due dates, including any CBDT extension | | | |

---

## 7. When to re-verify

- A Finance Act or Taxation Laws (Amendment) Act is passed
- CBDT extends a due date — **check before 30 September 2026**
- A new Assessment Year block is added — AY 2027-28 onwards falls under the **Income-tax
  Act, 2025** and needs a new engine, not just new numbers
- A court or the ICAI changes the settled reading of a limb
