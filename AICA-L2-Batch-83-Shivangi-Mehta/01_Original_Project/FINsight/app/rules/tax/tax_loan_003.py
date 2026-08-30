"""
TAX-LOAN-003 — Cash Loan/Deposit Acceptance & Repayment Restriction Screen.

Legal provision: Section 269SS (acceptance) and Section 269T
(repayment), Income-tax Act, 1961. No loan, deposit, or specified sum
of ₹20,000 or more (single or aggregate outstanding-plus-fresh) may be
accepted or repaid other than by account-payee cheque/draft/prescribed
electronic mode. Enhanced ₹2,00,000 threshold for Primary Agricultural
Credit Society / Primary Co-operative Agricultural and Rural
Development Bank transactions (not distinguished here — see
Limitation). Exceptions: Government, banking companies, post office
savings banks, co-operative banks, notified institutions, and
transactions where both parties have only agricultural income.

Verification: VERIFIED (old Act, 1961) — primary source: the official
"threshold limit for Section 269SS" FAQ and equivalent Section 269T
text, incometaxindia.gov.in (see documentation/stage10_tax_rule_
catalogue_proposal.md, TAX-LOAN-003). New Act 2025 forward reference
(UNVERIFIED, non-gating): Section 185 (acceptance) / Section 188
(repayment) — cross-checked across three independent sources,
consistent, but not itself primary-confirmed; never used to decide
executability.

FinSight Analytical Test — operationalizes Section 269SS/269T, with a
threshold set by the Act itself (₹20,000), not by FinSight. FinSight
has NO dedicated loans/deposits dataset type (Decision 5 — no new
dataset type added this stage), so loan/deposit transactions are
approximated via a keyword match on GL/JE/AP/AR account name or
description ("loan", "deposit", "advance from", "unsecured loan"), a
heuristic of the same kind Audit's write-off/related-party detectors
already use. A credit-side match is treated as a candidate acceptance
(269SS); a debit-side match is treated as a candidate repayment
(269T).

Payment Mode handling (Round 2 correction — previously every keyword
match at or above ₹20,000 was flagged regardless of mode, with the mode
only noted for context, not used to decide whether to flag at all):
  - Payment Mode present and clearly a restricted/cash mode
    (`is_cash_payment_mode()`) → flagged as a candidate finding
    (`Potential Tax Issue`), same as before.
  - Payment Mode present and clearly a permitted mode (NEFT/RTGS/IMPS/
    UPI/other named electronic transfer, or explicitly "account payee"
    cheque/draft) → NOT flagged at all. Section 269SS/269T only
    restrict cash/non-account-payee-instrument acceptance or
    repayment; a transaction already known to be by a permitted mode
    is not a candidate.
  - Payment Mode present but ambiguous (e.g. a bare "Cheque"/"Draft"
    with no "account payee" qualifier — could be a bearer instrument,
    which the Act does NOT exempt) → flagged as `Tax Review Required`
    (lower confidence than a known-cash match), asking the reviewer to
    confirm whether the instrument was genuinely account-payee.
  - Payment Mode unavailable (GL only carries this field — JE/AP/AR do
    not, per `FILE_TYPE_FIELD_SETS`) → flagged as `Tax Review Required`,
    asking the reviewer to confirm the mode before any conclusion.
This mode classification is FinSight's own, disclosed judgment call —
it is not itself a figure or category the Act defines in these exact
terms.

Limitation: (1) account-name/description keyword matching is FinSight's
own approximation, not a reliable loan/deposit identifier — it will
both miss genuine loan transactions with unclear naming and may flag
unrelated transactions that happen to use these words. (2) Only a
single transaction's amount is checked against ₹20,000 — this does NOT
track aggregate outstanding-plus-fresh balances across the year, which
the Act's own wording also covers. (3) The ₹2,00,000 PACS/PCARD
enhanced threshold is not distinguished — every match uses ₹20,000.
(4) None of the statutory exceptions are evaluated. (5) A "permitted"
mode match is skipped entirely rather than surfaced at a lower risk
level — if FinSight's mode-text matching is wrong (e.g. a mislabeled
or misspelled mode value), a genuinely restricted-mode transaction
could go unflagged; this is a disclosed trade-off, not a silent one.
This rule never states a violation is confirmed — only that the
transaction pattern warrants review against Section 269SS/269T.

Insufficient data: no validated GL, JE, AP, or AR data at all for this
engagement.
"""
from __future__ import annotations

from app.rules import wording
from app.rules.accounting.shared_detectors import is_cash_payment_mode
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.rules.tax.act_transition import describe_act_era
from app.utils.currency import paise_to_display

RULE_ID = "TAX-LOAN-003"
TOPIC = "Cash Loan/Deposit Acceptance & Repayment Restriction Screen"
PROVISION_REFERENCE = "Section 269SS, Section 269T, Income-tax Act, 1961"

LOAN_THRESHOLD_PAISE = 2_000_000  # ₹20,000 — the Act's own figure, not FinSight's
_LOAN_KEYWORDS = ("loan", "deposit", "advance from", "unsecured loan")
_LEDGER_TYPES = ("GL", "JE", "AP", "AR")

# FinSight's own classification of a free-text Payment Mode value into "clearly
# permitted" (Section 269SS/269T never restrict these) — disclosed, not a statutory
# term-for-term list. A bare "cheque"/"draft" with no "account payee" qualifier is
# deliberately NOT included here (see module docstring, Payment Mode handling).
_CLEARLY_PERMITTED_MODE_KEYWORDS = (
    "neft", "rtgs", "imps", "upi", "electronic", "bank transfer", "wire transfer",
    "online transfer", "account payee cheque", "account payee draft",
)


def _classify_payment_mode(payment_mode: str | None) -> str:
    """Returns "cash", "permitted", "ambiguous", or "unknown" — see this
    module's docstring, Payment Mode handling, for what each means and
    how the caller uses it."""
    if not payment_mode or not payment_mode.strip():
        return "unknown"
    if is_cash_payment_mode(payment_mode):
        return "cash"
    mode_lower = payment_mode.strip().lower()
    if any(p in mode_lower for p in _CLEARLY_PERMITTED_MODE_KEYWORDS):
        return "permitted"
    return "ambiguous"


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    ledger_rows = [row for dt in _LEDGER_TYPES for row in dataset.get(dt, [])]
    if not ledger_rows:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped General Ledger, Journal Entries, Accounts Payable, or Accounts "
            "Receivable data is available for this engagement."
        )
        return outcome

    era = describe_act_era(engagement.financial_year)

    for row in ledger_rows:
        v = row.values
        account_name = (v.get("account_name") or "").strip()
        description = (v.get("description") or "").strip()
        party_name = (v.get("party_name") or "").strip()
        haystack = f"{account_name} {description}".strip().lower()
        if not haystack or not any(k in haystack for k in _LOAN_KEYWORDS):
            continue

        debit = v.get("debit_amount") or 0
        credit = v.get("credit_amount") or 0
        amount = max(debit, credit)
        if amount <= 0:
            continue

        outcome.evaluated_count += 1
        if amount < LOAN_THRESHOLD_PAISE:
            continue

        direction = "acceptance (Section 269SS)" if credit >= debit else "repayment (Section 269T)"
        provision = "Section 269SS" if credit >= debit else "Section 269T"
        counterparty = party_name or account_name or description or f"row {row.row_index + 1}"

        payment_mode = v.get("payment_mode")
        mode_classification = _classify_payment_mode(payment_mode)

        if mode_classification == "permitted":
            # Clearly a permitted mode (account-payee cheque/draft or a named
            # electronic transfer) — Section 269SS/269T does not restrict this,
            # so no candidate finding is raised at all (Round 2 correction).
            continue

        if mode_classification == "cash":
            label = wording.POTENTIAL_TAX_ISSUE
            mode_note = f'recorded payment mode "{payment_mode}" (a restricted/cash mode)'
            confidence_note = "FinSight identified"
        elif mode_classification == "ambiguous":
            label = wording.TAX_REVIEW_REQUIRED
            mode_note = (
                f'recorded payment mode "{payment_mode}" — not clearly an account-payee/electronic instrument '
                f"nor clearly cash; please confirm which"
            )
            confidence_note = "FinSight identified a lower-confidence candidate:"
        else:  # "unknown" — no Payment Mode value available in this data source
            label = wording.TAX_REVIEW_REQUIRED
            mode_note = "no Payment Mode field available in this data source — mode could not be determined"
            confidence_note = "FinSight identified a lower-confidence candidate:"

        outcome.exceptions.append(ExceptionDraft(
            label=label,
            area=TOPIC,
            trigger_condition=(
                f'Transaction matching a loan/deposit keyword with "{counterparty}" for {paise_to_display(amount)} '
                f"(candidate {direction}) is at or above the Section 269SS/269T threshold of "
                f"{paise_to_display(LOAN_THRESHOLD_PAISE)}."
            ),
            explanation=(
                f'{era}. Section 269SS/269T restrict accepting or repaying a loan, deposit, or specified sum of '
                f'₹20,000 or more other than by account-payee cheque/draft/prescribed electronic mode. '
                f'{confidence_note} a transaction with "{counterparty}" for {paise_to_display(amount)} whose '
                f'account name or description matched a loan/deposit keyword — a candidate {direction}, based on '
                f"FinSight's own keyword heuristic (FinSight has no dedicated loans/deposits data source). The "
                f"mode of this transaction: {mode_note}. This does NOT establish that Section 269SS/269T was "
                f"contravened — the keyword match may not be a genuine loan/deposit, statutory exceptions may "
                f"apply, and the actual payment mode may not have been cash. This is a potential issue for "
                f"professional review, not a determination that a violation occurred."
            ),
            suggested_query=(
                f'Please confirm whether this transaction with "{counterparty}" is genuinely a loan/deposit under '
                f"Section 269SS/269T, its actual mode of {('acceptance' if credit >= debit else 'repayment')}, and "
                f"whether any statutory exception applies."
            ),
            risk_level="MEDIUM",
            data_sources=[str(row.file_id)],
            threshold_used={
                "loan_threshold_paise": LOAN_THRESHOLD_PAISE,
                "threshold_is_statutory": True,
                "statutory_source": provision,
                "identification_method": "FinSight account-name/description keyword heuristic",
                "payment_mode_determinable": bool(payment_mode),
                "payment_mode_classification": mode_classification,
                "pacs_pcard_enhanced_threshold_applied": False,
            },
            amount_paise=amount,
            related_transaction_id=row.transaction_id,
        ))

    return outcome
