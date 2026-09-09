"""
Accounting rule-pack content bootstrap (Stage 8, revised in Round 2).

Seeds the `standards` and `accounting_rules` tables for the 7 active
rule families implemented under `app/rules/accounting/` (14 rows — one
AS row + one Ind AS row per family), 3 coded-but-deliberately-inactive
families (6 rows — "Future / Not Currently Executable"), and 1 withdrawn
marker row (AS6-DEP-002), plus a new `knowledge_base_versions` row
marking this content current. See `app/rules/accounting/__init__.py`
for the full catalogue rationale.

Stage 8 Round 2 correction #1 (framework-aware execution): every rule
family that can run under both frameworks now has TWO separate
`accounting_rules` rows — one `framework="AS"` (citing the old AS
number), one `framework="IND_AS"` (citing the Ind AS number) — never
one row serving both. `app/services/rule_runner_service.py` selects
only the row matching an engagement's own `accounting_framework`.

Correction #8 (verification_status): a rule's standard mapping and
number/title were checked against primary/authoritative sources during
this round — MCA's Companies (Accounting Standards) Amendment Rules,
2016 (G.S.R. 364(E), AS 6 withdrawal), ICAI's own "Accounting Standards
as on 1st Feb 2022" compendium (AS titles), and each standard's own
text for the AS 5/Ind AS 8 terminology distinction (see AS5-PPI-012's
module docstring) — not merely asserted as "topic-level names are
stable." Every row below is marked VERIFIED on that basis. Paragraph-
level compliance citations are still never asserted anywhere in this
file.

Run with:  python -m database.seed.seed_accounting_rules
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy.orm import Session

from app.extensions import init_engine
from app.models import AccountingRule, Base, KnowledgeBaseVersion, Standard
from config import Config

KB_VERSION_LABEL = "0.4-accounting-v2-framework-aware"

# code, title, source_reference, framework ("AS" or "IND_AS")
STANDARDS = [
    ("AS 2", "Valuation of Inventories", "ICAI Accounting Standard (AS) 2", "AS"),
    ("AS 5", "Net Profit or Loss for the Period, Prior Period Items and Changes in Accounting Policies", "ICAI Accounting Standard (AS) 5", "AS"),
    ("AS 6", "Depreciation Accounting — WITHDRAWN: omitted by the Companies (Accounting Standards) Amendment Rules, 2016 (G.S.R. 364(E), dated 30 March 2016), effective for periods commencing on or after 1 April 2017; provisions incorporated into revised AS 10.", "MCA Companies (Accounting Standards) Amendment Rules, 2016 — G.S.R. 364(E)", "AS"),
    ("AS 10", "Property, Plant and Equipment", "ICAI Accounting Standard (AS) 10 (Revised)", "AS"),
    ("AS 13", "Accounting for Investments", "ICAI Accounting Standard (AS) 13", "AS"),
    ("AS 15", "Employee Benefits", "ICAI Accounting Standard (AS) 15", "AS"),
    ("AS 16", "Borrowing Costs", "ICAI Accounting Standard (AS) 16", "AS"),
    ("AS 18", "Related Party Disclosures", "ICAI Accounting Standard (AS) 18", "AS"),
    ("AS 26", "Intangible Assets", "ICAI Accounting Standard (AS) 26", "AS"),
    ("AS 29", "Provisions, Contingent Liabilities and Contingent Assets", "ICAI Accounting Standard (AS) 29", "AS"),
    ("Ind AS 2", "Inventories", "Companies (Indian Accounting Standards) Rules, 2015 — Ind AS 2", "IND_AS"),
    ("Ind AS 8", "Accounting Policies, Changes in Accounting Estimates and Errors", "Companies (Indian Accounting Standards) Rules, 2015 — Ind AS 8", "IND_AS"),
    ("Ind AS 16", "Property, Plant and Equipment", "Companies (Indian Accounting Standards) Rules, 2015 — Ind AS 16", "IND_AS"),
    ("Ind AS 19", "Employee Benefits", "Companies (Indian Accounting Standards) Rules, 2015 — Ind AS 19", "IND_AS"),
    ("Ind AS 23", "Borrowing Costs", "Companies (Indian Accounting Standards) Rules, 2015 — Ind AS 23", "IND_AS"),
    ("Ind AS 24", "Related Party Disclosures", "Companies (Indian Accounting Standards) Rules, 2015 — Ind AS 24", "IND_AS"),
    ("Ind AS 37", "Provisions, Contingent Liabilities and Contingent Assets", "Companies (Indian Accounting Standards) Rules, 2015 — Ind AS 37", "IND_AS"),
    ("Ind AS 38", "Intangible Assets", "Companies (Indian Accounting Standards) Rules, 2015 — Ind AS 38", "IND_AS"),
    ("Ind AS 109", "Financial Instruments", "Companies (Indian Accounting Standards) Rules, 2015 — Ind AS 109 (broader in scope than AS 13 — see the AS13-INV-005/INDAS109-INV-005 rule description)", "IND_AS"),
]

# ---------------------------------------------------------------------------
# Active rule families (7 families x 2 framework rows = 14 rows)
# ---------------------------------------------------------------------------
_ACTIVE_FAMILIES = [
    dict(
        base_rule_id="AS10-FA-001", ind_rule_id="INDAS16-FA-001",
        as_standard="AS 10", ind_standard="Ind AS 16",
        topic="Fixed Assets — Roll-Forward Consistency Review",
        description=(
            "Fixed Assets: Roll-Forward Consistency Review. Checks whether the entity's own reported roll-forward "
            "(opening WDV + additions - deletions - recorded depreciation = closing WDV) reconciles arithmetically. "
            "Method-agnostic by design — no depreciation method (SLM/WDV/units-of-production) is ever assumed, "
            "since no field in the schema captures which method applies."
        ),
        data_required='["FIXED_ASSETS: opening_wdv_paise, additions_paise, deletions_paise, book_depreciation_amount_paise, closing_wdv_paise"]',
        logic_summary="For each asset, check whether opening WDV + additions - deletions - recorded depreciation reconciles with reported closing WDV, within a small rounding tolerance. Does not assume any specific depreciation method.",
        applicability_preconditions="Engagement has validated, confirmed-mapped Fixed Asset Register data with all five roll-forward fields present for at least one asset.",
        analytical_test="difference = (opening_wdv_paise + additions_paise - deletions_paise - book_depreciation_amount_paise) - closing_wdv_paise; flagged if |difference| exceeds a ₹1 rounding tolerance.",
        expected_result="The reported roll-forward reconciles with the reported closing WDV.",
        suggested_action="Review Required — the reported roll-forward figures do not reconcile arithmetically; this does not itself identify which figure is incorrect or assume any depreciation method.",
        suggested_query_template="Please reconcile the reported roll-forward for [asset] — opening WDV, additions, deletions, and recorded depreciation do not arithmetically produce the reported closing WDV.",
        risk_level_default="MEDIUM",
    ),
    dict(
        base_rule_id="AS26-INT-011", ind_rule_id="INDAS38-INT-011",
        as_standard="AS 26", ind_standard="Ind AS 38",
        topic="Intangible Assets — Roll-Forward Consistency Review",
        description=(
            "Intangible Assets: Roll-Forward Consistency Review. Same method-agnostic roll-forward arithmetic "
            "check as AS10-FA-001/INDAS16-FA-001, restricted to Fixed Asset Register rows tagged "
            "asset_class = \"Intangible\". No amortization method is ever assumed."
        ),
        data_required='["FIXED_ASSETS: asset_class=Intangible, opening_wdv_paise, additions_paise, deletions_paise, book_depreciation_amount_paise, closing_wdv_paise"]',
        logic_summary="Same roll-forward reconciliation check as AS10-FA-001/INDAS16-FA-001, applied to intangible-tagged assets only.",
        applicability_preconditions="Engagement has validated, confirmed-mapped Fixed Asset Register rows tagged asset_class = \"Intangible\" with all five roll-forward fields present.",
        analytical_test="Same identity as AS10-FA-001/INDAS16-FA-001, restricted to intangible-tagged rows.",
        expected_result="The reported roll-forward reconciles with the reported closing WDV.",
        suggested_action="Review Required — the reported roll-forward figures do not reconcile arithmetically; no amortization method is assumed.",
        suggested_query_template="Please reconcile the reported roll-forward for [intangible asset] — opening WDV, additions, deletions, and recorded amortization do not arithmetically produce the reported closing WDV.",
        risk_level_default="LOW",
    ),
    dict(
        base_rule_id="AS10-DEP-002", ind_rule_id="INDAS16-DEP-002",
        as_standard="AS 10", ind_standard="Ind AS 16",
        topic="Depreciation Rate Consistency — Year on Year",
        description=(
            "Depreciation Rate Consistency — Year on Year. Replaces the withdrawn AS6-DEP-002 (AS 6 was withdrawn "
            "by ICAI and its provisions incorporated into revised AS 10 — see the AS 6 Standard row's own "
            "description). Compares average book depreciation rate per asset class against a prior-year "
            "engagement for the same entity — a rate-consistency check, not a claim about which method is used."
        ),
        data_required='["FIXED_ASSETS: asset_class, book_depreciation_rate (current engagement + prior-year engagement, same entity)"]',
        logic_summary="Average book depreciation rate per asset class this year vs. the same class in a prior-year engagement for the same entity; flag any difference.",
        applicability_preconditions="A prior-year engagement exists for the same entity_name (financial_year - 1) with validated Fixed Asset Register data.",
        analytical_test="Average(book_depreciation_rate) grouped by asset_class, current period vs. prior-year engagement.",
        expected_result="Average rate per asset class unchanged year-on-year, or a documented change in estimate/policy.",
        suggested_action="Potential Inconsistency — average rate changed with no policy-note field available to confirm a documented basis.",
        suggested_query_template="Please provide the basis for the change in depreciation rate for asset class [class] (from [rate] to [rate]).",
        risk_level_default="MEDIUM",
    ),
    dict(
        base_rule_id="AS29-PROV-010", ind_rule_id="INDAS37-PROV-010",
        as_standard="AS 29", ind_standard="Ind AS 37",
        topic="Provisions — Significant Movement Review",
        description=(
            "Provisions: Significant Movement Review. Flags a provision movement/reversal exceeding a "
            "CONFIGURABLE FinSight analytical threshold (currently 50% of the prior-year closing balance) as "
            "warranting review of the current best estimate and its supporting basis. The threshold is a "
            "FinSight analytical trigger, not an accounting-standard requirement, and a flagged movement is "
            "never described as an accounting inconsistency."
        ),
        data_required='["TB/GL/JE: account_name (provision-like), debit_amount, credit_amount (current engagement + prior-year engagement, same entity)"]',
        logic_summary="Prior-year closing provision balance vs. current-year net movement on the same account name; flag a movement of 50% or more of the opening balance (a configurable FinSight threshold) for review.",
        applicability_preconditions="A prior-year engagement exists for the same entity with a matching provision-like account and a positive opening balance.",
        analytical_test="movement_amount = max(-(current net credit movement), 0); movement_pct = movement_amount / prior_closing_balance x 100; flagged if movement_pct >= 50 (configurable FinSight threshold, not a standard requirement).",
        expected_result="Movement, if any, below the configurable review threshold, or accompanied by a documented change in the current best estimate.",
        suggested_action="Review Required — Significant Provision Movement. The threshold is a configurable FinSight analytical trigger, not an accounting-standard requirement; this finding does not describe the movement as an accounting inconsistency.",
        suggested_query_template="Please explain the basis for the movement in the provision for [account], including whether it reflects a change in the current best estimate.",
        risk_level_default="MEDIUM",
    ),
    dict(
        base_rule_id="AS16-BC-006", ind_rule_id="INDAS23-BC-006",
        as_standard="AS 16", ind_standard="Ind AS 23",
        topic="Borrowing Costs — Capitalization Review Signal",
        description=(
            "Borrowing Costs: Capitalization Review Signal. Coarse co-occurrence check: flags when a capital-"
            "work-in-progress (CWIP) tagged Fixed Asset Register row and a loan/borrowing-like ledger account are "
            "both present. Explicitly NOT a narration-based guess linking a specific loan to a specific asset, "
            "and explicitly does not establish qualifying-asset status, direct attribution, capitalization-"
            "commencement conditions, or that any actual borrowing cost was capitalized."
        ),
        data_required='["FIXED_ASSETS: asset_class=CWIP; TB/GL/JE: account_name (loan-like), debit_amount, credit_amount"]',
        logic_summary="Flags co-occurrence of a CWIP-tagged asset and a loan/borrowing-like ledger account in the same engagement — a review signal only.",
        applicability_preconditions="At least one Fixed Asset Register row is tagged asset_class = \"CWIP\" (or description contains a CWIP-family keyword).",
        analytical_test="Presence of >=1 CWIP-tagged asset AND >=1 ledger row with a loan-keyword account_name and a nonzero debit/credit.",
        expected_result="No general expectation — this is a relevance/review signal, not a computed variance.",
        suggested_action="Review Required. Co-occurrence signal only — does not establish qualifying-asset status, direct attribution, capitalization-commencement conditions, or actual capitalized borrowing costs.",
        suggested_query_template="Please confirm whether the capital-work-in-progress asset(s) meet the qualifying-asset test, whether any borrowing is directly attributable to them, and whether any borrowing costs were capitalized during this period.",
        risk_level_default="LOW",
    ),
    dict(
        base_rule_id="AS18-RPT-009", ind_rule_id="INDAS24-RPT-009",
        as_standard="AS 18", ind_standard="Ind AS 24",
        topic="Related Party Disclosure — Candidate Identification",
        description=(
            "Related Party Disclosure: Candidate Identification. Flags related-party CANDIDATES via a shared "
            "coarse text heuristic (keyword match / name similarity to the entity's own name) — never asserts "
            "legal related-party status or disclosure adequacy."
        ),
        data_required='["Any mapped row with party_name; engagement.entity_name"]',
        logic_summary="Flags counterparties whose party_name matches a related-party keyword list or closely resembles the entity's own name.",
        applicability_preconditions="At least one mapped row across the dataset has a non-blank party_name value.",
        analytical_test="Keyword match / difflib name-similarity (>=0.6) between party_name and known related-party terms / entity_name.",
        expected_result="No general expectation — candidates are surfaced for professional review, not judged.",
        suggested_action="Potential Inconsistency — candidate identified; relationship and disclosure completeness require professional confirmation.",
        suggested_query_template="Please confirm the relationship, if any, between the entity and [party], and whether related-party disclosures for this counterparty are complete.",
        risk_level_default="MEDIUM",
    ),
    dict(
        base_rule_id="AS5-PPI-012", ind_rule_id="INDAS8-PPE-012",
        as_standard="AS 5", ind_standard="Ind AS 8",
        topic="Prior Period Items / Errors — Narration Keyword Check",
        description=(
            "Prior Period Items (AS 5) / Prior Period Errors (Ind AS 8) — Narration Keyword Check. Plain keyword "
            "match against GL/JE narration text — explicitly a text heuristic, not a determination. AS 5's "
            "\"Prior Period Items\" and Ind AS 8's \"Prior Period Errors\" are each standard's own distinct "
            "defined term, not interchangeable synonyms; the standard reference, explanation, and suggested "
            "query are framework-specific even though the same keyword heuristic is shared."
        ),
        data_required='["GL/JE: description"]',
        logic_summary="Keyword match on GL/JE description/narration text against a fixed list of prior-period-adjustment phrases; terminology (\"item\" vs \"error\") and standard reference are framework-specific.",
        applicability_preconditions="At least one GL/JE row has a non-blank description value.",
        analytical_test="Substring keyword match (case-insensitive) against description.",
        expected_result="No matching narration language (absence does not itself prove no prior period item/error exists).",
        suggested_action="Potential Inconsistency — narration keyword matched; a text heuristic only.",
        suggested_query_template="Please confirm whether this entry represents a prior period item/error under the applicable standard and, if so, how it was disclosed/treated.",
        risk_level_default="LOW",
    ),
]

# ---------------------------------------------------------------------------
# Coded-but-inactive families (3 families x 2 framework rows = 6 rows) —
# "Future / Not Currently Executable", per correction #9.
# ---------------------------------------------------------------------------
_INACTIVE_FAMILIES = [
    dict(
        base_rule_id="AS2-INV-003", ind_rule_id="INDAS2-INV-003",
        as_standard="AS 2", ind_standard="Ind AS 2",
        topic="Inventory Valuation Method — Future / Insufficient Data",
        description=(
            "Inventory Valuation Method. No file type or mapped field in the current FinSight schema captures a "
            "valuation method, cost basis, or net realizable value comparison — this rule always reports "
            "Insufficient Data. Kept coded and in the catalogue for transparency, but seeded inactive "
            "(Future / Not currently executable) rather than activated merely to reach a rule count."
        ),
        data_required='["None available — no INVENTORY dataset type or valuation-method field exists in the current schema"]',
        logic_summary="Always reports Insufficient Data — no inventory valuation-method or NRV field exists anywhere in the current schema.",
        applicability_preconditions="Never met by the current schema.",
        analytical_test="Not computable — no source field exists.",
        expected_result="N/A — Insufficient Data by design until a future stage adds an INVENTORY dataset type.",
        suggested_action="Insufficient Data. Not currently executable.",
        suggested_query_template="N/A — no automated query is generated; this rule never produces an exception.",
        risk_level_default="LOW",
    ),
    dict(
        base_rule_id="AS13-INV-005", ind_rule_id="INDAS109-INV-005",
        as_standard="AS 13", ind_standard="Ind AS 109",
        topic="Investment Valuation & Classification — Future / Insufficient Data",
        description=(
            "Investment Valuation. No file type or mapped field in the current FinSight schema captures "
            "investment classification or a fair-value figure — this rule always reports Insufficient Data. "
            "Seeded inactive (Future / Not currently executable). Note: AS 13 and Ind AS 109 are not a clean "
            "1:1 mapping — Ind AS 109 is far broader in scope (all financial instruments, not just investments), "
            "and the investment-property subset is carved out under Ind AS into Ind AS 40."
        ),
        data_required='["None available — no INVESTMENTS dataset type or classification/fair-value field exists in the current schema"]',
        logic_summary="Always reports Insufficient Data — no investment classification or fair-value field exists anywhere in the current schema.",
        applicability_preconditions="Never met by the current schema.",
        analytical_test="Not computable — no source field exists.",
        expected_result="N/A — Insufficient Data by design until a future stage adds an INVESTMENTS dataset type.",
        suggested_action="Insufficient Data. Not currently executable.",
        suggested_query_template="N/A — no automated query is generated; this rule never produces an exception.",
        risk_level_default="LOW",
    ),
    dict(
        base_rule_id="AS15-EB-008", ind_rule_id="INDAS19-EB-008",
        as_standard="AS 15", ind_standard="Ind AS 19",
        topic="Employee Benefit Provisions — Presence Check (Future)",
        description=(
            "Employee Benefit Provisions. Low-confidence presence/absence check only — an actuarial valuation "
            "would be needed to assess adequacy, which is never available from uploaded ledger data. Coded and "
            "ready, but seeded inactive (Future / Not currently executable) per the \"only strong rules should "
            "be active\" instruction — recommend revisiting if HR/actuarial data becomes an available input."
        ),
        data_required='["TB/GL/JE: account_name"]',
        logic_summary="Checks whether any ledger account name matches common employee-benefit provision keywords (gratuity, leave encashment, etc.).",
        applicability_preconditions="Engagement has validated Trial Balance/General Ledger/Journal Entry data.",
        analytical_test="Keyword match on account_name against a fixed list of employee-benefit-provision terms.",
        expected_result="At least one matching account present (absence is not itself proof no provision exists or is required).",
        suggested_action="Review Required — advisory only, low-confidence presence check, not an adequacy assessment. Not currently executable.",
        suggested_query_template="Please confirm whether provisions for employee benefits (e.g. gratuity, leave encashment) exist, and if so, where they appear in the trial balance/general ledger.",
        risk_level_default="LOW",
    ),
]


def _upsert_standard(session, standards_by_code, code, title, source_reference, framework):
    if code in standards_by_code:
        return standards_by_code[code]
    standard = Standard(framework=framework, code=code, title=title, source_reference=source_reference)
    session.add(standard)
    return standard


def _upsert_rule(session, existing_rule_ids, standards_by_code, *, rule_id, framework, standard_code, spec, is_active, verification_status):
    if rule_id in existing_rule_ids:
        return
    standard = standards_by_code[standard_code]
    session.add(AccountingRule(
        rule_id=rule_id,
        standard_id=standard.standard_id,
        framework=framework,
        topic=spec["topic"],
        description=spec["description"],
        data_required=spec["data_required"],
        logic_summary=spec["logic_summary"],
        risk_level_default=spec["risk_level_default"],
        suggested_action=spec["suggested_action"],
        suggested_query_template=spec["suggested_query_template"],
        version="2.0",
        effective_date=None,
        is_active=is_active,
        applicability_preconditions=spec["applicability_preconditions"],
        analytical_test=spec["analytical_test"],
        expected_result=spec["expected_result"],
        knowledge_base_version=KB_VERSION_LABEL,
        verification_status=verification_status,
    ))


def seed(session: Session) -> None:
    standards_by_code = {s.code: s for s in session.query(Standard).all()}
    for code, title, source_reference, framework in STANDARDS:
        _upsert_standard(session, standards_by_code, code, title, source_reference, framework)
    session.commit()  # assigns standard_id to any newly-added rows before the FK lookups below

    standards_by_code = {s.code: s for s in session.query(Standard).all()}
    existing_rule_ids = {r.rule_id for r in session.query(AccountingRule).all()}

    for spec in _ACTIVE_FAMILIES:
        _upsert_rule(
            session, existing_rule_ids, standards_by_code,
            rule_id=spec["base_rule_id"], framework="AS", standard_code=spec["as_standard"],
            spec=spec, is_active=True, verification_status="VERIFIED",
        )
        _upsert_rule(
            session, existing_rule_ids, standards_by_code,
            rule_id=spec["ind_rule_id"], framework="IND_AS", standard_code=spec["ind_standard"],
            spec=spec, is_active=True, verification_status="VERIFIED",
        )

    for spec in _INACTIVE_FAMILIES:
        _upsert_rule(
            session, existing_rule_ids, standards_by_code,
            rule_id=spec["base_rule_id"], framework="AS", standard_code=spec["as_standard"],
            spec=spec, is_active=False, verification_status="VERIFIED",
        )
        _upsert_rule(
            session, existing_rule_ids, standards_by_code,
            rule_id=spec["ind_rule_id"], framework="IND_AS", standard_code=spec["ind_standard"],
            spec=spec, is_active=False, verification_status="VERIFIED",
        )

    # Withdrawn marker row — single row, AS-only (there was never an "Ind AS 6"),
    # never active, kept purely for catalogue traceability (correction #2).
    if "AS6-DEP-002" not in existing_rule_ids:
        as6 = standards_by_code["AS 6"]
        session.add(AccountingRule(
            rule_id="AS6-DEP-002",
            standard_id=as6.standard_id,
            framework="AS",
            topic="Depreciation Accounting (WITHDRAWN — see AS10-DEP-002)",
            description=(
                "WITHDRAWN. AS 6 (Depreciation Accounting) was withdrawn by ICAI and its provisions incorporated "
                "into revised AS 10 — see the AS 6 Standard row's own description for the source citation. This "
                "rule_id is retained only as a catalogue traceability marker for the pre-Round-2 rule it "
                "replaces; the active depreciation-rate-consistency check now runs as AS10-DEP-002 (AS) / "
                "INDAS16-DEP-002 (Ind AS). This row must never execute."
            ),
            data_required=None,
            logic_summary="Withdrawn — superseded by AS10-DEP-002. No logic runs under this rule_id.",
            risk_level_default="LOW",
            suggested_action="N/A — withdrawn, superseded by AS10-DEP-002.",
            suggested_query_template=None,
            version="2.0",
            effective_date=None,
            is_active=False,
            applicability_preconditions="Never — withdrawn.",
            analytical_test="N/A",
            expected_result="N/A",
            knowledge_base_version=KB_VERSION_LABEL,
            verification_status="VERIFIED",
        ))

    if not session.query(KnowledgeBaseVersion).filter_by(version_label=KB_VERSION_LABEL).first():
        for kb in session.query(KnowledgeBaseVersion).filter_by(is_current=True).all():
            kb.is_current = False
        session.add(KnowledgeBaseVersion(
            version_label=KB_VERSION_LABEL,
            released_at=None,
            notes=(
                "Stage 8 Round 2: framework-aware Accounting Review rule content. 14 active AccountingRule rows "
                "(7 families x AS + Ind AS), 6 coded-but-inactive rows (3 families x AS + Ind AS, Future / Not "
                "Currently Executable), and 1 withdrawn marker row (AS6-DEP-002, superseded by AS10-DEP-002). "
                "AS11-FX-007 still deliberately excluded — pending a schema-change decision (see the Stage 8 "
                "Round 2 report)."
            ),
            is_current=True,
        ))

    session.commit()


def main() -> None:
    engine = init_engine(Config.SQLALCHEMY_DATABASE_URI)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session)
    print("Accounting rule content seeded: 19 standards, 21 accounting_rules (14 active / 6 future / 1 withdrawn), 1 knowledge_base_versions row.")


if __name__ == "__main__":
    main()
