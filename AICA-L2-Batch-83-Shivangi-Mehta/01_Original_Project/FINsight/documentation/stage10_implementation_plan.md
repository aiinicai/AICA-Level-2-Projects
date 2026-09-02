# Stage 10 — Implementation Plan (post-approval)

Produced per your explicit "before coding" instruction, after Decisions 1-5 above.
This plan is engineering structure only — the legal research itself is already in
`documentation/stage10_tax_rule_catalogue_proposal.md` and is not repeated here except
where it drives a design choice.

---

## 1. Which rules will be executable

**Updated per your follow-up answer:** nine rules, coded and seeded
`verification_status="VERIFIED"`, `is_active=True`, present in
`app/rules/tax/__init__.py::RULES` — the 8 from Decision 2 plus TAX-MSME-013, built now
using Decision 4's exact required wording ("Potential MSME Payment Review," never
asserting a disallowance from the 45-day gap alone, always requiring confirmation of
MSME registration and payment terms):

| Rule ID | Topic |
|---|---|
| TAX-CASH-001 | Cash Expenditure Disallowance Screen (Sec 40A(3)/(3A)) |
| TAX-CASH-002 | Large Cash Receipt Restriction Screen (Sec 269ST) |
| TAX-LOAN-003 | Cash Loan/Deposit Acceptance & Repayment Restriction Screen (Sec 269SS/269T) |
| TAX-DIS-006 | Statutory Dues Payment-Basis Timing Test (Sec 43B(a)-(f)) |
| TAX-AUD-014 | Tax Audit Applicability / Turnover-Threshold Test (Sec 44AB) |
| TAX-DEP-005 | Tax Depreciation Recompute & Book-vs-Tax Variance (Sec 32 + Appendix I) |
| TAX-RPT-004 | Related-Party Payment Reasonableness Screen (Sec 40A(2)) |
| TAX-GST-009 | GST Invoice Reconciliation (logic-only) |
| TAX-MSME-013 | MSME Delayed-Payment Review Screen (Sec 43B(h)) |

## 2. Which rules remain gated

| Rule ID | Seeded status | is_active | Coded module? |
|---|---|---|---|
| TAX-UXC-019 | SOURCE_VERIFICATION_REQUIRED | False | No |
| TAX-3CD-011 | SOURCE_VERIFICATION_REQUIRED | False | No |
| TAX-TDS-007 | SOURCE_VERIFICATION_REQUIRED | False | No |
| TAX-TDS-008 | SOURCE_VERIFICATION_REQUIRED | False | No |
| TAX-PRES-015 | SOURCE_VERIFICATION_REQUIRED | False | No |
| TAX-ACM-010 | **VERIFIED** (legal citation only) | False | No |

TAX-ACM-010 is seeded `VERIFIED` (its Section 145 legal citation genuinely was
primary-sourced) but `is_active=False` and absent from `RULES` — the existing
three-part gate (`is_active` AND `verification_status == "VERIFIED"` AND `rule_id in
RULES`) already used by `get_runnable_accounting_rules()`/`get_runnable_audit_rules()`
means a row can be legally verified and still structurally non-executable. This
correctly distinguishes "the law is unverified" (the five SOURCE_VERIFICATION_REQUIRED
rows) from "the law is fine, the data isn't there yet" (TAX-ACM-010, blocked on the
accounting-method field Decision 5 says not to add) — worth keeping visibly different
in the catalogue rather than collapsing both into one status. TAX-MSME-013 moved out of
this table per your answer above; its data gap (no MSME-registration field) is instead
handled the way Decision 4 specifies — a candidate/review screen with hedged wording,
not a blocked rule, since the finding itself asks the reviewer to confirm what FinSight
can't determine, rather than waiting on a schema change.

## 3. Exact database fields each rule uses

**No new table, no new column.** `TaxRule` (already defined, Blueprint Section 2.6,
untouched since the original v0.2 approval) has every field this build needs:
`rule_id, standard_id, topic, description, data_required, logic_summary,
risk_level_default, suggested_action, suggested_query_template, effective_date,
is_active, legislative_act, provision_reference, applicable_from_ay,
applicable_to_ay, verification_status, verified_source, verified_on, verified_by`.
`ExceptionRecord`/`QueryRecord` already accept `module="TAX"` (the column comment has
said `ACCOUNTING / AUDIT / TAX / SEBI` since Stage 3) and need nothing new either.

Field usage, one row per rule:

- **`legislative_act`** = `"IT_ACT_1961"` for all 9 (Decision 1 — V1 gates on the old
  Act only). Never `"IT_ACT_2025"` on an executable row.
- **`provision_reference`** = the verified old-Act section, e.g. `"Section 40A(3),
  Section 40A(3A)"`.
- **`description`** carries the New Act 2025 forward reference as clearly labeled,
  non-gating prose, e.g.: *"New Act 2025 forward reference (UNVERIFIED, non-gating):
  Section 36. Do not treat as confirmed or use to determine executability."* No code
  path ever parses or acts on this text — it is display-only, exactly like Audit's SA
  citation is display-only relative to its own threshold.
- **`applicable_from_ay`** = the AY the current threshold took effect (e.g.
  `"AY 2018-19"` for the ₹10,000 40A(3) figure) — the provision's own currency, not
  this engagement's AY.
- **`verified_source`** = the incometaxindia.gov.in/incometax.gov.in URL fetched during
  research. **`verified_on`** = today's date. **`verified_by`** = `"FinSight Stage 10
  research pass — see stage10_tax_rule_catalogue_proposal.md"`.
- **`logic_summary`** = the FinSight analytical test, prefixed exactly like Audit's
  convention: `"FinSight Analytical Test — operationalizes {provision}, threshold set
  by the Act itself: ..."` for the three rules whose rupee figure *is* the statutory
  figure (CASH-001, CASH-002, LOAN-003), versus `"FinSight Analytical Test — a
  FinSight-designed heuristic screen for {provision}, not itself a figure the Act
  specifies: ..."` for the others (RPT-004's reasonableness test, DIS-006/DEP-005's
  keyword/recompute heuristics, AUD-014's dual-threshold applicability check,
  GST-009's reconciliation tolerance).
- **`data_required`** = JSON list of the `dataset_type` values actually read (below).

Per-rule data actually read from `dataset_service.load_engagement_dataset()`
(`dict[dataset_type, list[MappedRow]]`, `MappedRow.values` keyed by target_field —
same mechanism every Accounting/Audit rule already uses; **no** rule reads the
`FixedAsset`/`GstLineItem`/`TdsLineItem` ORM tables directly, since — per
`dataset_service.py`'s own docstring — those remain unpopulated and all rule engines
read the live-mapped-row path instead):

| Rule ID | dataset_type(s) | fields read |
|---|---|---|
| TAX-CASH-001 | `GL`, `BANK` | `payment_mode`, `debit_amount`/`credit_amount`, `party_name` (GL only), `transaction_date` |
| TAX-CASH-002 | `GL`, `BANK`, `SALES`, `AR` | same shape, receipt side |
| TAX-LOAN-003 | `GL`, `JE`, `AP`, `AR` | `account_name`/`description` (keyword match), `payment_mode`, `debit_amount`/`credit_amount`, `party_name`, `transaction_date` |
| TAX-DIS-006 | `GL`, `JE`, `TB` | `account_name`/`description` (keyword match), `debit_amount`/`credit_amount` |
| TAX-AUD-014 | `GL`, `TB`, `SALES`, `BANK` | revenue-account aggregation for turnover, `payment_mode` for cash % |
| TAX-DEP-005 | `FIXED_ASSETS` | `tax_block_of_asset`, `tax_depreciation_rate`, `opening_wdv_paise`, `additions_paise`, `deletions_paise`, `closing_wdv_paise`, `date_put_to_use` |
| TAX-RPT-004 | all dataset_types (via `detect_related_party_candidates`) | `party_name`, `debit_amount`/`credit_amount` |
| TAX-GST-009 | `SALES`, `PURCHASE`, `GST` | `invoice_number`, `taxable_value_paise`, `cgst_paise`/`sgst_paise`/`igst_paise` |
| TAX-MSME-013 | `AP` | `party_name`, `transaction_date` (accrual proxy), `debit_amount`/`credit_amount`, `description` |

`engagement.financial_year` and (TAX-AUD-014 only) `EntityProfile.turnover` /
`EntityProfile.tax_audit_status` (already-existing fields, read not written) are also
used, via the existing `engagement_service` accessors.

## 4. Proposed schema changes

**None.** Per Decision 5, no MSME-registration field, no accounting-method field, no
loans/deposits dataset type, no statutory-dues classification field is added. Every
rule that would benefit from one of these instead uses a disclosed keyword/heuristic
workaround (same pattern Audit's write-off/round-sum detectors already use), with the
gap stated plainly in that rule's `Limitation` text and in its finding's `explanation`
— never silently assumed away. If you later want any of these sharpened, that needs
its own consolidated schema-change proposal, per Decision 5, before I touch the schema.

## 5. Rule execution flow

Mirrors the Audit engine's structure exactly, three new/changed files plus one new
shared module:

1. **`app/rules/tax/act_transition.py` (new)** — `is_old_act_fy(financial_year) ->
   bool` and `describe_act_era(financial_year) -> str` (a display string like `"FY
   2025-26 (AY 2026-27) — Income-tax Act, 1961"`). Pure functions, no DB access, same
   style as `period_utils.py`.
2. **`app/rules/tax/*.py` (new, 9 modules)** — one per executable rule, each exposing
   `RULE_ID`, `TOPIC`, `evaluate(engagement, dataset) -> RuleOutcome` — 2-arg, **not**
   framework-gated (Income-tax law doesn't depend on AS/Ind AS, same reasoning Audit
   already established for SA-based procedures).
3. **`app/rules/tax/__init__.py` (edit)** — `RULES = {rule_id: module}` for exactly
   these 9, explicit imports, mirroring `app/rules/audit/__init__.py`'s registry
   pattern precisely (including its "only these N rules, no silent addition" comment).
4. **`app/rules/wording.py` (edit)** — add the 3 new Tax labels + `TAX_LABELS` tuple
   (Section 8 below).
5. **`app/services/rule_runner_service.py` (edit)** — add `list_all_tax_rules()`,
   `get_runnable_tax_rules()`, `run_tax_rule()`, `run_all_tax_rules()`, mirroring the
   Audit mirror-functions exactly (no framework parameter), with `run_tax_rule()`
   additionally enforcing `wording.TAX_LABELS` the same way `run_audit_rule()` enforces
   `AUDIT_LABELS`.
6. **`app/services/tax_review_service.py` (new)** — mirrors
   `audit_review_service.py` field-for-field: `preview_tax_review()` /
   `run_tax_review()` / `get_last_review_results()` / `get_tax_rules_by_id()`, same
   re-run preservation logic (untouched auto-generated `module="TAX"` exceptions
   cleared before re-insert; reviewer-touched rows preserved). One addition: a new
   `ActEraNotSupportedError(Exception)` (mirrors `AccountingFrameworkNotSetError`'s
   pattern precisely), raised by the shared `_compute_outcomes()` helper when
   `act_transition.is_old_act_fy(engagement.financial_year)` is `False`, **before**
   `run_all_tax_rules()` is ever called — so an FY2026-27+ engagement never even
   attempts to run a rule verified only against the old Act.
7. **`app/api/tax_bp.py` (edit)** — replaces the Stage-3 placeholder with a real GET/POST
   blueprint mirroring `audit_bp.py`, catching `ActEraNotSupportedError` the same way
   `accounting_bp.py` catches `AccountingFrameworkNotSetError` and rendering it as a
   clear banner (not a crash).
8. **`frontend/templates/tax/index.html` (new)** — mirrors `audit/index.html`'s
   structure: info panel explaining the Act-1961-only V1 scope and the Legal
   provision → FinSight test → Limitation → Suggested query split; live-results detail
   table; Persisted Exceptions table; full Rule Catalogue (all 15 rows — 9 executable +
   6 gated/non-executable — so the gated ones stay visible for transparency, exactly
   like Audit's catalogue shows every rule regardless of status).
9. **`database/seed/seed_tax_rules.py` (new)** — mirrors `seed_audit_rules.py`'s
   structure: `STANDARDS` (one `Standard` row per distinct old-Act section family,
   `framework="IT_ACT_1961"`) and `RULES` (all 15 `TaxRule` rows — 9 `VERIFIED`+active,
   6 gated/inactive as specified in Section 2 above).

No migration file — confirmed nothing above needs one.

## 6. FY/AY handling

`engagement.financial_year` (validated `"YYYY-YY"` string, e.g. `"2025-26"`) is the
single source of truth, exactly as every other module already uses it via
`period_utils.financial_year_bounds()`. New `act_transition.is_old_act_fy()` computes
the FY's end date and compares it to 31 March 2026 (the CBDT-confirmed cutover date).
Every Tax finding's explanation states both the FY and its old-Act Assessment Year
(e.g. `"FY 2025-26 (Assessment Year 2026-27), Income-tax Act, 1961"`) via
`act_transition.describe_act_era()`, so a reviewer never has to infer which Act/AY a
finding is citing.

## 7. Act-transition handling

- **Gate:** `tax_review_service._compute_outcomes()` refuses to run *any* tax rule
  (not per-rule — the whole module) for an engagement whose FY is 2026-27 or later,
  raising `ActEraNotSupportedError`. This is deliberately an engagement-level
  precondition, not a per-rule one, since currently *every* executable rule is verified
  against the old Act only — there is no partial case yet.
- **Forward reference, never gating:** the New Act 2025 section number for each rule
  lives only in `TaxRule.description` as labeled prose (Section 3 above). No function
  anywhere reads `legislative_act` and branches to "new Act" behavior — `legislative_act`
  is fixed to `"IT_ACT_1961"` on every row this stage, full stop. When a future stage
  verifies the new Act, the design will need a second `legislative_act="IT_ACT_2025"`
  row (or a versioned-effective-date model) per rule — explicitly **not** built now,
  flagged as a future schema question rather than guessed at today.
- **Sub-facts already primary-verified and safe to use regardless:** the "earlier of
  credit or payment relative to 31 March 2026" TDS cutover rule and the 30 April TDS
  deposit date for March are documented in
  `stage10_tax_rule_catalogue_proposal.md` but are **not used by any of the 8
  executable rules** (none of them are TDS rules) — noted here only so it's clear I
  haven't silently built TDS logic under a different rule ID.

## 8. Finding/query wording

`app/rules/wording.py` gains:

```python
POTENTIAL_TAX_ISSUE = "Potential Tax Issue"
TAX_REVIEW_REQUIRED = "Tax Review Required"
POTENTIAL_DISALLOWANCE_REVIEW_REQUIRED = "Potential Disallowance — Review Required"

TAX_LABELS = (
    POTENTIAL_TAX_ISSUE, TAX_REVIEW_REQUIRED,
    POTENTIAL_DISALLOWANCE_REVIEW_REQUIRED, INSUFFICIENT_DATA,
)
```

`run_tax_rule()` enforces every `ExceptionDraft.label` a Tax module returns is a member
of `TAX_LABELS`, structurally, the same "not a courtesy" approach used for
`AUDIT_LABELS`. A Tax rule never uses an Accounting or Audit label.

**The four-part structure** — every rule's module docstring, every seeded
`TaxRule.logic_summary`, and every persisted finding's `explanation` text follows the
same shape, visible in that order:

1. **Legal provision** — the verified old-Act section and its actual text/threshold.
2. **FinSight analytical test** — exactly what FinSight computed and compared, stated
   as FinSight's own operationalization of the provision (never implied to be verbatim
   from the Act itself, even when the rupee threshold *is* the Act's own figure — the
   *identification method*, e.g. keyword-matching a GL account as a "loan," is always
   FinSight's, even where the *threshold* is the law's).
3. **Limitation** — what the rule cannot establish from the data alone (the specific
   gap: Rule 6DD exceptions not automatable, MSME status unconfirmable, "event/occasion"
   grouping not implemented, etc.), stated in every finding, not just the docstring.
4. **Suggested query** — addressed to the client/auditee, never asserting the answer.

**Never confirmed, always "review required."** No finding text states a disallowance
or violation is confirmed — `wording.assert_non_definitive()` (already enforced on
every `ExceptionDraft` at construction, via `base_rule.py`'s `__post_init__`) continues
to block `FORBIDDEN_TERMS`; I'm not adding "disallowance" to that list since it's part
of an approved label, but every rule's `explanation` text is written to hedge properly
(*"may result in disallowance if X is not established"*, never *"is disallowed"*),
consistent with Decision 4's exact instruction for MSME and applied uniformly to all 8.

**`threshold_used` gains a new key not present in Audit's version:**
`"threshold_is_statutory"` — `True` for TAX-CASH-001/002 and TAX-LOAN-003 (the rupee
figure genuinely *is* the Act's own threshold, cited with its `verified_source`) and
`False` for the other five (a FinSight-designed heuristic or recompute, same as every
Audit threshold today). This is the opposite default from Audit's `threshold_used`
(which is always `False`) — flagging the distinction explicitly so it's not read as
inconsistent with the Audit engine's established convention; it's a deliberate,
disclosed difference because Tax genuinely has some law-mandated numbers where Audit
never did.

---

Nothing above has been coded yet as of this document. Proceeding to implement exactly
the 9 rules in Section 1, gate exactly the rules in Section 2, and change no schema —
per your instruction, moving directly to implementation now.
