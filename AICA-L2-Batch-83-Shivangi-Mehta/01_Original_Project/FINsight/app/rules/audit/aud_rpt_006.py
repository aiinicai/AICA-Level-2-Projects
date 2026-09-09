"""
AUD-RPT-006 — Related Party Transaction Candidates.

Audit area: Related Party Transactions. Relevant SA: SA 550 (Related
Parties). Assertions: Presentation/Disclosure, Rights & Obligations,
Occurrence.

SA Reference (authoritative — ICAI Standard on Auditing): SA 550. This
citation identifies related-party audit procedures as the context this
check informs; it does NOT mean SA 550 prescribes the keyword list or
name-similarity heuristic below — SA 550 requires the auditor to
identify related parties and evaluate related-party transactions, but
specifies no automated text-matching method for candidate
identification; that method is entirely FinSight's own.
FinSight Analytical Test (created by FinSight, not prescribed by any
SA): flag a counterparty whose name matches a fixed related-party
keyword list, or closely resembles the engagement's own entity name
(text-similarity heuristic, threshold currently 0.6 —
`_NAME_SIMILARITY_THRESHOLD`, defined in `shared_detectors.py`). No
amount threshold is applied.

Reuses `shared_detectors.detect_related_party_candidates()` AS-IS — the
same detector AS18-RPT-009 (Accounting) already uses — per Blueprint
Section 1.1's "centralize detection once, each module interprets it"
principle. Only the interpretive wrapper differs: AS18-RPT-009 asks
whether the accounting treatment/disclosure is framework-consistent;
this rule asks whether the transaction warrants audit attention
regarding SA 550's related-party procedures.

What data is required: any mapped row with `party_name`; the
engagement's own `entity_name`.
What can actually be established: whether a party name matches a coarse
keyword list or closely resembles the engagement's own name — exactly
the same heuristic AS18-RPT-009 uses, no more.
What cannot be established, and MUST NOT be inferred: actual
related-party status under any legal definition. This rule flags
CANDIDATES ONLY — it never asserts that a counterparty is, in fact, a
related party (the user's Stage 9 instruction: "Do not infer
related-party status from text matching").
Insufficient data: no row anywhere in the dataset has a `party_name`
value at all.
"""
from __future__ import annotations

from collections import defaultdict

from app.rules import wording
from app.rules.accounting.shared_detectors import detect_related_party_candidates
from app.rules.base_rule import ExceptionDraft, RuleOutcome

RULE_ID = "AUD-RPT-006"
AUDIT_AREA = "Related Party Transactions"
RELATED_SA = "SA 550"
ASSERTIONS = ("PRESENTATION_DISCLOSURE", "RIGHTS_OBLIGATIONS", "OCCURRENCE")
TOPIC = "Related Party Transaction Candidates"


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    any_party_name = any(row.values.get("party_name") for rows in dataset.values() for row in rows)
    if not any_party_name:
        outcome.insufficient_data_reason = (
            "No mapped row in this engagement's validated data has a Party Name value — related-party candidates "
            "cannot be identified without at least one party-bearing transaction file (e.g. Sales, Purchase, AR, AP)."
        )
        return outcome

    candidates = detect_related_party_candidates(dataset, engagement.entity_name)
    outcome.evaluated_count = len(candidates)
    if not candidates:
        return outcome

    by_party: dict[str, list] = defaultdict(list)
    for row in candidates:
        by_party[(row.values.get("party_name") or "").strip()].append(row)

    for party_name, rows in by_party.items():
        reason = getattr(rows[0], "_related_party_reason", "matched the related-party keyword/name-similarity heuristic")
        total_amount = sum((r.values.get("debit_amount") or 0) + (r.values.get("credit_amount") or 0) for r in rows)
        outcome.exceptions.append(ExceptionDraft(
            label=wording.AUDIT_ATTENTION_REQUIRED,
            area=AUDIT_AREA,
            trigger_condition=(
                f'Party "{party_name}" appears in {len(rows)} transaction(s) and {reason}.'
            ),
            explanation=(
                f'The counterparty "{party_name}" is a related-party CANDIDATE only, because it {reason}. This is '
                f"a coarse text heuristic on the party name — it does NOT establish related-party status under any "
                f"legal or accounting definition; only a professional review of the actual relationship can do "
                f"that. Under SA 550, once a related-party relationship is confirmed, the auditor considers "
                f"whether the transaction's terms are at arm's length and whether disclosure is complete."
            ),
            suggested_query=(
                f'Please confirm the actual relationship, if any, between the entity and "{party_name}", the '
                f"terms of the transaction(s), and whether related-party disclosures are complete."
            ),
            risk_level="HIGH",
            data_sources=[str(r.file_id) for r in rows],
            threshold_used={"transaction_count": len(rows), "candidate_only_not_confirmed": True},
            amount_paise=total_amount or None,
        ))

    return outcome
