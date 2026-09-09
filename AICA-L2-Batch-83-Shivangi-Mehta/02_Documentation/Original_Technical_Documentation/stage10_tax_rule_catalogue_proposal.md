# Stage 10 — Proposed Tax Rule Catalogue + Source Verification Register

**Status: PROPOSAL ONLY. No code written. No `TaxRule` row activated. Nothing in this
document executes.** Per your explicit instruction, this is produced *before* any Tax
rule is coded, for your review and approval. Every rule below either carries a primary-
source verification for its core legal citation, or is explicitly marked
`SOURCE_VERIFICATION_REQUIRED` and will not be implemented as executable until further
verified — the existing structural gate already built into FinSight
(`rule_runner_service.get_runnable_accounting_rules()` / `get_runnable_audit_rules()`,
which filter on `verification_status == "VERIFIED"`) will be reused unchanged for Tax
rules; this document does not propose any change to that mechanism.

This catalogue was produced by dispatching five independent research passes (one per
required review area below), each using live web search against primary sources
(incometaxindia.gov.in, incometax.gov.in, egazette-hosted Finance Bill/Act text, CBDT
notifications) wherever possible, with secondary sources (ClearTax, TaxGuru, ICAI-
adjacent commentary) used only for cross-checking, never as the sole basis for a
`VERIFIED` status. Every rule states its source(s) and is honest about which claims
rest on primary text and which do not.

---

## 0. Critical background you need before reviewing this catalogue

**India's income-tax law is mid-transition between two Acts right now.** The
Income-tax Act, 2025 (Act No. 30 of 2025) came into force on **1 April 2026**,
repealing the Income-tax Act, 1961 from that date — confirmed directly from CBDT's own
"FAQs on Interplay and Transition to the Income-tax Act, 2025"
([incometaxindia.gov.in](https://www.incometaxindia.gov.in/documents/81799/11848482/FAQs-on-Interplay-and-Transition.pdf/05f80c1a-073c-a5d7-fb6f-55509242be53?t=1774082865717))
and the official press release on the same site.

Concretely, as of today (24 August 2026), **both regimes are simultaneously relevant**:

- **FY 2025-26 (Assessment Year 2026-27)** — the year whose tax audit report is due
  **30 September 2026**, i.e. the audit work FinSight would actually be used for right
  now — remains governed by the **old 1961 Act**, old section numbers, Form
  3CA/3CB/3CD.
- **FY 2026-27 (Tax Year 2026-27)**, already underway, is governed by the **new 2025
  Act**, which renumbers nearly every section, and (per multiple, though not fully
  primary-confirmed, sources) replaces Form 3CA/3CB/3CD with a new consolidated
  "Form 26."
- For TDS specifically, the applicable Act is determined transaction-by-transaction by
  the "earlier of credit or payment" event date relative to 31 March 2026 (confirmed
  verbatim from an incometax.gov.in FAQ) — so a single engagement's FY2025-26 data can
  contain transactions governed by two different Chapter/Section regimes depending on
  when TDS was actually triggered, if the engagement's year-end doesn't align with the
  Act cutover (it does, for a standard April–March FY2025-26 engagement — flagging this
  only because it would matter for a non-standard accounting year).

**A design decision I need your approval on, before any of this is coded:**
research consistently found the **old Act 1961 section numbers, thresholds and
mechanisms are independently confirmable against primary .gov.in text**, but the **new
Act 2025's section numbers are not yet reliably confirmable** — every research pass
that tried found either a single secondary source, or conflicting secondary sources,
for the new numbering (e.g., three sources put Section 40A(2) at three different new
section numbers). No official CBDT section-concordance table was found.

My proposal: **verify and gate each rule against the old Act 1961** (since that is what
governs the audit work actually due right now), and carry the researched new-Act-2025
section number as a **clearly labeled, non-gating, "unverified forward reference"**
field on each rule — visible to a reviewer, never asserted as confirmed, and never
blocking that rule's `VERIFIED` status once the old-Act citation itself is
primary-sourced. The rationale: a rule's actual analytical test (a threshold, a
payment-mode check, a date comparison) doesn't change depending on what the section is
*numbered* — only on what the underlying rule *is*. If you'd prefer every rule to stay
`SOURCE_VERIFICATION_REQUIRED` until the new-Act number is also pinned down, that's a
one-line policy change on my end and doesn't touch any rule's substance — flagging this
explicitly rather than deciding it silently, per your standing instruction.

---

## 1. How `VERIFIED` was decided (methodology, not a shortcut)

A rule's core legal citation is marked **`VERIFIED`** only where the research pass
directly fetched and quoted primary text from an official Income Tax Department page
(incometaxindia.gov.in / incometax.gov.in) or an official Finance Bill/Act PDF hosted
there, with no conflicting figures found elsewhere. Where the only support was
secondary commentary — even multiple, mutually consistent secondary sources — the item
is marked **`SOURCE_VERIFICATION_REQUIRED`**, explicitly, even if the figure is very
likely correct. This is a deliberately more conservative bar than "several blogs agree"
— per your instruction that an unverified rule must not execute, I'd rather over-flag
than under-flag.

A rule's **Form 3CD clause number**, where cited, is *always* marked
`SOURCE_VERIFICATION_REQUIRED` regardless of the rule's own status — clause numbering
was found to shift across CBDT amendment notifications, no primary Form 3CD/Rule 6G PDF
was directly fetched in this pass, and the clause number is *additive reporting
metadata*, not something the rule's own analytical test depends on to run. A rule can
therefore be `VERIFIED` for its substantive threshold/test while its 3CD clause
citation remains unconfirmed.

---

## 2. The catalogue

### A. Income-tax Analytical Review

---
**TAX-RPT-004 — Related-Party Payment Reasonableness Screen**
- **Provision/section:** Section 40A(2), Income-tax Act, 1961 (disallowance of
  expenditure to a "specified person" that the Assessing Officer considers excessive or
  unreasonable, having regard to fair market value / legitimate business need).
  "Specified person" broadly includes relatives, and persons/entities with a
  substantial interest (≥20% voting power or ≥20% profit share).
- **New Act 2025 (unverified forward reference):** not confirmed — three independent
  secondary sources gave three different section numbers (36 / 40 / split across
  29+32+36). Treat as unresolved.
- **FY/AY:** FY 2025-26, Assessment Year 2026-27 (old Act; current audit cycle).
- **Effective date:** Long-standing provision, no recent threshold change found.
- **Source:** [Section 40A — incometaxindia.gov.in](https://www.incometaxindia.gov.in/w/section-40a-9)
  (primary text fetched directly).
- **Applicability:** Any engagement with related-party expense transactions — no
  turnover/entity-type gate.
- **Data required:** `GL`/`JE`/`AP` rows with `account_name`/`description`/party
  identification; the related-party candidate list already produced by Audit's
  `detect_related_party_candidates()` (reused, not reimplemented).
- **Test:** Flag related-party candidate transactions that are **expense-side** (a
  payment *by* the entity, not a receipt) for professional reasonableness review. This
  is inherently **not a computable disallowance** — Section 40A(2) is a
  fact-and-judgment test against market value, which FinSight has no external
  market-rate data to compare against.
- **Limitation:** Produces a *candidate list for inquiry*, not a disallowance
  computation or a conclusion that any amount is unreasonable. Overlaps by design with
  Audit's AUD-RPT-006 (related-party candidate detection) — this rule reuses the same
  detector on the same data, filtered to the expense side, and should be presented to
  the reviewer alongside AUD-RPT-006's findings rather than as a wholly separate signal.
- **Suggested query:** "Please confirm this related-party payment reflects an
  arm's-length/market rate, and provide supporting benchmarking if available."
- **Verification status:** **VERIFIED** (old Act 1961 citation; new-Act number
  unresolved, non-gating).

---
**TAX-DIS-006 — Statutory Dues Payment-Basis Timing Test**
- **Provision/section:** Section 43B(a)–(f), Income-tax Act, 1961 — deduction for
  certain expenses (tax/duty/cess, employer PF/ESI/gratuity/welfare-fund contributions,
  bonus/commission under 36(1)(ii), interest on specified institutional/NBFC/bank
  loans, leave encashment) allowed only in the year of **actual payment**, not accrual
  — subject to the proviso allowing payment up to the return-filing due date to still
  count for that year (this proviso does **not** extend to clause (h)/MSME, see
  TAX-MSME-013 below).
- **New Act 2025 (unverified forward reference):** Section 37 — cross-checked across
  two independent secondary sources (TaxGuru, CACLubIndia), consistent, but not
  primary-confirmed.
- **FY/AY:** FY 2025-26, AY 2026-27 (old Act).
- **Effective date:** Long-standing provision.
- **Source:** [Section 43B — incometaxindia.gov.in](https://www.incometaxindia.gov.in/w/section-43b-42)
  (primary text fetched directly, full clause list confirmed).
- **Applicability:** Any engagement with GL/JE entries for statutory dues, PF/ESI,
  bonus, or specified interest.
- **Data required:** `GL`/`JE`/`TB` rows tagged to statutory-due account types;
  accrual date and payment date for each.
- **Test:** For each identified statutory-due accrual, check whether the corresponding
  payment occurred on or before the engagement's return-filing due date (using the
  engagement's financial year end); flag accruals with no matching payment evidence in
  the uploaded data.
- **Limitation:** Depends entirely on the chart-of-accounts/description text reliably
  identifying which GL accounts are "statutory dues" within the meaning of 43B(a)-(f) —
  FinSight has no dedicated statutory-dues account tag, so this will use a keyword
  list (same pattern as Audit's `_WRITE_OFF_KEYWORDS`-style detectors), which is a
  screening heuristic, not a guarantee of complete or precise identification.
- **Suggested query:** "Please confirm the payment date for this statutory due, and
  whether it was paid before the return-filing due date."
- **Verification status:** **VERIFIED** (old Act 1961 citation).

---
**TAX-MSME-013 — MSME Delayed-Payment Disallowance Screen** *(new this stage)*
- **Provision/section:** Section 43B, clause (h) — some sources currently label it (g)
  post-renumbering within 43B itself; this labeling ambiguity is noted but does not
  affect the substance — inserted by the Finance Act, 2023, effective **FY 2023-24 (AY
  2024-25)** onward. Disallows any sum payable to a **Micro or Small** enterprise
  (registered under Section 7(1) of the MSMED Act, 2006 — Medium enterprises are
  explicitly **excluded**) for goods/services, unless paid within the time limit under
  Section 15 of the MSMED Act, 2006 (the period agreed in writing, capped at 45 days,
  or 15 days if no written agreement). Unpaid-in-time amounts are disallowed in the
  year of accrual and allowed only in the year of actual payment — the general 43B
  "paid before return due date" grace period does **not** apply to this clause.
- **New Act 2025 (unverified forward reference):** reported as Section 37(2)(g) by a
  single secondary source (TaxUpdate.in) — **not cross-checked**, treat as unconfirmed.
- **FY/AY:** FY 2025-26, AY 2026-27 (old Act) — applicable since FY2023-24.
- **Effective date:** 1 April 2023 (Finance Act 2023).
- **Source:** [Section 43B — incometaxindia.gov.in](https://www.incometaxindia.gov.in/w/section-43b-42)
  (same primary fetch as TAX-DIS-006, includes this clause's text).
- **Applicability:** Any engagement with AP transactions to Micro or Small enterprise
  suppliers.
- **Data required:** `AP` rows with invoice/accrual date, payment date, and — this is a
  **genuine data-model gap, flagged here rather than assumed away** — FinSight
  currently has **no field anywhere capturing a supplier's MSME registration status
  (Micro/Small/Medium/not registered)**. Neither `AP` transaction rows nor any other
  table carries this.
- **Test:** Compute days-elapsed between each AP accrual and its matching payment; flag
  any AP relationship where elapsed days exceed 45 (FinSight's ceiling, matching the
  statutory cap) **and** ask the reviewer to confirm MSME status, rather than asserting
  it — since FinSight cannot determine MSME registration from the data it has.
- **Limitation:** Cannot determine, from data alone, which suppliers are Micro/Small
  registered under the MSMED Act — every finding must explicitly state "review whether
  this supplier is MSME-registered" rather than asserting a disallowance. If you want
  this to be a precise (non-candidate) check, it would need a new `is_msme_registered`
  or similar field on the AP party/vendor data — **a schema change I have not made and
  would flag separately for your approval if you want this rule sharpened.**
- **Suggested query:** "Please confirm whether this supplier is registered as a Micro
  or Small Enterprise under the MSMED Act, 2006, and if so, provide the agreed payment
  term and evidence of actual payment date."
- **Verification status:** **VERIFIED** (old Act 1961 citation and mechanism); the
  rule's *executability* is separately limited by the data-model gap above, disclosed
  in every finding.

---
**TAX-PRES-015 — Presumptive Taxation Declared-Rate Consistency Check** *(new this stage)*
- **Provision/section:** Sections 44AD (business) and 44ADA (specified professions),
  Income-tax Act, 1961. 44AD: turnover base limit ₹2 crore, enhanced to ₹3 crore where
  cash receipts are ≤5% of turnover (non-account-payee instruments count as cash);
  deemed income 8% of turnover (6% for digital receipts). 44ADA: gross-receipts base
  limit ₹50 lakh, enhanced to ₹75 lakh under the same ≥95%-digital condition; deemed
  income 50% of gross receipts.
- **New Act 2025 (unverified forward reference):** reported as a single consolidated
  Section 58 by two sources, but one of those sources was internally inconsistent
  (elsewhere citing 45/46) — treat as unresolved.
- **FY/AY:** FY 2025-26, AY 2026-27 (old Act).
- **Effective date:** current limits per Finance Act changes in recent years; the exact
  Finance Act/year that set the *current* ₹3cr/₹75L enhanced limits was not
  independently pinned down in this pass — flagged for a follow-up check, though the
  limit figures themselves are primary-sourced.
- **Source:** [Section 44AD — incometaxindia.gov.in](https://www.incometaxindia.gov.in/w/section-44ad-34),
  [Section 44ADA — incometaxindia.gov.in](https://www.incometaxindia.gov.in/w/section-44ada-6)
  (primary text fetched directly for both).
- **Applicability:** Business/professional engagements at or near these turnover bands.
- **Data required:** `GL`/`TB`/`SALES` for turnover, `BANK` payment-mode data (reusing
  `is_cash_payment_mode()`) for the cash-receipts percentage.
- **Test:** Compute annual turnover/gross receipts and cash-receipt percentage; flag
  where the engagement crosses a base or enhanced presumptive threshold, or where a
  declared presumptive income appears inconsistent with the 6%/8%/50% deemed rate
  applied to computed turnover.
- **Limitation:** Purely a threshold/consistency flag — does not itself determine
  eligibility (e.g. certain entity types and certain professions are excluded from
  44ADA regardless of turnover) or override a taxpayer's valid election.
- **Suggested query:** "Please confirm the presumptive scheme election for this year
  and the basis for the declared income percentage."
- **Verification status:** **VERIFIED** (old Act 1961 citation; effective-date-of-current-limits
  needs one follow-up confirmation, does not affect the limit figures themselves).

---
**TAX-UXC-019 — Unexplained/Unsubstantiated Credit Entry Screening Flag** *(new this stage)*
- **Provision/section:** Sections 68 (unexplained cash credits in books), 69
  (unexplained investments), 69A (unexplained money/bullion/jewellery), 69C (unexplained
  expenditure), Income-tax Act, 1961.
- **New Act 2025 (unverified forward reference):** reported as Sections 102–105 by
  three independent sources, conflicting with a fourth source claiming unchanged
  numbering — a genuine, unresolved conflict, explicitly flagged.
- **FY/AY:** FY 2025-26, AY 2026-27 (old Act).
- **Effective date:** Long-standing provisions.
- **Source:** section existence/numbers cross-checked, but **verbatim section text was
  not directly fetched from incometaxindia.gov.in in this research pass** — the
  research agent explicitly recommended a follow-up direct fetch before finalizing
  wording.
- **Applicability:** Any engagement with GL/JE credit entries lacking clear
  counterparty/source documentation.
- **Data required:** `GL`/`JE` rows, particularly credits to capital, unsecured-loan,
  or similarly opaque account types.
- **Test:** Flag large, round-sum, or narratively-thin credit entries to
  capital/unsecured-loan-type accounts as candidates for a "source of funds" inquiry —
  this is explicitly a heuristic screen, reusing patterns already established elsewhere
  in FinSight (round-sum detection from AUD-JE-003, rarity/unusual-account detection
  from AUD-ACC-004), not a new detection mechanism.
- **Limitation:** This is the **most legally fraught rule in this catalogue** — Sections
  68/69/69A/69C turn on whether an explanation offered by the assessee is
  "satisfactory" to the Assessing Officer, a judgment call no software can make.
  FinSight's role here is strictly limited to surfacing candidates for a professional
  to inquire about — a finding here must never be worded as "unexplained" (a legal
  conclusion) and must instead say "no source/counterparty narrative found in the data
  provided; recommend inquiry." Given this rule's heavier legal-wording risk, I'd
  recommend treating it as **lower priority than the other rules in this catalogue** —
  flagging that recommendation rather than deciding it, since you may feel differently.
- **Suggested query:** "Please provide the nature and source of this credit entry, and
  supporting documentation (agreement, bank confirmation, counterparty PAN, etc.)."
- **Verification status:** **SOURCE_VERIFICATION_REQUIRED** — section text not yet
  directly primary-fetched; must not execute until that follow-up is done.

---

### B. Tax Audit / Form 3CD Review

---
**TAX-AUD-014 — Tax Audit Applicability / Turnover-Threshold Test** *(new this stage)*
- **Provision/section:** Section 44AB, Income-tax Act, 1961. Business: base ₹1 crore
  turnover/gross receipts; enhanced to ₹10 crore where cash receipts **and** cash
  payments each do not exceed 5% of the respective total (non-account-payee instruments
  count as cash). Professionals: ₹50 lakh gross receipts, no enhanced-cash variant.
  Audit also triggers where a taxpayer eligible for 44AD/44ADA either opts out or
  declares income below the deemed presumptive rate while total income exceeds the
  basic exemption limit.
- **New Act 2025 (unverified forward reference):** reported as **Section 63** by
  multiple consistent secondary sources (certicom.in, ClearTax, TaxGuru) but **no
  primary text was reached** — flagged explicitly as secondary-only despite the
  consistency.
- **FY/AY:** FY 2025-26, AY 2026-27 (old Act; this is the audit currently due).
- **Effective date:** current thresholds; exact Finance Act/year of the last threshold
  change not independently pinned down in this pass.
- **Source:** [Section 44AB — incometaxindia.gov.in](https://www.incometaxindia.gov.in/w/section-44ab-38)
  (primary text fetched directly).
- **Applicability:** Every engagement — this is the gateway determination for whether a
  tax audit applies at all.
- **Data required:** `GL`/`TB`/`SALES` for turnover, `BANK` payment-mode data for the
  cash-receipt/cash-payment percentages, and TAX-PRES-015's presumptive-scheme output.
- **Test:** Compute turnover/gross receipts and cash percentages; compare against the
  base and enhanced thresholds; report whether tax audit applicability appears likely,
  with the basis shown.
- **Limitation:** An **applicability indicator, not a determination** — entity-type-
  specific carve-outs, prior-year audit history, and presumptive-scheme elections can
  all affect the actual answer in ways FinSight's data alone cannot fully resolve.
- **Suggested query:** "Please confirm whether a tax audit under Section 44AB applies
  for this year, and the basis (turnover, cash percentage, or presumptive-scheme
  opt-out)."
- **Verification status:** **VERIFIED** (old Act 1961 citation).

---
**TAX-DEP-005 — Tax Depreciation Recompute & Book-vs-Tax Variance**
- **Provision/section:** Section 32, Income-tax Act, 1961, read with Rule 5 and
  Appendix I (block-of-asset depreciation). Current WDV rates for common blocks:
  Residential buildings 5%, non-residential/factory buildings 10%, furniture & fittings
  10%, plant & machinery (general) 15%, computers/software 40%, motor vehicles
  (general use) 15%, motor vehicles (used in hire business) 30%. The "put to use for
  less than 180 days → half rate" rule remains current and unchanged.
- **New Act 2025 (unverified forward reference):** Section 33 — cross-checked across
  two independent sources, consistent, but not primary-confirmed; the 180-day rule's
  retention under the new Act rests on secondary comparison only.
- **FY/AY:** FY 2025-26, AY 2026-27 (old Act).
- **Effective date:** Current rate table; no recent rate change found for the blocks
  above. A historical motor-car value/usage restriction (pre-2001 acquisitions only)
  was confirmed to have no current effect.
- **Source:** [Depreciation Rates — incometaxindia.gov.in](https://www.incometaxindia.gov.in/w/depreciation-rates),
  [Section 32 — incometaxindia.gov.in](https://www.incometaxindia.gov.in/w/section-32-16)
  (primary text fetched directly for both).
- **Applicability:** Any engagement with `FIXED_ASSETS` data.
- **Data required:** `FixedAsset` rows — already has `tax_block_of_asset`,
  `tax_depreciation_rate`, `opening_wdv_paise`, `additions_paise`, `deletions_paise`,
  `closing_wdv_paise`, `date_put_to_use` (this table's own docstring, written in an
  earlier stage, already anticipated this rule by name).
- **Test:** Recompute expected tax depreciation per block (opening WDV + additions,
  applying the 180-day half-rate rule per asset, less deletions) using the recorded
  `tax_depreciation_rate`, and flag variance against the recorded
  `closing_wdv_paise`/depreciation amount beyond a FinSight-configurable tolerance.
- **Limitation:** Correctness depends entirely on `tax_block_of_asset` and
  `tax_depreciation_rate` having been accurately populated at upload/mapping time —
  FinSight does not independently verify an asset was correctly classified into its
  block; a misclassified block will produce a wrong "expected" figure. Also flags
  (does not silently apply) the **Form 3CD Clause 15** citation for depreciation
  particulars — **clause number SOURCE_VERIFICATION_REQUIRED**, not confirmed against
  the gazetted Form 3CD in this pass.
- **Suggested query:** "Please confirm the tax block classification and rate applied
  for this asset, and explain the variance between computed and recorded tax
  depreciation."
- **Verification status:** **VERIFIED** (old Act 1961 citation and rate table); 3CD
  clause-15 citation separately `SOURCE_VERIFICATION_REQUIRED`.

---
**TAX-3CD-011 — Capital vs Revenue Expenditure Classification (Form 3CD)**
*(carried forward from the original v0.2 catalogue — not researched in this pass)*
- **Provision/section:** Form 3CD's capital-vs-revenue expenditure clause, Income-tax
  Act 1961 / Rule 6G.
- **Status note:** this topic was **not covered by any of the five research passes run
  for this stage** — it fell outside the specific areas you listed (it doesn't map
  cleanly onto Income-tax analytical / TDS / Cash / and the other 3CD items were
  prioritized). Carried forward unchanged from the original Blueprint Section 5
  placeholder rather than silently dropped.
- **FY/AY / Effective date / Source / Applicability / Data required / Test /
  Limitation / Suggested query:** not yet determined — genuinely TBD.
- **Verification status:** **SOURCE_VERIFICATION_REQUIRED** (unresearched; recommend
  prioritizing in a follow-up pass if you want this rule included in Stage 10's actual
  build).

---

### C. TDS Review

---
**TAX-TDS-007 — TDS Non-/Short-Deduction Expense Disallowance Screen**
- **Provision/section:** Section 40(a)(ia) (payments to residents) / 40(a)(i)
  (payments to non-residents) and Section 36(1)(va) (employee PF/ESI contribution
  deposited late), Income-tax Act, 1961 — disallowance of the expense where applicable
  TDS was not deducted, or deducted but not deposited, within the prescribed time.
- **New Act 2025 (unverified forward reference):** not researched at the specific-
  disallowance-clause level in this pass (Section 393 was confirmed for the *TDS rate*
  provisions, Chapter XVII-B, but the *disallowance-for-default* provision is a
  different section (40(a)) and was not separately traced).
- **FY/AY:** FY 2025-26, AY 2026-27 (old Act).
- **Effective date:** Long-standing provision.
- **Source:** **Not directly primary-fetched in this pass** — existence and general
  mechanism are well-established, but no research agent quoted the verbatim
  incometaxindia.gov.in text for Section 40(a)(ia)/40(a)(i)/36(1)(va) specifically.
- **Applicability:** Any engagement with AP/expense transactions subject to TDS.
- **Data required:** `TdsLineItem` (already has `section_code`, `deductee_pan`,
  `rate_applied`, `amount_deducted_paise`, `challan_number`, `deposit_date`, and a
  `transaction_id` FK into `transactions`) joined against `AP`/`GL` expense rows.
- **Test:** For AP/expense transactions above a TDS-applicable threshold (per
  TAX-TDS-008's rate/threshold table, once verified), check for a matching
  `TdsLineItem` row with a populated `deposit_date`; flag expense rows with no matching
  deduction/deposit evidence.
- **Limitation:** Depends on TAX-TDS-008's rate/threshold table (currently
  unverified) to know which expenses were TDS-applicable in the first place — this
  rule cannot run meaningfully until that one is verified. Also carries an unconfirmed
  **Form 3CD Clause 16** citation.
- **Suggested query:** "Please confirm whether TDS was deducted and deposited for this
  payment, and provide the challan/deposit evidence."
- **Verification status:** **SOURCE_VERIFICATION_REQUIRED** — core section text not
  primary-fetched; must not execute.

---
**TAX-TDS-008 — TDS Rate & Threshold Consistency Check**
- **Provision/section:** Chapter XVII-B, Income-tax Act, 1961 — section-wise TDS rates
  and thresholds. Candidate rates researched (194C contractors: 1%/2%, ₹30,000
  single/₹1,00,000 aggregate; 194J professional/technical fees: 10%/2%, ₹50,000
  threshold; 194H commission: 2%, ₹20,000 threshold; 194-I rent: 2% plant & machinery /
  10% land-building, ₹50,000/month threshold; 194Q goods purchase: 0.1%, buyer turnover
  >₹10cr and purchase >₹50 lakh from one seller; 192 salary: slab-based, not a flat
  rate).
- **New Act 2025 (unverified forward reference):** Section 393 (consolidated non-
  salary TDS section) and Section 392 (salary) — this consolidation itself **is**
  primary-confirmed (official press release plus incometax.gov.in's own Form 141 help
  page reference "Form 141... u/s 393"), but the **specific rate/threshold figures
  inside Section 393's table were not independently read from primary text** in this
  pass (the fetch of the Act PDF truncated before reaching that table).
- **FY/AY:** FY 2025-26 rates effective 1 April 2025 (old Act, Finance Act 2025
  changes); FY 2026-27 onward under new Act Section 393 (rates reported as "largely
  unchanged" by secondary sources, not primary-confirmed).
- **Effective date:** 1 April 2025 for the current rate/threshold figures (194J
  threshold raised to ₹50,000, 194H raised to ₹20,000 and rate cut to 2%, 194-I raised
  to ₹50,000/month — all per Finance Act 2025 changes, secondary-corroborated).
- **Source:** rates/thresholds corroborated across multiple consistent secondary
  sources (setindiabiz, TaxGuru); **no primary incometaxindia.gov.in section page was
  directly quoted for the rate figures themselves** in this pass (only Section 206AB's
  omission and the March-2026 TDS deposit due date were primary-confirmed — see below).
- **Two sub-facts that ARE primary-verified and safe to treat as settled regardless of
  the rate table's status:**
  - **Section 206AB (and 206CCA) — higher TDS/TCS rate for return-non-filers — was
    OMITTED effective 1 April 2025** by Clause 66/68 of the Finance Act 2025, confirmed
    directly from the Finance Bill 2025 PDF on incometaxindia.gov.in
    ([source](https://www.incometaxindia.gov.in/documents/20117/6476586/Finance_Bill-2025.pdf)).
    **No 206AB "higher rate" logic should ever be built as currently active** — if
    modeled at all, it must be labeled a historical rule for pre-1-April-2025
    transactions only.
  - **TDS deposit due date for March is 30 April** of the following year (not the usual
    7th of the following month) — confirmed verbatim from an incometax.gov.in FAQ.
  - **"Earlier of credit or payment" relative to 31 March 2026** determines whether the
    old or new Act governs a given TDS event — confirmed verbatim from the same FAQ.
- **Applicability:** Any engagement with TDS-relevant expense transactions.
- **Data required:** `TdsLineItem`, `AP`/`GL` expense rows.
- **Test:** (once verified) compare `TdsLineItem.rate_applied` against the correct
  section-wise rate for the transaction date, and the transaction amount against the
  applicable threshold, flagging mismatches.
- **Limitation:** Cannot execute meaningfully until the rate/threshold table itself is
  primary-verified — recommend that as the very next concrete verification step if you
  approve this catalogue, since TAX-TDS-007 depends on it too.
- **Suggested query:** "Please confirm the TDS section, rate, and threshold applied to
  this payment against the current rate chart."
- **Verification status:** **SOURCE_VERIFICATION_REQUIRED** for the rate/threshold
  table; the three sub-facts above (206AB omission, March deposit date, Act-cutover
  rule) are individually `VERIFIED` and safe to use as supporting logic/messaging even
  while the rule itself stays gated.

---

### D. Cash Transaction Review

---
**TAX-CASH-001 — Cash Expenditure Disallowance Screen**
- **Provision/section:** Section 40A(3) and 40A(3A), Income-tax Act, 1961 —
  disallowance of expenditure paid in cash exceeding ₹10,000 in a day to a single
  person, otherwise than by account-payee cheque/draft/prescribed electronic mode
  (₹35,000 for payments to transport operators for plying/hiring/leasing goods
  carriages). Rule 6DD carries exceptions (payments to banks/RBI/government where cash
  is mandated, payments to cultivators/producers of agricultural/forest/animal-
  husbandry/dairy/fishery/cottage-industry produce, payments in villages without bank
  service, terminal benefits to employees up to ₹50,000, and others).
- **New Act 2025 (unverified forward reference):** Section 36 — cross-checked across
  three independent sources, consistent.
- **FY/AY:** FY 2025-26, AY 2026-27 (old Act).
- **Effective date:** ₹10,000 threshold effective from Finance Act 2017 (AY 2018-19
  onward, reduced from ₹20,000); ₹35,000 transporter threshold from Finance Act
  2008/2009.
- **Source:** [Prohibited transaction in cash / limit on cash transactions — incometaxindia.gov.in](https://www.incometaxindia.gov.in/w/prohibited-transaction-in-cash/limit-on-cash-transactions%E2%80%8B)
  (primary, consolidated official page), cross-checked against TaxGuru/ClearTax with no
  conflict.
- **Applicability:** Every engagement with cash-mode payments.
- **Data required:** `GL`/`JE`/`BANK` rows with `payment_mode` (reusing
  `is_cash_payment_mode()`), amount, party, and date.
- **Test:** Aggregate same-day cash payments per party; flag where the aggregate
  exceeds ₹10,000 (or ₹35,000 for identified transporter payments), excluding rows the
  reviewer has tagged against a Rule 6DD exception category.
- **Limitation:** Cannot automatically apply the Rule 6DD exceptions (e.g. identifying
  which payees are agricultural producers, or which villages lack bank service) — every
  finding must state the exceptions exist and ask the reviewer to confirm none apply,
  rather than silently assuming a violation.
- **Suggested query:** "Please confirm the mode of payment and whether any Rule 6DD
  exception applies to this cash payment."
- **Verification status:** **VERIFIED** (old Act 1961 citation).

---
**TAX-CASH-002 — Large Cash Receipt Restriction Screen**
- **Provision/section:** Section 269ST, Income-tax Act, 1961 — no person shall receive
  ₹2,00,000 or more in cash (a) in aggregate from a person in a day, (b) in respect of a
  single transaction, or (c) in respect of transactions relating to one event/occasion
  from a person. Exceptions: receipts by Government, banking company, post office
  savings bank, co-operative bank; transactions already covered by Section 269SS;
  and other Central-Government-notified receipts.
- **New Act 2025 (unverified forward reference):** Section 186 — cross-checked across
  multiple independent sources, consistent.
- **FY/AY:** FY 2025-26, AY 2026-27 (old Act).
- **Effective date:** Inserted by Finance Act 2017, effective 1 April 2017.
- **Source:** [Section 269ST — incometaxindia.gov.in](https://www.incometaxindia.gov.in/w/section-269st-9)
  and the same consolidated threshold page as TAX-CASH-001 (both primary, fetched
  directly).
- **Applicability:** Every engagement with cash receipts.
- **Data required:** `GL`/`JE`/`BANK`/`SALES`/`AR` rows with `payment_mode`, amount,
  party, date.
- **Test:** Check all three limbs — same-day aggregate per party, single transaction,
  and (where an "event/occasion" grouping can be inferred, e.g. a shared invoice/order
  reference) transactions tied to one occasion — against ₹2,00,000, excluding rows
  already captured under TAX-LOAN-003/Section 269SS.
- **Limitation:** The "one event or occasion" limb requires grouping logic FinSight's
  data may not cleanly support (no dedicated "event" field) — this limb will likely
  need to be flagged as **partial coverage**, clearly disclosed, rather than a full
  implementation, unless a grouping key is identified during design.
- **Suggested query:** "Please confirm the mode of receipt and whether the aggregate
  cash received from this party (by day, transaction, or event) exceeds ₹2,00,000."
- **Verification status:** **VERIFIED** (old Act 1961 citation).

---
**TAX-LOAN-003 — Cash Loan/Deposit Acceptance & Repayment Restriction Screen**
- **Provision/section:** Section 269SS (acceptance) and Section 269T (repayment),
  Income-tax Act, 1961 — no loan, deposit, or specified sum of ₹20,000 or more (single
  or aggregate outstanding-plus-fresh) may be accepted or repaid other than by
  account-payee cheque/draft/prescribed electronic mode. Enhanced threshold ₹2,00,000
  for transactions with a Primary Agricultural Credit Society or Primary Co-operative
  Agricultural and Rural Development Bank (Finance Act 2023, effective 1 April 2023).
  Exceptions include Government, banking companies, post office savings banks,
  co-operative banks, notified institutions, and transactions where both parties have
  only agricultural income.
- **New Act 2025 (unverified forward reference):** Section 185 (acceptance) / Section
  188 (repayment) — cross-checked across three independent sources, consistent.
- **FY/AY:** FY 2025-26, AY 2026-27 (old Act).
- **Effective date:** ₹20,000 threshold long-standing; ₹2,00,000 PACS/PCARD enhancement
  from 1 April 2023.
- **Source:** [What is the threshold limit for Section 269SS? — incometaxindia.gov.in](https://www.incometaxindia.gov.in/w/what-is-the-threshold-limit-for-section-269ss-)
  and equivalent official 269T text (primary, fetched directly).
- **Applicability:** Every engagement with loan/deposit-type transactions.
- **Data required:** **A genuine data-model gap, flagged rather than assumed away:**
  FinSight has no dedicated "loans/deposits register" dataset type (the current list is
  `TB, GL, JE, SALES, PURCHASE, BANK, AR, AP, FIXED_ASSETS, GST, TDS, PRIOR_YEAR,
  OTHER`). This rule would need to approximate loan/deposit transactions via `GL`/`JE`
  account-name keyword matching (e.g. "unsecured loan," "deposit accepted") or `BANK`
  transactions above the threshold to/from a counterparty tagged as a lender — the same
  keyword-heuristic pattern already used elsewhere in FinSight (e.g. Audit's write-off
  detector), not a new mechanism, but disclosed here as a real limitation, not silently
  assumed to be reliable.
- **Test:** Identify cash-mode loan/deposit acceptance or repayment transactions
  ≥₹20,000 (or ≥₹2,00,000 for PACS/PCARD counterparties, if identifiable) via the
  keyword/account heuristic above.
- **Limitation:** Precision is bounded by how reliably loan/deposit transactions can be
  identified from GL/JE account naming — this will under- or over-flag depending on
  chart-of-accounts quality, and must say so in every finding. Also carries an
  unconfirmed **Form 3CD Clause 21** citation.
- **Suggested query:** "Please confirm the mode of acceptance/repayment for this
  loan/deposit, and whether any Section 269SS/269T exception applies."
- **Verification status:** **VERIFIED** (old Act 1961 citation and threshold); 3CD
  clause-21 citation separately `SOURCE_VERIFICATION_REQUIRED`; practical execution
  bounded by the data-model gap above.

---
*(Informational only, not a separate rule: penalty provisions Section 271D — 269SS
violation, Section 271E — 269T violation, and Section 271DA — 269ST violation — each a
penalty equal to 100% of the amount involved, confirmed via primary text for 271D and
271DA — should appear in the finding explanation text of TAX-CASH-002/TAX-LOAN-003 as
context on stakes, exactly as Audit's rules cite consequences without computing them.)*

---

### E. Other Tax-Related Review Areas

---
**TAX-GST-009 — GST Invoice Reconciliation**
*(carried forward from the original v0.2 catalogue, unchanged in substance)*
- **Provision/section:** Not a specific statutory provision — this is a data-
  reconciliation check (matching the same invoice across `SALES`/`PURCHASE`/`GST`
  source datasets via `GstLineItem.invoice_number`), not a legal test.
- **New context from this stage's research:** No Income-tax Act provision (old or new)
  was found to *statutorily mandate* reconciling GST turnover against income-tax
  turnover — a 2020 government clarification (reported by Business Standard) states GST
  turnover shown in Form 26AS is "for information only." This kind of reconciliation is
  standard professional practice, not a codified cross-check requirement — worth
  knowing, since it means this rule's value is audit-quality/risk-based, not
  compliance-mandated.
- **FY/AY / Effective date:** Not applicable (logic-only).
- **Source:** N/A for the reconciliation logic itself; Business Standard reporting of a
  government clarification for the "no statutory mandate" context above.
- **Applicability:** Any engagement with `GstLineItem` data from more than one
  `source_dataset`.
- **Data required:** `GstLineItem` rows (already modeled — `invoice_number`,
  `taxable_value_paise`, `cgst_paise`/`sgst_paise`/`igst_paise`, `source_dataset`).
- **Test:** For each `invoice_number`, compare the taxable value and tax amounts
  recorded across its `SALES`/`PURCHASE`/`GST` source rows; flag mismatches beyond a
  FinSight-configurable tolerance.
- **Limitation:** Lower risk category (per the original register) since there's no
  statutory citation to get wrong — purely internal consistency of data already in
  FinSight; does not verify actual GST return filing or its correctness. Carries an
  unconfirmed **Form 3CD Clause 41** citation (turnover-reconciliation reporting) —
  clause number not verified against the gazetted form.
- **Suggested query:** "Please explain the discrepancy between the Sales/Purchase
  register and GST return figures for this invoice."
- **Verification status:** **VERIFIED** (logic-only rule, no statutory citation to
  verify — unchanged from the original register's classification); 3CD clause-41
  citation separately `SOURCE_VERIFICATION_REQUIRED`.

---
**TAX-ACM-010 — Method of Accounting / ICDS Consistency Flag**
- **Provision/section:** Section 145, Income-tax Act, 1961 — income under "Profits and
  Gains of Business or Profession" or "Income from Other Sources" must be computed per
  the method of accounting (cash or mercantile) regularly employed by the assessee.
  Section 145(2) empowers the Central Government to notify Income Computation and
  Disclosure Standards (ICDS) by Official Gazette — 10 ICDS are currently notified,
  applicable from AY 2017-18 onward to assessees on the mercantile system (with
  carve-outs for individuals/HUFs not subject to 44AB audit and, with caveats,
  presumptive-taxation assessees).
- **New Act 2025 (unverified forward reference):** Section 276 for 145(1) — single-
  source only; the ICDS-notification-power sub-clause specifically (145(2)'s new-Act
  equivalent) was not found in this pass.
- **FY/AY:** FY 2025-26, AY 2026-27 (old Act); ICDS applicable from AY 2017-18 onward.
- **Effective date:** ICDS from AY 2017-18.
- **Source:** [ICDS — incometaxindia.gov.in](https://www.incometaxindia.gov.in/income-computation-and-disclosure-standards-icds-1)
  (primary text fetched directly, confirming applicability and notified-standard count).
- **Applicability:** Any engagement — but see the data-model gap below.
- **Data required:** **Another genuine data-model gap, flagged rather than assumed
  away:** FinSight's `EntityProfile` (per the architecture blueprint) does not
  currently capture the entity's elected accounting method (cash vs mercantile), only
  `accounting_framework` (AS/Ind AS). Without that field, this rule cannot determine
  which method is "regularly employed" to check against.
- **Test:** (once a method field exists) check applied revenue/expense recognition
  patterns in `GL`/`JE` data for consistency with the declared method, year over year.
- **Limitation:** Not executable as designed without a new field — this is a design
  question, not a decision I've made; if you want this rule active, it needs a
  proposed `EntityProfile` schema addition, which per the standing project rule I would
  flag and get your approval on separately, before touching the schema.
- **Suggested query:** "Please confirm the method of accounting (cash or mercantile)
  regularly employed, and any change from the prior year."
- **Verification status:** **VERIFIED** (old Act 1961 legal basis and ICDS
  applicability); **not currently implementable** without a separate, approved schema
  addition — flagged, not decided, here.

---

## 3. Summary table

| Rule ID | Area | Provision (old Act 1961) | Verification status | Blocking issue (if any) |
|---|---|---|---|---|
| TAX-RPT-004 | Income-tax Analytical | Sec 40A(2) | VERIFIED | Candidate-list only, no market-rate data |
| TAX-DIS-006 | Income-tax Analytical | Sec 43B(a)-(f) | VERIFIED | Keyword-based statutory-due identification |
| TAX-MSME-013 | Income-tax Analytical | Sec 43B(h) | VERIFIED | No MSME-registration field in schema |
| TAX-PRES-015 | Income-tax Analytical | Sec 44AD/44ADA | VERIFIED | Effective-date-of-limits follow-up recommended |
| TAX-UXC-019 | Income-tax Analytical | Sec 68/69/69A/69C | **SOURCE_VERIFICATION_REQUIRED** | Verbatim section text not primary-fetched |
| TAX-AUD-014 | Tax Audit / 3CD | Sec 44AB | VERIFIED | Applicability indicator only |
| TAX-DEP-005 | Tax Audit / 3CD | Sec 32 + Appendix I | VERIFIED | 3CD Clause 15 citation unconfirmed |
| TAX-3CD-011 | Tax Audit / 3CD | Form 3CD capital/revenue clause | **SOURCE_VERIFICATION_REQUIRED** | Not researched this pass |
| TAX-TDS-007 | TDS | Sec 40(a)(ia)/40(a)(i)/36(1)(va) | **SOURCE_VERIFICATION_REQUIRED** | Core text not primary-fetched; depends on TAX-TDS-008 |
| TAX-TDS-008 | TDS | Chapter XVII-B rate chart | **SOURCE_VERIFICATION_REQUIRED** | Rate table secondary-only |
| TAX-CASH-001 | Cash Transaction | Sec 40A(3)/40A(3A) | VERIFIED | Rule 6DD exceptions not automatable |
| TAX-CASH-002 | Cash Transaction | Sec 269ST | VERIFIED | "Event/occasion" limb partial coverage only |
| TAX-LOAN-003 | Cash Transaction | Sec 269SS/269T | VERIFIED | No loan/deposit dataset type; 3CD Clause 21 unconfirmed |
| TAX-GST-009 | Other | N/A (logic-only) | VERIFIED | 3CD Clause 41 citation unconfirmed |
| TAX-ACM-010 | Other | Sec 145 + ICDS | VERIFIED | No accounting-method field in schema |

**11 of 15 rules VERIFIED** (old Act 1961 citation, primary-sourced); **4 remain
SOURCE_VERIFICATION_REQUIRED** and will not be implemented as executable
(TAX-UXC-019, TAX-3CD-011, TAX-TDS-007, TAX-TDS-008). Note that "VERIFIED" here means
the *legal citation* is primary-sourced — several VERIFIED rules still carry disclosed,
real limitations (data-model gaps, heuristic-only identification, unconfirmed 3CD
clause numbers) that bear on how much weight a finding from that rule should carry;
these are not hidden, they're written into each rule's own Limitation field and would
carry into that rule's finding text exactly as Audit's rules already do.

---

## 4. What I need from you before any code is written

1. **Approve or revise the Act-transition design decision in Section 0** — verify/gate
   against the old Act 1961, carry new-Act-2025 numbers as unverified non-gating
   metadata. This is the single biggest structural decision in this catalogue.
2. **Decide on the 4 data-model gaps flagged above** (no MSME-registration field, no
   loans/deposits dataset type, no accounting-method field, no dedicated statutory-dues
   account tag) — none of these have been implemented; each would need its own flagged
   schema-change proposal before the affected rule could move beyond a heuristic
   screen, per the standing project rule that no schema change happens without your
   explicit sign-off.
3. **Confirm which of the 15 rules to prioritize for Stage 10's actual build** — all 15
   are proposed, but you may want a smaller first slice (e.g. the Cash Transaction
   Review area, which has the strongest verification and least data-gap exposure).
4. **Tell me if TAX-UXC-019 (unexplained credits) should stay in scope at all**, given
   its heavier legal-wording risk flagged above — I've recommended lower priority but
   left the decision with you.
5. Separately, and not blocking: the 4 `SOURCE_VERIFICATION_REQUIRED` rules can be
   pushed toward `VERIFIED` with one more direct research pass each (a targeted primary-
   source fetch), if you want that done before or during Stage 10's build rather than
   left gated indefinitely.

Nothing above is code. `verification_status` defaults to `SOURCE_VERIFICATION_REQUIRED`
at row creation for every rule, exactly as the original Blueprint Section 5 governance
rule specifies, and `rule_runner_service` will not execute or display anything not
`VERIFIED` — this document does not change that gate, it only proposes what should
eventually sit behind it.
