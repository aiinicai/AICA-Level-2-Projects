"""
Tax rule-pack content bootstrap (Stage 10).

Seeds the `standards` (one row per distinct Income-tax Act, 1961
section family, framework="IT_ACT_1961"), and `tax_rules` (15 rows —
the full approved Stage 10 catalogue proposal: 9 coded+active+VERIFIED
rules, plus 6 gated rows seeded as metadata only, with NO corresponding
Python module) tables, plus a new `knowledge_base_versions` row marking
this content current. See `app/rules/tax/__init__.py` for the coded-
rule rationale, `documentation/stage10_tax_rule_catalogue_proposal.md`
for the full legal research, and `documentation/stage10_implementation_
plan.md` for the approved executable/gated split (Decisions 1-5).

Tax is NOT framework-gated (same reasoning as Audit) — one TaxRule row
per rule_id, no AS/Ind AS doubling.

ACT-TRANSITION DESIGN (Decision 1, approved): `legislative_act` is
"IT_ACT_1961" on every row — the verified, gating citation. The
Income-tax Act, 2025 forward reference for each rule (where research
found one, however unconfirmed) lives ONLY in `description`, clearly
labeled "UNVERIFIED, non-gating" — never in `legislative_act`, never
used by any code path to decide executability (see
`app/rules/tax/act_transition.py`).

VERIFICATION STATUS SPLIT (Decision 2/3, approved):
  - 9 rows: verification_status="VERIFIED", is_active=True — coded in
    app/rules/tax/RULES.
  - 5 rows (TAX-UXC-019, TAX-3CD-011, TAX-TDS-007, TAX-TDS-008,
    TAX-PRES-015): verification_status="SOURCE_VERIFICATION_REQUIRED",
    is_active=False, no coded module — the law itself is not yet
    primary-verified.
  - 1 row (TAX-ACM-010): verification_status="VERIFIED" (its Section
    145 legal citation genuinely was primary-sourced) but
    is_active=False and no coded module — blocked on a data-model gap
    (no accounting-method field, Decision 5), not a legal-verification
    gap. `rule_runner_service.get_runnable_tax_rules()` still excludes
    it (is_active=False), so this distinction is display-only, not a
    second execution path.

Run with:  python -m database.seed.seed_tax_rules
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy.orm import Session

from app.extensions import init_engine
from app.models import Base, KnowledgeBaseVersion, Standard, TaxRule
from config import Config

KB_VERSION_LABEL = "0.6.2-tax-v1-round3"

# code, title, source_reference — one Standard row per distinct Income-tax Act, 1961
# section family this catalogue cites. framework is always "IT_ACT_1961" (Decision 1
# — the old Act is the only one FinSight's Tax module verifies/gates against in V1).
STANDARDS = [
    ("IT1961 s.40A(3)", "Expenditure in respect of certain payments otherwise than by account payee cheque, etc.", "Section 40A(3), 40A(3A), Income-tax Act, 1961"),
    ("IT1961 s.269ST", "Mode of undertaking transactions", "Section 269ST, Income-tax Act, 1961"),
    ("IT1961 s.269SS/T", "Mode of taking/accepting and repaying certain loans, deposits and specified sums/advances", "Section 269SS, Section 269T, Income-tax Act, 1961"),
    ("IT1961 s.43B(a-f)", "Certain deductions to be allowed only on actual payment", "Section 43B(a)-(f), Income-tax Act, 1961"),
    ("IT1961 s.43B(h)", "Certain deductions to be allowed only on actual payment — Micro/Small Enterprise dues", "Section 43B(h), Income-tax Act, 1961, read with Section 15, MSMED Act, 2006"),
    ("IT1961 s.44AB", "Audit of accounts of certain persons carrying on business or profession", "Section 44AB, Income-tax Act, 1961"),
    ("IT1961 s.32", "Depreciation", "Section 32, Income-tax Act, 1961, read with Rule 5 and Appendix I"),
    ("IT1961 s.40A(2)", "Expenses or payments not deductible in certain circumstances — payments to specified persons", "Section 40A(2), Income-tax Act, 1961"),
    ("IT1961 s.68-69C", "Cash credits; unexplained investments/money/expenditure", "Section 68, 69, 69A, 69C, Income-tax Act, 1961"),
    ("IT1961 3CD-cap-rev", "Form 3CD — particulars of capital vs revenue expenditure (clause not yet confirmed)", "Form 3CD, Rule 6G, Income-tax Act, 1961 (not researched this stage)"),
    ("IT1961 s.40(a)/36(1)(va)", "Amounts not deductible — TDS default; contributions to employee welfare funds", "Section 40(a)(ia), 40(a)(i), 36(1)(va), Income-tax Act, 1961"),
    ("IT1961 ch.XVIIB", "Collection and recovery of tax — deduction at source", "Chapter XVII-B, Income-tax Act, 1961"),
    ("IT1961 s.44AD/ADA", "Special provision for computing profits and gains on presumptive basis", "Section 44AD, Section 44ADA, Income-tax Act, 1961"),
    ("IT1961 s.145", "Method of accounting", "Section 145, Income-tax Act, 1961"),
]

# rule_id, topic, primary_standard (code above, or None for logic-only), legislative_act,
# provision_reference, applicable_from_ay, description (New Act 2025 forward reference,
# clearly labeled unverified/non-gating), data_required, logic_summary,
# suggested_query_template, risk_level_default, is_active, verification_status,
# verified_source, verified_on, verified_by
RULES = [
    dict(
        rule_id="TAX-CASH-001", topic="Cash Expenditure Disallowance Screen",
        primary_standard="IT1961 s.40A(3)", provision_reference="Section 40A(3), Section 40A(3A), Income-tax Act, 1961",
        applicable_from_ay="AY 2018-19",
        description="New Act 2025 forward reference (UNVERIFIED, non-gating): Section 36. Cross-checked across three independent secondary sources, consistent, but not itself primary-confirmed. Do not treat as confirmed or use to determine executability.",
        data_required='["GL: payment_mode, party_name, debit_amount, credit_amount, transaction_date", "BANK: payment_mode, description, debit_amount, credit_amount, transaction_date"]',
        logic_summary="FinSight Analytical Test — threshold set by the Act itself (exceeds ₹10,000/day/person — a strict inequality, Round 3 correction; exactly ₹10,000 does not trigger a finding), not FinSight: aggregates same-day cash-mode PAYMENTS ONLY (debit_amount side, not receipts) per counterparty across GL/BANK data. Identification of counterparty/cash-mode rows is FinSight's own; GL/Bank double-counting is not deduplicated (disclosed per finding).",
        suggested_query_template="Please confirm the mode of payment and whether any Rule 6DD exception or the transporter carve-out applies.",
        risk_level_default="MEDIUM", is_active=True, verification_status="VERIFIED",
        verified_source="https://www.incometaxindia.gov.in/w/prohibited-transaction-in-cash/limit-on-cash-transactions​",
    ),
    dict(
        rule_id="TAX-CASH-002", topic="Large Cash Receipt Restriction Screen",
        primary_standard="IT1961 s.269ST", provision_reference="Section 269ST, Income-tax Act, 1961",
        applicable_from_ay="AY 2017-18",
        description="New Act 2025 forward reference (UNVERIFIED, non-gating): Section 186. Cross-checked across multiple independent sources, consistent, but not itself primary-confirmed. Do not treat as confirmed or use to determine executability.",
        data_required='["GL/BANK/SALES/AR: payment_mode, party_name, debit_amount, credit_amount, transaction_date"]',
        logic_summary="FinSight Analytical Test — threshold set by the Act itself (₹2,00,000), not FinSight: covers same-day aggregate and single-transaction limbs across GL/BANK/SALES/AR cash-mode RECEIPTS ONLY (credit_amount side, not payments). The 'event/occasion' limb is not implemented; cross-source double-counting is not deduplicated (disclosed per finding).",
        suggested_query_template="Please confirm the mode of receipt, whether any Section 269ST exception applies, and whether this receipt is already covered under Section 269SS.",
        risk_level_default="MEDIUM", is_active=True, verification_status="VERIFIED",
        verified_source="https://www.incometaxindia.gov.in/w/section-269st-9",
    ),
    dict(
        rule_id="TAX-LOAN-003", topic="Cash Loan/Deposit Acceptance & Repayment Restriction Screen",
        primary_standard="IT1961 s.269SS/T", provision_reference="Section 269SS, Section 269T, Income-tax Act, 1961",
        applicable_from_ay="AY (long-standing; ₹2,00,000 PACS/PCARD enhancement from AY 2024-25)",
        description="New Act 2025 forward reference (UNVERIFIED, non-gating): Section 185 (acceptance) / Section 188 (repayment). Cross-checked across three independent sources, consistent, but not itself primary-confirmed. Do not treat as confirmed or use to determine executability.",
        data_required='["GL/JE/AP/AR: account_name, description, party_name, payment_mode, debit_amount, credit_amount"]',
        logic_summary="FinSight Analytical Test — threshold set by the Act itself (₹20,000), not FinSight: keyword-matches GL/JE/AP/AR account name/description for loan/deposit terms (FinSight has no dedicated loans/deposits dataset type, Decision 5), flags matches at or above the threshold. A known clearly-permitted payment mode (e.g. NEFT/RTGS/account-payee cheque) is not flagged at all; a known cash/restricted mode is flagged with higher confidence; an ambiguous or unavailable mode is flagged as Tax Review Required.",
        suggested_query_template="Please confirm whether this transaction is genuinely a loan/deposit under Section 269SS/269T, its actual mode, and whether any statutory exception applies.",
        risk_level_default="MEDIUM", is_active=True, verification_status="VERIFIED",
        verified_source="https://www.incometaxindia.gov.in/w/what-is-the-threshold-limit-for-section-269ss-",
    ),
    dict(
        rule_id="TAX-DIS-006", topic="Statutory Dues Payment-Basis Timing Test",
        primary_standard="IT1961 s.43B(a-f)", provision_reference="Section 43B(a)-(f), Income-tax Act, 1961",
        applicable_from_ay="AY (long-standing)",
        description="New Act 2025 forward reference (UNVERIFIED, non-gating): Section 37. Cross-checked across two independent sources, consistent, but not itself primary-confirmed. Do not treat as confirmed or use to determine executability.",
        data_required='["GL/JE/TB: account_name, description, debit_amount, credit_amount"]',
        logic_summary="FinSight Analytical Test — a FinSight-designed heuristic, not itself a figure the Act specifies: keyword-matches statutory-dues-type accounts (PF, ESI, gratuity, leave encashment, bonus, etc.) and flags a positive net credit (unpaid) balance as of financial year end above a small FinSight noise floor.",
        suggested_query_template="Please confirm the nature of this account and, if it is a Section 43B statutory due, its actual payment date relative to the return-filing due date.",
        risk_level_default="MEDIUM", is_active=True, verification_status="VERIFIED",
        verified_source="https://www.incometaxindia.gov.in/w/section-43b-42",
    ),
    dict(
        rule_id="TAX-AUD-014", topic="Tax Audit Applicability / Turnover-Threshold Test",
        primary_standard="IT1961 s.44AB", provision_reference="Section 44AB, Income-tax Act, 1961",
        applicable_from_ay="AY (current limits; exact Finance Act year of last change not independently pinned down)",
        description="New Act 2025 forward reference (UNVERIFIED, non-gating): Section 63. Reported consistently across several secondary sources but no primary text was reached. Do not treat as confirmed or use to determine executability.",
        data_required='["SALES/GL/TB: turnover computation", "GL/BANK: payment_mode for cash percentage", "EntityProfile.turnover (fallback)"]',
        logic_summary="FinSight Analytical Test — thresholds set by the Act itself (EXCEEDS ₹1cr/₹10cr business, EXCEEDS ₹50L professional — strict inequalities, Round 3 correction; a figure exactly equal to a threshold does not cross it), not FinSight: computes turnover from Sales Register, else GL/TB revenue-keyword accounts, else the Entity Profile's turnover; computes cash-receipt and cash-payment percentages SEPARATELY (not blended, unchanged '≤5%' semantics) — the ₹10cr enhanced business threshold applies only when both sides are determinable and each ≤5%; the business and professional threshold comparisons are now INDEPENDENT findings (Round 3), each raised only when its own threshold is actually crossed, since entity type doesn't distinguish which applies. The professional finding is labeled 'Tax Audit Applicability — Review Required' and explicitly states FinSight does not have enough data to resolve Section 44ADA-related applicability. A ₹75L figure sometimes cited alongside the professional threshold is Section 44ADA's own presumptive-scheme ceiling, not a Section 44AB(b) enhancement, and is shown informationally only.",
        suggested_query_template="Please confirm whether this engagement is a business or specified profession for Section 44AB purposes, the actual turnover figure, and whether a presumptive-scheme election affects audit applicability.",
        risk_level_default="HIGH", is_active=True, verification_status="VERIFIED",
        verified_source="https://www.incometaxindia.gov.in/w/section-44ab-38",
    ),
    dict(
        rule_id="TAX-DEP-005", topic="Tax Depreciation Consistency Review",
        primary_standard="IT1961 s.32", provision_reference="Section 32, Income-tax Act, 1961, read with Rule 5 and Appendix I",
        applicable_from_ay="AY (long-standing rate table and 180-day rule)",
        description="New Act 2025 forward reference (UNVERIFIED, non-gating): Section 33. Cross-checked across two independent sources for the section number and retention of the 180-day rule, but not itself primary-confirmed. Do not treat as confirmed or use to determine executability.",
        data_required='["FIXED_ASSETS: tax_block_of_asset, tax_depreciation_rate, opening_wdv_paise, additions_paise, deletions_paise, closing_wdv_paise, date_put_to_use"]',
        logic_summary="FinSight Analytical Test — the rate table and 180-day rule are the Act's own; the recompute-and-compare mechanism is FinSight's: recomputes expected tax depreciation per asset from its own recorded rate, applying the 180-day half-rate rule to additions, and flags variance against the recorded closing WDV beyond a small FinSight tolerance.",
        suggested_query_template="Please confirm the tax block classification, depreciation rate, and closing WDV computation for this asset, and explain the variance shown.",
        risk_level_default="MEDIUM", is_active=True, verification_status="VERIFIED",
        verified_source="https://www.incometaxindia.gov.in/w/depreciation-rates",
    ),
    dict(
        rule_id="TAX-RPT-004", topic="Related-Party Payment Reasonableness Screen",
        primary_standard="IT1961 s.40A(2)", provision_reference="Section 40A(2), Income-tax Act, 1961",
        applicable_from_ay="AY (long-standing)",
        description="New Act 2025 forward reference (UNVERIFIED, non-gating): unresolved — three independent secondary sources gave three different section numbers. Not asserted here given the conflict; never used to decide executability.",
        data_required='["all dataset_types: party_name (via detect_related_party_candidates), debit_amount, credit_amount"]',
        logic_summary="FinSight Analytical Test — the Act's own test is reasonableness against market value, which FinSight cannot compute: reuses Audit's detect_related_party_candidates() unchanged, filtered to expense-side (debit) rows only.",
        suggested_query_template="Please confirm the actual relationship, if any, between the entity and this counterparty, and whether the payment terms reflect fair market value.",
        risk_level_default="MEDIUM", is_active=True, verification_status="VERIFIED",
        verified_source="https://www.incometaxindia.gov.in/w/section-40a-9",
    ),
    dict(
        rule_id="TAX-GST-009", topic="GST Invoice Reconciliation",
        primary_standard=None, provision_reference=None,
        applicable_from_ay=None,
        description="Logic-only rule — no statutory citation to verify (unchanged classification from the original v0.2 Tax Rule Verification Register). No Income-tax Act provision statutorily mandates this reconciliation; it is standard professional practice, not a compliance requirement.",
        data_required='["SALES/PURCHASE/GST: invoice_number, taxable_value_paise, cgst_paise, sgst_paise, igst_paise"]',
        logic_summary="FinSight Analytical Test — a pure data-reconciliation check, no statutory basis to disclose: compares taxable value and total tax for the same invoice_number across Sales/Purchase/GST sources, flags mismatches beyond a small FinSight tolerance.",
        suggested_query_template="Please explain the discrepancy between the Sales/Purchase register and GST figures for this invoice, and confirm which figure is correct.",
        risk_level_default="LOW", is_active=True, verification_status="VERIFIED",
        verified_source=None,
    ),
    dict(
        rule_id="TAX-MSME-013", topic="MSME Delayed-Payment Review Screen",
        primary_standard="IT1961 s.43B(h)", provision_reference="Section 43B(h), Income-tax Act, 1961, read with Section 15, MSMED Act, 2006",
        applicable_from_ay="AY 2024-25",
        description="New Act 2025 forward reference (UNVERIFIED, non-gating): reported as Section 37(2)(g) by a single secondary source, not cross-checked. Do not treat as confirmed or use to determine executability.",
        data_required='["AP: party_name, transaction_date, debit_amount, credit_amount, description"]',
        logic_summary="FinSight Analytical Test — the 45-day cap is the Act's own (via MSMED Act Section 15); FinSight approximates elapsed days from AP data: computes net AP balance per counterparty and days since last movement, flags balances aged beyond 45 days. FinSight has NO MSME-registration data (Decision 5) — every finding is a candidate for review, never a stated disallowance (Decision 4).",
        suggested_query_template="Please confirm whether this supplier is registered as a Micro or Small Enterprise under the MSMED Act, 2006, the agreed payment term, and the actual payment date.",
        risk_level_default="MEDIUM", is_active=True, verification_status="VERIFIED",
        verified_source="https://www.incometaxindia.gov.in/w/section-43b-42",
    ),
    # --- Gated: SOURCE_VERIFICATION_REQUIRED, is_active=False, no coded module ---
    dict(
        rule_id="TAX-UXC-019", topic="Unexplained/Unsubstantiated Credit Entry Screening Flag",
        primary_standard="IT1961 s.68-69C", provision_reference="Section 68, Section 69, Section 69A, Section 69C, Income-tax Act, 1961",
        applicable_from_ay=None,
        description="Section numbers/existence cross-checked, but verbatim section text was NOT directly fetched from incometaxindia.gov.in during Stage 10 research — flagged for a follow-up direct fetch before this rule can be coded. New Act 2025 forward reference: reported as Sections 102-105 by three sources, conflicting with a fourth claiming unchanged numbering — unresolved conflict.",
        data_required='["GL/JE: account_name, description, debit_amount, credit_amount"]',
        logic_summary=None,
        suggested_query_template=None,
        risk_level_default="MEDIUM", is_active=False, verification_status="SOURCE_VERIFICATION_REQUIRED",
        verified_source=None,
    ),
    dict(
        rule_id="TAX-3CD-011", topic="Capital vs Revenue Expenditure Classification (Form 3CD)",
        primary_standard="IT1961 3CD-cap-rev", provision_reference=None,
        applicable_from_ay=None,
        description="Not researched in the Stage 10 catalogue pass — carried forward unchanged from the original v0.2 Tax Rule Verification Register placeholder rather than silently dropped. Genuinely TBD pending a future verification pass.",
        data_required=None,
        logic_summary=None,
        suggested_query_template=None,
        risk_level_default="MEDIUM", is_active=False, verification_status="SOURCE_VERIFICATION_REQUIRED",
        verified_source=None,
    ),
    dict(
        rule_id="TAX-TDS-007", topic="TDS Non-/Short-Deduction Expense Disallowance Screen",
        primary_standard="IT1961 s.40(a)/36(1)(va)", provision_reference="Section 40(a)(ia), Section 40(a)(i), Section 36(1)(va), Income-tax Act, 1961",
        applicable_from_ay=None,
        description="Existence and general mechanism are well-established, but no Stage 10 research agent quoted verbatim incometaxindia.gov.in text for this specific disallowance provision. Depends on TAX-TDS-008's rate/threshold table (also gated) to know which expenses were TDS-applicable.",
        data_required='["TdsLineItem-equivalent TDS-mapped rows joined against AP/GL expense rows"]',
        logic_summary=None,
        suggested_query_template=None,
        risk_level_default="MEDIUM", is_active=False, verification_status="SOURCE_VERIFICATION_REQUIRED",
        verified_source=None,
    ),
    dict(
        rule_id="TAX-TDS-008", topic="TDS Rate & Threshold Consistency Check",
        primary_standard="IT1961 ch.XVIIB", provision_reference="Chapter XVII-B, Income-tax Act, 1961",
        applicable_from_ay=None,
        description="Candidate rates (194C/194H/194I/194J/194Q) were corroborated across multiple consistent secondary sources but NOT primary-confirmed against incometaxindia.gov.in section text — 'Do not substitute secondary sources for the required primary-source verification' (Decision 3). Two sub-facts ARE primary-verified: Section 206AB/206CCA omitted effective 1 April 2025 (Finance Bill 2025 PDF), and the March TDS deposit due date is 30 April.",
        data_required='["TdsLineItem-equivalent TDS-mapped rows, AP/GL expense rows"]',
        logic_summary=None,
        suggested_query_template=None,
        risk_level_default="MEDIUM", is_active=False, verification_status="SOURCE_VERIFICATION_REQUIRED",
        verified_source=None,
    ),
    dict(
        rule_id="TAX-PRES-015", topic="Presumptive Taxation Declared-Rate Consistency Check",
        primary_standard="IT1961 s.44AD/ADA", provision_reference="Section 44AD, Section 44ADA, Income-tax Act, 1961",
        applicable_from_ay=None,
        description="Threshold figures (₹2cr/₹3cr business, ₹50L/₹75L professional) were primary-fetched, but the exact Finance Act/year that set the CURRENT enhanced limits was not independently pinned down (Decision 3 — kept gated pending that specific effective-date verification, even though the figures themselves are primary-sourced).",
        data_required='["GL/TB/SALES: turnover", "BANK: payment_mode for cash percentage"]',
        logic_summary=None,
        suggested_query_template=None,
        risk_level_default="MEDIUM", is_active=False, verification_status="SOURCE_VERIFICATION_REQUIRED",
        verified_source=None,
    ),
    # --- Gated: VERIFIED (legal citation only) but structurally non-executable — data gap, not a law gap ---
    dict(
        rule_id="TAX-ACM-010", topic="Method of Accounting / ICDS Consistency Flag",
        primary_standard="IT1961 s.145", provision_reference="Section 145, Income-tax Act, 1961",
        applicable_from_ay="AY 2017-18 (ICDS applicability)",
        description="New Act 2025 forward reference (UNVERIFIED, non-gating): Section 276 for 145(1) — single-source only; the ICDS-notification-power sub-clause (145(2)'s equivalent) was not found. Do not treat as confirmed or use to determine executability.",
        data_required='["No accounting-method (cash/mercantile) field exists in EntityProfile — Decision 5, not added this stage"]',
        logic_summary="Not implementable without a new EntityProfile field recording the elected accounting method — flagged, not built, per Decision 5. Legal citation (Section 145(1) text and ICDS applicability) was primary-fetched and is genuinely VERIFIED; is_active=False structurally prevents execution regardless.",
        suggested_query_template=None,
        risk_level_default="MEDIUM", is_active=False, verification_status="VERIFIED",
        verified_source="https://www.incometaxindia.gov.in/income-computation-and-disclosure-standards-icds-1",
    ),
]


def _upsert_standard(session, standards_by_code, code, title, source_reference):
    if code in standards_by_code:
        return standards_by_code[code]
    standard = Standard(framework="IT_ACT_1961", code=code, title=title, source_reference=source_reference)
    session.add(standard)
    return standard


def seed(session: Session) -> None:
    standards_by_code = {s.code: s for s in session.query(Standard).all()}
    for code, title, source_reference in STANDARDS:
        _upsert_standard(session, standards_by_code, code, title, source_reference)
    session.commit()  # assigns standard_id to any newly-added rows before the FK lookups below

    standards_by_code = {s.code: s for s in session.query(Standard).all()}
    existing_rule_ids = {r.rule_id for r in session.query(TaxRule).all()}

    for spec in RULES:
        if spec["rule_id"] in existing_rule_ids:
            continue
        primary_standard = standards_by_code[spec["primary_standard"]] if spec["primary_standard"] else None
        rule = TaxRule(
            rule_id=spec["rule_id"],
            standard_id=primary_standard.standard_id if primary_standard else None,
            topic=spec["topic"],
            description=spec["description"],
            data_required=spec["data_required"],
            logic_summary=spec["logic_summary"],
            risk_level_default=spec["risk_level_default"],
            suggested_action=None,
            suggested_query_template=spec["suggested_query_template"],
            version="1.0",
            effective_date=None,
            is_active=spec["is_active"],
            legislative_act="IT_ACT_1961",
            provision_reference=spec["provision_reference"],
            applicable_from_ay=spec["applicable_from_ay"],
            applicable_to_ay=None,
            verification_status=spec["verification_status"],
            verified_source=spec["verified_source"],
            verified_on="2026-08-24" if spec["verified_source"] or spec["verification_status"] == "VERIFIED" else None,
            verified_by=(
                "FinSight Stage 10 research pass — see documentation/stage10_tax_rule_catalogue_proposal.md"
                if spec["verified_source"] or spec["verification_status"] == "VERIFIED" else None
            ),
        )
        session.add(rule)

    if not session.query(KnowledgeBaseVersion).filter_by(version_label=KB_VERSION_LABEL).first():
        for kb in session.query(KnowledgeBaseVersion).filter_by(is_current=True).all():
            kb.is_current = False
        session.add(KnowledgeBaseVersion(
            version_label=KB_VERSION_LABEL,
            released_at=None,
            notes=(
                "Stage 10 Round 3: Tax Review Engine rule content, second post-approval correction pass. 14 "
                "IT_ACT_1961 standards, 15 tax_rules rows (9 active+VERIFIED+coded, 5 SOURCE_VERIFICATION_REQUIRED+"
                "inactive+uncoded, 1 VERIFIED+inactive+uncoded pending a data-model gap) — same 9-rule executable "
                "scope as Stage 10/Round 2, with two further corrections: (1) CRITICAL — TAX-AUD-014 and "
                "TAX-CASH-001's turnover/aggregate-amount threshold comparisons now use strict 'exceeds' (>) "
                "instead of 'at or above' (>=), so a figure exactly equal to a threshold (₹1cr/₹10cr/₹50L for "
                "TAX-AUD-014, ₹10,000 for TAX-CASH-001) no longer triggers a finding — only a figure strictly "
                "above it does; the 5%-cash-percentage conditions in TAX-AUD-014 are unchanged ('does not exceed' "
                "-> <=). (2) TAX-AUD-014's business (Section 44AB(a)) and professional (Section 44AB(b)) threshold "
                "comparisons are now INDEPENDENT findings, each raised only when its own threshold is crossed; the "
                "professional finding uses a new, dedicated label ('Tax Audit Applicability — Review Required') "
                "and explicitly states FinSight cannot resolve Section 44ADA-related applicability (specified-"
                "profession status, presumptive-scheme election/opt-out, or the ₹75L condition) from current data "
                "— the ₹50L/₹75L statutory figures are unchanged and the ₹75L figure remains informational only. "
                "No schema changes in either round. Every executable rule remains gated to the Income-tax Act, "
                "1961 only (Decision 1); the Income-tax Act, 2025 is carried as unverified, non-gating forward-"
                "reference text only. SEBI rules are not implemented in this stage."
            ),
            is_current=True,
        ))

    session.commit()


def main() -> None:
    engine = init_engine(Config.SQLALCHEMY_DATABASE_URI)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session)
    print("Tax rule content seeded: 14 IT_ACT_1961 standards, 15 tax_rules (9 active+VERIFIED, 6 gated), 1 knowledge_base_versions row.")


if __name__ == "__main__":
    main()
