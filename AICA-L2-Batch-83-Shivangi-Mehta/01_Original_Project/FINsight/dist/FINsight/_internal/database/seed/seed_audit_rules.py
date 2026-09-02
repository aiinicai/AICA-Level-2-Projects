"""
Audit rule-pack content bootstrap (Stage 9; extended for the Ledger
Scrutiny pack per the user's explicit further approval).

Seeds the `standards` (9 SA rows — unchanged; the Ledger Scrutiny pack
reuses SA 500/SA 520/SA 240, no new Standard rows needed),
`audit_rules` (25 rows total: the original Stage 9 catalogue of 13, plus
the 12-rule AUD-LS-0xx Ledger Scrutiny pack — AUD-LS-008 was retired at
Stage 21, see `app/rules/audit/__init__.py`'s docstring), and
`audit_rule_assertions` (junction rows, 1-3 per rule) tables, plus a
`knowledge_base_versions` row for each pack revision marking the latest
one current. See
`app/rules/audit/__init__.py` for the full catalogue rationale and
`app/services/rule_runner_service.py` for how these rows gate execution.

Audit is NOT framework-gated (Stage 9 design) — unlike
`seed_accounting_rules.py`, there is no AS/Ind AS row-doubling here:
one `AuditRule` row per rule_id, full stop.

`related_sa` (free text, e.g. "SA 240, SA 330") is the complete,
denormalized SA citation used verbatim in `ExceptionRecord.standard_
reference` at persist time (see `audit_review_service.py`'s module
docstring for why a single `standard_id` FK cannot cleanly hold a
multi-SA citation). `standard_id` on the AuditRule row itself is set to
the PRIMARY/first-listed SA only, for catalogue-display join purposes.

SA verification: SA 240/315/330/500/505/520/540/550/560 titles below
are the ORIGINAL ICAI Clarity Project (2009) titles, confirmed current
as of this stage. "SA 315 (Revised)" and "SA 540 (Revised)" exist only
as unfinalized ICAI exposure drafts (July 2023) as of this stage and
are deliberately NOT used — every reference in this file and in the 13
rule modules cites the original, non-"Revised" title/number.

Post-approval metadata refinement (Stage 9 closure): every rule's
`related_sa` is the AUTHORITATIVE ICAI standard reference only — it
identifies the audit area/context, never a source for this rule's
specific threshold. Every `logic_summary` below is now explicitly
prefixed "FinSight Analytical Test — not prescribed by the cited
SA(s):" for exactly this reason — the presence of an SA citation must
never be read as implying that SA prescribes the FinSight-configurable
threshold or heuristic used to implement the check. Each of the 13
rule modules' own docstrings carries the same explicit two-part
SA Reference / FinSight Analytical Test split; this seed data mirrors
it so the same distinction is visible wherever a rule's metadata is
displayed (the Rule Catalogue screen, this seed data, and the module
source).

Run with:  python -m database.seed.seed_audit_rules
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy.orm import Session

from app.extensions import init_engine
from app.models import AuditAssertion, AuditRule, AuditRuleAssertion, Base, KnowledgeBaseVersion, Standard
from config import Config

KB_VERSION_LABEL = "0.5-audit-v1"
LEDGER_SCRUTINY_KB_VERSION_LABEL = "0.6-audit-ledger-scrutiny-v1"
LEDGER_SCRUTINY_REVISION_KB_VERSION_LABEL = "0.7-audit-ledger-scrutiny-v2"

# code, title (original Clarity Project title — never the unfinalized "(Revised)" exposure draft), source_reference
STANDARDS = [
    ("SA 240", "The Auditor's Responsibilities Relating to Fraud in an Audit of Financial Statements", "ICAI Standard on Auditing (SA) 240"),
    ("SA 315", "Identifying and Assessing the Risks of Material Misstatement Through Understanding the Entity and Its Environment", "ICAI Standard on Auditing (SA) 315"),
    ("SA 330", "The Auditor's Responses to Assessed Risks", "ICAI Standard on Auditing (SA) 330"),
    ("SA 500", "Audit Evidence", "ICAI Standard on Auditing (SA) 500"),
    ("SA 505", "External Confirmations", "ICAI Standard on Auditing (SA) 505"),
    ("SA 520", "Analytical Procedures", "ICAI Standard on Auditing (SA) 520"),
    ("SA 540", "Auditing Accounting Estimates, Including Fair Value Accounting Estimates, and Related Disclosures", "ICAI Standard on Auditing (SA) 540"),
    ("SA 550", "Related Parties", "ICAI Standard on Auditing (SA) 550"),
    ("SA 560", "Subsequent Events", "ICAI Standard on Auditing (SA) 560"),
]

# rule_id, audit_area, related_sa (full citation), primary_sa (for standard_id),
# topic, assertions (tuple of codes), risk_level_default, description,
# data_required, logic_summary, suggested_audit_procedure, suggested_evidence,
# suggested_query_template
RULES = [
    dict(
        rule_id="AUD-JE-001", audit_area="Journal Entry Testing", related_sa="SA 240, SA 330", primary_sa="SA 240",
        topic="Manual Journal Entries Near Year-End", assertions=("OCCURRENCE", "CUT_OFF", "ACCURACY"),
        risk_level_default="HIGH",
        description=(
            "Flags manually-posted journal entries within a FinSight-configurable window of financial year end, "
            "at or above the applicable materiality threshold — a classic SA 240 journal-entry-testing focus "
            "area, not itself evidence of manipulation."
        ),
        data_required='["JE: is_manual_entry, transaction_date, debit_amount, credit_amount (current engagement)"]',
        logic_summary="FinSight Analytical Test — not prescribed by the cited SA(s): manual entries (is_manual_entry truthy) dated within 5 days of financial year end, with amount >= the applicable materiality threshold (Entity Profile Overall Materiality if set, else a FinSight default of ₹1,00,000), are flagged for review.",
        suggested_audit_procedure="Inspect supporting documentation and approval for manual entries posted near year end; corroborate the business rationale.",
        suggested_evidence="Journal voucher, approval record, supporting documentation.",
        suggested_query_template="Please provide supporting documentation and the business rationale for this manual entry posted near financial year end.",
    ),
    dict(
        rule_id="AUD-JE-002", audit_area="Journal Entry Testing", related_sa="SA 240", primary_sa="SA 240",
        topic="Manual Journal Entry Posted on a Non-Business Day", assertions=("OCCURRENCE", "EXISTENCE"),
        risk_level_default="LOW",
        description=(
            "Flags manually-posted journal entries dated on a weekend (Saturday/Sunday). Stage 9 catalogue "
            "review corrected this rule's risk level from Medium to Low/Advisory — a weekend posting is not "
            "inherently suspicious, and the finding text says so explicitly."
        ),
        data_required='["JE: is_manual_entry, transaction_date (current engagement)"]',
        logic_summary="FinSight Analytical Test — not prescribed by the cited SA: manual entries (is_manual_entry truthy) whose transaction_date falls on a Saturday or Sunday are flagged as a low-risk/advisory review item. No posting-timestamp field exists in the schema, so off-hours weekday posting is out of scope, not inferred.",
        suggested_audit_procedure="As a low-risk advisory item, consider whether the weekend posting pattern warrants a brief inquiry as part of routine journal-entry testing.",
        suggested_evidence="Journal voucher, explanation for the posting date.",
        suggested_query_template="Please confirm the reason this manual entry was posted on a non-business day.",
    ),
    dict(
        rule_id="AUD-JE-003", audit_area="Journal Entry Testing", related_sa="SA 240, SA 500", primary_sa="SA 240",
        topic="Round-Sum Manual Entry Above Threshold", assertions=("ACCURACY", "OCCURRENCE"),
        risk_level_default="MEDIUM",
        description=(
            "Flags manually-posted journal entries for a round-sum amount (an exact multiple of ₹10,000) at or "
            "above the applicable materiality threshold — a common journal-entry-testing heuristic, not itself "
            "evidence of an irregular entry."
        ),
        data_required='["JE: is_manual_entry, debit_amount, credit_amount (current engagement)"]',
        logic_summary="FinSight Analytical Test — not prescribed by the cited SA(s): manual entries (is_manual_entry truthy) whose amount is an exact multiple of the FinSight-configurable round-sum denomination (₹10,000) and is at or above the applicable materiality threshold are flagged.",
        suggested_audit_procedure="Inspect supporting documentation for round-sum manual entries above the threshold; corroborate the business rationale.",
        suggested_evidence="Journal voucher, supporting documentation, approval record.",
        suggested_query_template="Please provide supporting documentation for this round-sum manual entry.",
    ),
    dict(
        rule_id="AUD-ACC-004", audit_area="Unusual Account Combinations", related_sa="SA 315, SA 330", primary_sa="SA 315",
        topic="Rare Account Combination", assertions=("CLASSIFICATION", "OCCURRENCE"),
        risk_level_default="MEDIUM",
        description=(
            "Flags a combination of accounts appearing together on a multi-line journal voucher that occurs "
            "rarely (at most once) across the engagement's own journal entries — an SA 315/330 analytical "
            "pattern-testing signal, not a determination that the combination is wrong."
        ),
        data_required='["JE: reference_number, account_name (current engagement, multi-line vouchers only)"]',
        logic_summary="FinSight Analytical Test — not prescribed by the cited SA(s): journal entries grouped by reference_number into multi-line vouchers; the sorted set of account names on each voucher is compared across all vouchers, and combinations occurring at most once (a FinSight-configurable rarity threshold) are flagged, provided at least 5 multi-line vouchers exist to compare against (both the rarity count and the 5-voucher minimum are FinSight-configurable, not SA figures).",
        suggested_audit_procedure="Inspect the rare account combination and its supporting documentation; assess whether it reflects an unusual or non-standard transaction.",
        suggested_evidence="Journal voucher, supporting documentation.",
        suggested_query_template="Please explain the business rationale for this unusual combination of accounts on a single voucher.",
    ),
    dict(
        rule_id="AUD-MOV-005", audit_area="Analytical Review", related_sa="SA 520", primary_sa="SA 520",
        topic="Significant Account Balance Movement vs Prior Year", assertions=("COMPLETENESS", "ACCURACY", "EXISTENCE"),
        risk_level_default="MEDIUM",
        description=(
            "Flags a Trial Balance account whose net balance moved by 25% or more (either direction) compared to "
            "a prior-year engagement for the same entity — SA 520 analytical procedures. Stage 9 catalogue "
            "review downgraded this rule from High to Medium — a 25% movement is an analytical review indicator, "
            "not automatically high risk."
        ),
        data_required='["TB: account_name, debit_amount, credit_amount (current engagement + prior-year engagement, same entity)"]',
        logic_summary="FinSight Analytical Test — not prescribed by SA 520: net balance per account this year vs. the same account in a prior-year engagement; flagged if the absolute percentage change is at or above 25% (a FinSight-configurable analytical threshold, not an SA 520 figure). No account-type field exists to distinguish balance-sheet from P&L accounts, disclosed in every finding.",
        suggested_audit_procedure="Perform analytical review of the movement; obtain explanation and, where relevant, corroborate against supporting schedules.",
        suggested_evidence="Supporting schedule, management explanation, comparative trial balance.",
        suggested_query_template="Please explain the movement in this account balance compared to the prior year and provide any supporting schedule.",
    ),
    dict(
        rule_id="AUD-RPT-006", audit_area="Related Party Transactions", related_sa="SA 550", primary_sa="SA 550",
        topic="Related Party Transaction Candidates", assertions=("PRESENTATION_DISCLOSURE", "RIGHTS_OBLIGATIONS", "OCCURRENCE"),
        risk_level_default="HIGH",
        description=(
            "Flags related-party transaction CANDIDATES via a coarse text heuristic (keyword match / name "
            "similarity to the entity's own name) — the same shared detector AS18-RPT-009 (Accounting) uses. "
            "Never asserts actual related-party status under any legal or accounting definition; this rule "
            "flags candidates only, for professional confirmation."
        ),
        data_required='["Any mapped row with party_name; engagement.entity_name"]',
        logic_summary="FinSight Analytical Test — not prescribed by SA 550: counterparties whose party_name matches a FinSight related-party keyword list, or closely resembles the entity's own name (a FinSight text-similarity heuristic), are flagged as related-party candidates. SA 550 requires the auditor to identify related parties; it does not specify this text-matching method.",
        suggested_audit_procedure="Confirm the actual relationship with the counterparty; if related, evaluate whether the transaction's terms are at arm's length and whether disclosure is complete.",
        suggested_evidence="Related-party declaration, agreement/contract, disclosure note.",
        suggested_query_template="Please confirm the actual relationship, if any, with this counterparty, the terms of the transaction(s), and whether related-party disclosures are complete.",
    ),
    dict(
        rule_id="AUD-SUB-007", audit_area="Subsequent Period Reversals", related_sa="SA 560", primary_sa="SA 560",
        topic="Pre-Year-End Entry Reversed Shortly After", assertions=("OCCURRENCE", "CUT_OFF"),
        risk_level_default="HIGH",
        description=(
            "Flags a pre-year-end journal entry that appears to be reversed by an equal-and-opposite entry on "
            "the same account, either later within the same financial year or shortly after the start of the "
            "following financial year (in a subsequent engagement's own data). The within-period and "
            "subsequent-period halves run and report independently — a missing subsequent-year engagement "
            "blocks only the subsequent-period half, never the within-period half."
        ),
        data_required='["JE: transaction_date, account_name, debit_amount, credit_amount (current engagement, and a subsequent-year engagement for the same entity where available)"]',
        logic_summary="FinSight Analytical Test — not prescribed by SA 560: pre-year-end entries (within 10 days of year end, a FinSight-configurable window) are matched against an equal-and-opposite entry on the same account, either later within the same FY or within 10 days of the start of the following FY (in a subsequent engagement) — both day-counts are FinSight-configurable, not SA 560 figures. A matched pair is a pattern match on account + amount only, never a confirmed determination.",
        suggested_audit_procedure="Inspect the business rationale for the original entry and its apparent reversal; assess the entry's period-matching.",
        suggested_evidence="Journal voucher for both entries, supporting documentation, management explanation.",
        suggested_query_template="Please explain the business rationale for this entry and its apparent reversal shortly after.",
    ),
    dict(
        rule_id="AUD-CUT-013", audit_area="Revenue Cut-off", related_sa="SA 240, SA 315, SA 500", primary_sa="SA 240",
        topic="Revenue Cut-off", assertions=("CUT_OFF", "OCCURRENCE"),
        risk_level_default="HIGH",
        description=(
            "Flags Sales transactions dated within a FinSight-configurable proximity window (7 days) either "
            "side of financial year end — a cut-off review indicator, not itself a determination that the "
            "transaction is recorded in the wrong period."
        ),
        data_required='["SALES: transaction_date, debit_amount, credit_amount (current engagement)"]',
        logic_summary="FinSight Analytical Test — not prescribed by the cited SA(s): sales transactions dated within 7 days before or after financial year end (a FinSight-configurable window, not an SA figure) are flagged for cut-off review.",
        suggested_audit_procedure="Inspect dispatch/delivery or service-completion evidence to confirm the period the transaction belongs to.",
        suggested_evidence="Dispatch/delivery note, service-completion evidence, sales invoice.",
        suggested_query_template="Please provide dispatch/delivery or service-completion evidence for this transaction to confirm the period it belongs to.",
    ),
    dict(
        rule_id="AUD-REV-008", audit_area="Unusual Revenue Transactions", related_sa="SA 240, SA 315", primary_sa="SA 240",
        topic="Revenue Entry With No Matching Receivable", assertions=("EXISTENCE", "COMPLETENESS"),
        risk_level_default="MEDIUM",
        description=(
            "Flags a Sales transaction with no matching Accounts Receivable entry for the same (normalized) "
            "party name and a comparable amount, within a FinSight-configurable date-proximity window. A "
            "heuristic party-name-and-amount match, not a true invoice-level reconciliation."
        ),
        data_required='["SALES and AR: party_name, transaction_date, debit_amount, credit_amount (current engagement)"]',
        logic_summary="FinSight Analytical Test — not prescribed by the cited SA(s): each Sales row is matched against Accounts Receivable rows by normalized party name and amount within a small, FinSight-configurable date and amount tolerance; an unmatched Sales row is flagged.",
        suggested_audit_procedure="Trace the sale to underlying dispatch/service evidence and to the receivables ledger or subsequent collection.",
        suggested_evidence="Dispatch/service evidence, receivables ledger extract, collection evidence.",
        suggested_query_template="Please trace this sale to underlying dispatch/service evidence and to the receivables ledger or subsequent collection.",
    ),
    dict(
        rule_id="AUD-EST-009", audit_area="Significant Estimates", related_sa="SA 540", primary_sa="SA 540",
        topic="Significant Estimate-Linked Account Movement", assertions=("VALUATION", "ACCURACY"),
        risk_level_default="HIGH",
        description=(
            "Flags a provision/reserve/allowance/impairment/estimate-linked account whose net balance moved by "
            "30% or more (either direction) compared to a prior-year engagement for the same entity — a "
            "movement signal for estimate review, not a judgment on the estimate's methodology or assumptions."
        ),
        data_required='["GL/JE/TB: account_name (estimate-linked keyword), debit_amount, credit_amount (current engagement + prior-year engagement, same entity)"]',
        logic_summary="FinSight Analytical Test — not prescribed by SA 540: net balance per estimate-linked-keyword account this year vs. the same account in a prior-year engagement; flagged if the absolute percentage change is at or above 30% (a FinSight-configurable analytical threshold, not an SA 540 figure), in either direction.",
        suggested_audit_procedure="Evaluate the methodology, key assumptions, and data used by management; consider whether an expert should be involved.",
        suggested_evidence="Management working paper, basis note.",
        suggested_query_template="Please provide the methodology and key assumptions supporting this estimate.",
    ),
    dict(
        rule_id="AUD-CASH-010", audit_area="Material Cash Transaction Review", related_sa="SA 240, SA 500", primary_sa="SA 240",
        topic="Material Cash Transaction Review", assertions=("EXISTENCE", "OCCURRENCE"),
        risk_level_default="MEDIUM",
        description=(
            "Flags a Bank Statement transaction recorded with a cash payment mode at or above the applicable "
            "materiality threshold. Renamed from the original catalogue proposal's \"Unusual Cash Movements\" "
            "per Stage 9 review — the wording must not imply that a material cash transaction is inherently "
            "unusual or inappropriate."
        ),
        data_required='["BANK: payment_mode, debit_amount, credit_amount (current engagement)"]',
        logic_summary="FinSight Analytical Test — not prescribed by the cited SA(s): Bank Statement rows with a cash payment mode (payment_mode contains \"cash\", case-insensitive) and an amount at or above the applicable materiality threshold are flagged as warranting review.",
        suggested_audit_procedure="Obtain explanation and supporting documentation; corroborate with bank records and cash book.",
        suggested_evidence="Bank statement, cash book, explanation.",
        suggested_query_template="Please provide the explanation and supporting documentation for this cash transaction.",
    ),
    dict(
        rule_id="AUD-WO-011", audit_area="Large Write-offs", related_sa="SA 240, SA 500", primary_sa="SA 240",
        topic="Large Write-offs", assertions=("VALUATION", "EXISTENCE", "RIGHTS_OBLIGATIONS"),
        risk_level_default="HIGH",
        description=(
            "Flags a General Ledger/Journal Entry/Trial Balance row whose account name or description matches a "
            "write-off/bad-debt/waiver keyword, at or above the applicable materiality threshold — a keyword-"
            "and-amount screen, not a conclusion about approval adequacy or recoverability."
        ),
        data_required='["GL/JE/TB: account_name, description, debit_amount, credit_amount (current engagement)"]',
        logic_summary="FinSight Analytical Test — not prescribed by the cited SA(s): rows whose account_name or description contains a FinSight write-off/bad-debt/waiver keyword, and whose amount is at or above the applicable materiality threshold, are flagged.",
        suggested_audit_procedure="Inspect approval and rationale; assess recoverability efforts undertaken prior to write-off.",
        suggested_evidence="Approval record, recovery correspondence.",
        suggested_query_template="Please provide the approval record and details of recovery efforts undertaken prior to this write-off.",
    ),
    dict(
        rule_id="AUD-LOB-012", audit_area="Long Outstanding Balances", related_sa="SA 500, SA 505", primary_sa="SA 500",
        topic="Long Outstanding Balances", assertions=("EXISTENCE", "VALUATION", "RIGHTS_OBLIGATIONS"),
        risk_level_default="MEDIUM",
        description=(
            "Flags an Accounts Receivable/Payable party balance with no recorded movement for 180 days or more "
            "as of financial year end, above a small noise floor. No due-date or invoice-date field exists in "
            "the schema, so ageing is approximated as days since the party's last recorded movement, not true "
            "per-invoice ageing — disclosed in every finding."
        ),
        data_required='["AR/AP: party_name, transaction_date, debit_amount, credit_amount (current engagement)"]',
        logic_summary="FinSight Analytical Test — not prescribed by SA 500 or SA 505: net outstanding balance per party as of financial year end (AR: debit - credit; AP: credit - debit), with ageing measured as days since that party's last recorded transaction_date on or before year end; flagged if ageing >= 180 days (FinSight-configurable) and the balance is at or above a small, FinSight-configurable minimum-outstanding floor (₹1,000). SA 505 governs how a confirmation, if performed, is designed/evaluated — it does not set this ageing threshold.",
        suggested_audit_procedure="Consider external confirmation (per SA 505) or inspect subsequent realization/settlement evidence.",
        suggested_evidence="Confirmation reply, subsequent receipt/payment.",
        suggested_query_template="Please provide the status of this outstanding balance — a confirmation, or evidence of subsequent realization/settlement.",
    ),
]

# Ledger Scrutiny pack — added per the user's explicit further approval,
# on top of the 13-rule cap set at Stage 9. Adapted from a user-provided
# ledger-scrutiny prototype (15 checks; 2 excluded as duplicates of
# AUD-JE-002/existing materiality rules — see
# app/rules/audit/ledger_scrutiny_shared.py). Reuses SA 500 and SA 520,
# both already seeded above; no new Standard rows needed.
#
# Stage 21 revision: AUD-LS-008 ("Month-End Transaction") is retired —
# removed from this list at the user's explicit request (see
# app/rules/audit/__init__.py's docstring for the rationale). Its
# rule_id is never reused. 12 rules remain in this pack (was 13).
LEDGER_SCRUTINY_RULES = [
    dict(
        rule_id="AUD-LS-001", audit_area="Ledger Scrutiny", related_sa="SA 500", primary_sa="SA 500",
        topic="Ledger Scrutiny — Missing Narration", assertions=("COMPLETENESS", "ACCURACY"),
        risk_level_default="MEDIUM",
        description="Flags a General Ledger/Journal Entry/Bank Statement row whose narration/description is blank.",
        data_required='["GL/JE/BANK: description (current engagement)"]',
        logic_summary="FinSight Analytical Test — not prescribed by SA 500: a row whose description field is blank or whitespace-only is flagged.",
        suggested_audit_procedure="Obtain the narration/description and supporting documents for the entry.",
        suggested_evidence="Voucher, supporting narration.",
        suggested_query_template="Please obtain the narration/description and supporting documents for this entry.",
    ),
    dict(
        rule_id="AUD-LS-002", audit_area="Ledger Scrutiny", related_sa="SA 500", primary_sa="SA 500",
        topic="Ledger Scrutiny — Generic Narration", assertions=("COMPLETENESS", "ACCURACY"),
        risk_level_default="LOW",
        description="Flags a General Ledger/Journal Entry/Bank Statement row whose narration matches a generic-term/short-narration heuristic.",
        data_required='["GL/JE/BANK: description (current engagement)"]',
        logic_summary="FinSight Analytical Test — not prescribed by SA 500: a non-blank description matching a FinSight generic-term word list, or 6 characters or fewer with no digit, is flagged.",
        suggested_audit_procedure="Confirm the business purpose and supporting documents for the entry.",
        suggested_evidence="Voucher, supporting narration.",
        suggested_query_template="Please confirm the business purpose and supporting documents for this entry.",
    ),
    dict(
        rule_id="AUD-LS-003", audit_area="Ledger Scrutiny", related_sa="SA 240, SA 500", primary_sa="SA 240",
        topic="Ledger Scrutiny — Potential Duplicate Transactions", assertions=("OCCURRENCE", "ACCURACY"),
        risk_level_default="HIGH",
        description="Flags General Ledger/Journal Entry/Bank Statement rows sharing an identical date, account/party, amount, and narration.",
        data_required='["GL/JE/BANK: transaction_date, account_name, party_name, debit_amount, credit_amount, description (current engagement)"]',
        logic_summary="FinSight Analytical Test — not prescribed by the cited SA(s): rows are grouped by an exact-match key (date, account/party, amount, narration); every row in a group of 2 or more is flagged.",
        suggested_audit_procedure="Verify against supporting invoice/voucher to confirm this is not a duplicate entry.",
        suggested_evidence="Invoice, voucher.",
        suggested_query_template="Please verify against supporting invoice/voucher to confirm this is not a duplicate entry.",
    ),
    dict(
        rule_id="AUD-LS-004", audit_area="Ledger Scrutiny", related_sa="SA 500", primary_sa="SA 500",
        topic="Ledger Scrutiny — Zero, Negative, or Dual-Sided Amount", assertions=("ACCURACY", "EXISTENCE"),
        risk_level_default="MEDIUM",
        description="Flags a General Ledger/Journal Entry/Bank Statement row where both Debit and Credit are zero, either side is negative, or both sides are populated at once.",
        data_required='["GL/JE/BANK: debit_amount, credit_amount (current engagement)"]',
        logic_summary="FinSight Analytical Test — not prescribed by SA 500: a row is flagged if Debit and Credit are both zero, either is negative, or both are non-zero simultaneously.",
        suggested_audit_procedure="Confirm the entry was posted correctly and obtain the supporting voucher.",
        suggested_evidence="Voucher, correction record if applicable.",
        suggested_query_template="Please confirm this entry was posted correctly and provide the supporting voucher.",
    ),
    dict(
        rule_id="AUD-LS-005", audit_area="Ledger Scrutiny", related_sa="SA 240, SA 500", primary_sa="SA 240",
        topic="Ledger Scrutiny — Round-Number Transaction", assertions=("ACCURACY", "VALUATION"),
        risk_level_default="LOW",
        description="Flags a General Ledger/Journal Entry/Bank Statement row whose amount is an exact multiple of a FinSight round-number denomination (₹5,000).",
        data_required='["GL/JE/BANK: debit_amount, credit_amount (current engagement)"]',
        logic_summary="FinSight Analytical Test — not prescribed by the cited SA(s): a non-zero amount that is an exact multiple of ₹5,000 (FinSight-configurable) is flagged.",
        suggested_audit_procedure="Confirm the basis on which this round-figure amount was arrived at.",
        suggested_evidence="Voucher, supporting calculation.",
        suggested_query_template="Please confirm the basis on which this round-figure amount was arrived at.",
    ),
    dict(
        rule_id="AUD-LS-006", audit_area="Ledger Scrutiny", related_sa="SA 520", primary_sa="SA 520",
        topic="Ledger Scrutiny — Unusual Amount vs Ledger Pattern", assertions=("ACCURACY", "VALUATION"),
        risk_level_default="MEDIUM",
        description="Flags a row whose amount deviates from its own account's mean by more than 2 standard deviations, where the account has 3 or more rows.",
        data_required='["GL/JE/BANK: account_name, debit_amount, credit_amount (current engagement)"]',
        logic_summary="FinSight Analytical Test — not prescribed by SA 520: within each account with 3 or more rows (FinSight-configurable), a row whose amount is more than 2 standard deviations (FinSight-configurable) from that account's own mean is flagged.",
        suggested_audit_procedure="Explain the reason for this entry's unusual amount relative to this ledger's normal pattern.",
        suggested_evidence="Voucher, explanation.",
        suggested_query_template="Please explain the reason for this entry's unusual amount relative to this ledger's normal pattern.",
    ),
    dict(
        rule_id="AUD-LS-007", audit_area="Ledger Scrutiny", related_sa="SA 240, SA 500", primary_sa="SA 240",
        topic="Ledger Scrutiny — Possible Split Transactions", assertions=("OCCURRENCE", "ACCURACY"),
        risk_level_default="HIGH",
        description="Flags same-party, same-date rows each individually below the applicable materiality threshold whose combined total meets or exceeds it.",
        data_required='["GL/JE/BANK: party_name/account_name, transaction_date, debit_amount, credit_amount (current engagement)"]',
        logic_summary="FinSight Analytical Test — not prescribed by the cited SA(s): rows are grouped by same party and same transaction date; a group of 2 or more rows, each below the applicable materiality threshold but totalling at or above it, has every row flagged.",
        suggested_audit_procedure="Confirm whether same-day entries represent separate transactions or a single transaction recorded in parts.",
        suggested_evidence="Invoices/vouchers for each entry in the group.",
        suggested_query_template="Please confirm whether these same-day entries represent separate transactions or a single transaction recorded in parts, and provide the supporting invoices/vouchers.",
    ),
    dict(
        rule_id="AUD-LS-009", audit_area="Ledger Scrutiny", related_sa="SA 240, SA 520", primary_sa="SA 240",
        topic="Ledger Scrutiny — Year-End Transaction", assertions=("CUT_OFF",),
        risk_level_default="MEDIUM",
        description="Flags a General Ledger/Journal Entry/Bank Statement row dated within the last 3 days of the engagement's financial year.",
        data_required='["GL/JE/BANK: transaction_date (current engagement); engagement.financial_year"]',
        logic_summary="FinSight Analytical Test — not prescribed by the cited SA(s): a row dated within the last 3 days (FinSight-configurable) of the engagement's financial year (1 April - 31 March convention) is flagged.",
        suggested_audit_procedure="Confirm the business rationale and cut-off treatment of this year-end entry.",
        suggested_evidence="Voucher, cut-off working paper.",
        suggested_query_template="Please confirm the business rationale and cut-off treatment of this year-end entry.",
    ),
    dict(
        rule_id="AUD-LS-010", audit_area="Ledger Scrutiny", related_sa="SA 240, SA 500", primary_sa="SA 240",
        topic="Ledger Scrutiny — Risk Indicator Keywords", assertions=("OCCURRENCE", "CLASSIFICATION"),
        risk_level_default="MEDIUM",
        description="Flags a row whose account name or description matches a FinSight risk-indicator keyword list.",
        data_required='["GL/JE/BANK: account_name, description (current engagement)"]',
        logic_summary="FinSight Analytical Test — not prescribed by the cited SA(s): a row whose account name or description contains one of FinSight's own risk-indicator keywords (e.g. personal, penalty, donation, cash, loan, advance, director, relative, gift, fine, adjustment, reversal) is flagged.",
        suggested_audit_procedure="Obtain the business rationale and supporting documents for the entry.",
        suggested_evidence="Voucher, supporting documents.",
        suggested_query_template="Please provide the business rationale and supporting documents for this entry.",
    ),
    dict(
        rule_id="AUD-LS-011", audit_area="Ledger Scrutiny", related_sa="SA 520", primary_sa="SA 520",
        topic="Ledger Scrutiny — Repeated Party Transactions", assertions=("OCCURRENCE",),
        risk_level_default="LOW",
        description="Flags every row for a party with more than 2 entries in the same calendar month.",
        data_required='["GL/JE/BANK: party_name/account_name, transaction_date (current engagement)"]',
        logic_summary="FinSight Analytical Test — not prescribed by SA 520: rows are grouped by party and calendar month; every row in a group with more than 2 entries (FinSight-configurable) is flagged.",
        suggested_audit_procedure="Confirm the nature of the relationship and the business reason for this transaction frequency.",
        suggested_evidence="Party ledger, correspondence.",
        suggested_query_template="Please confirm the nature of the relationship with this party and the business reason for this transaction frequency.",
    ),
    dict(
        rule_id="AUD-LS-012", audit_area="Ledger Scrutiny", related_sa="SA 520", primary_sa="SA 520",
        topic="Ledger Scrutiny — Unusual Ledger Activity", assertions=("ACCURACY", "VALUATION", "COMPLETENESS"),
        risk_level_default="MEDIUM",
        description="Flags a month's activity on an account that is either more than twice that account's average monthly total, or less than half its median monthly total (with 3+ other months of history), in its other months, where the account has 2 or more months of activity.",
        data_required='["GL/JE/BANK: account_name, transaction_date, debit_amount, credit_amount (current engagement)"]',
        logic_summary="FinSight Analytical Test — not prescribed by SA 520: within each account with activity in 2 or more months (FinSight-configurable), a month whose total exceeds 2x (FinSight-configurable) the average of that account's other months is flagged as unusually high; separately, with 3 or more other months of history, a month whose total is less than half the MEDIAN of that account's other months is flagged as unusually low (median rather than mean, and a 3-month minimum, specifically so a single large month does not itself drag every other month's baseline down into a false 'too low' reading).",
        suggested_audit_procedure="Explain the reason for the unusually high or unusually low activity on this account in this month, and confirm all expected entries have been recorded.",
        suggested_evidence="Voucher, explanation.",
        suggested_query_template="Please explain the reason for the unusual activity on this account in this month.",
    ),
    dict(
        rule_id="AUD-LS-013", audit_area="Ledger Scrutiny", related_sa="SA 520", primary_sa="SA 520",
        topic="Ledger Scrutiny — Unusual Ledger Usage", assertions=("OCCURRENCE", "CLASSIFICATION"),
        risk_level_default="LOW",
        description="Flags a party's one-off use of a ledger account, where that party has 5 or more total transactions across 2 or more distinct accounts.",
        data_required='["GL/JE/BANK: party_name, account_name (current engagement)"]',
        logic_summary="FinSight Analytical Test — not prescribed by SA 520: for a party with 5 or more total transactions (FinSight-configurable) across 2 or more distinct accounts (FinSight-configurable), an account used by that party only once is flagged.",
        suggested_audit_procedure="Confirm the business reason this party used this account on this one occasion.",
        suggested_evidence="Voucher, explanation.",
        suggested_query_template="Please confirm the business reason this party used this account on this one occasion.",
    ),
]


def _upsert_standard(session, standards_by_code, code, title, source_reference):
    if code in standards_by_code:
        return standards_by_code[code]
    standard = Standard(framework="SA", code=code, title=title, source_reference=source_reference)
    session.add(standard)
    return standard


def seed(session: Session) -> None:
    standards_by_code = {s.code: s for s in session.query(Standard).all()}
    for code, title, source_reference in STANDARDS:
        _upsert_standard(session, standards_by_code, code, title, source_reference)
    session.commit()  # assigns standard_id to any newly-added rows before the FK lookups below

    standards_by_code = {s.code: s for s in session.query(Standard).all()}
    assertions_by_code = {a.code: a for a in session.query(AuditAssertion).all()}
    existing_rule_ids = {r.rule_id for r in session.query(AuditRule).all()}

    def _insert_rules(specs):
        for spec in specs:
            if spec["rule_id"] in existing_rule_ids:
                continue
            primary_standard = standards_by_code[spec["primary_sa"]]
            rule = AuditRule(
                rule_id=spec["rule_id"],
                standard_id=primary_standard.standard_id,
                topic=spec["topic"],
                description=spec["description"],
                data_required=spec["data_required"],
                logic_summary=spec["logic_summary"],
                risk_level_default=spec["risk_level_default"],
                suggested_action=None,
                suggested_query_template=spec["suggested_query_template"],
                version="1.0",
                effective_date=None,
                is_active=True,
                related_sa=spec["related_sa"],
                audit_area=spec["audit_area"],
                suggested_audit_procedure=spec["suggested_audit_procedure"],
                suggested_evidence=spec["suggested_evidence"],
                verification_status="VERIFIED",
            )
            session.add(rule)
            session.flush()  # rule_id is the PK already known, but keeps ordering explicit before the junction inserts

            for assertion_code in spec["assertions"]:
                assertion = assertions_by_code[assertion_code]
                session.add(AuditRuleAssertion(rule_id=rule.rule_id, assertion_id=assertion.assertion_id))
            existing_rule_ids.add(spec["rule_id"])

    _insert_rules(RULES)
    _insert_rules(LEDGER_SCRUTINY_RULES)

    if not session.query(KnowledgeBaseVersion).filter_by(version_label=KB_VERSION_LABEL).first():
        for kb in session.query(KnowledgeBaseVersion).filter_by(is_current=True).all():
            kb.is_current = False
        session.add(KnowledgeBaseVersion(
            version_label=KB_VERSION_LABEL,
            released_at=None,
            notes=(
                "Stage 9: Audit Review Engine rule content. 9 SA standards, 13 active AuditRule rows (the "
                "full Stage 9 catalogue, reviewed and approved — no rule beyond these 13), and their "
                "audit_rule_assertions junction rows. Audit is not framework-gated. Tax and SEBI rules are "
                "not implemented in this stage."
            ),
            is_current=True,
        ))

    if not session.query(KnowledgeBaseVersion).filter_by(version_label=LEDGER_SCRUTINY_KB_VERSION_LABEL).first():
        for kb in session.query(KnowledgeBaseVersion).filter_by(is_current=True).all():
            kb.is_current = False
        session.add(KnowledgeBaseVersion(
            version_label=LEDGER_SCRUTINY_KB_VERSION_LABEL,
            released_at=None,
            notes=(
                "Ledger Scrutiny pack: 13 additional AuditRule rows (AUD-LS-001 through AUD-LS-013), added "
                "on top of the Stage 9 catalogue per the user's explicit further approval, adapted from a "
                "user-provided ledger-scrutiny prototype (2 of its 15 checks excluded as duplicates of "
                "existing rules). Reuses SA 500/SA 520/SA 240 standards already seeded above; no new "
                "Standard rows. 26 AuditRule rows active in total."
            ),
            is_current=True,
        ))

    if not session.query(KnowledgeBaseVersion).filter_by(version_label=LEDGER_SCRUTINY_REVISION_KB_VERSION_LABEL).first():
        for kb in session.query(KnowledgeBaseVersion).filter_by(is_current=True).all():
            kb.is_current = False
        session.add(KnowledgeBaseVersion(
            version_label=LEDGER_SCRUTINY_REVISION_KB_VERSION_LABEL,
            released_at=None,
            notes=(
                "Ledger Scrutiny pack revision (Stage 21, both changes explicitly approved by the user): "
                "AUD-LS-008 (Month-End Transaction) is retired — its rule_id is never reused, and its "
                "AuditRule row is simply no longer inserted by this script on a fresh install. AUD-LS-012 "
                "(Unusual Ledger Activity) is extended to also flag a month whose activity is unusually LOW "
                "versus that account's other months (previously it only flagged unusually HIGH months). "
                "25 AuditRule rows active in total (was 26)."
            ),
            is_current=True,
        ))

    session.commit()


def main() -> None:
    engine = init_engine(Config.SQLALCHEMY_DATABASE_URI)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session)
    print("Audit rule content seeded: 9 SA standards, 25 audit_rules (all active), audit_rule_assertions junction rows, 3 knowledge_base_versions rows.")


if __name__ == "__main__":
    main()
