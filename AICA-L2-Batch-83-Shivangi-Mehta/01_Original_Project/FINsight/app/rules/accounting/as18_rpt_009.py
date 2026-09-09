"""
AS18-RPT-009 / INDAS24-RPT-009 — Related Party Disclosure: Candidate
Identification.

Framework: AS 18 (Related Party Disclosures) / Ind AS 24 (Related
Party Disclosures). Framework-aware for Stage 8 Round 2, same pattern
as the other rules — one shared `evaluate()`, the correct `rule_id`
and (via the runner + seed data) the correct Standard reference for
whichever framework the engagement is on.

What data is required: any mapped row with a `party_name` value
(SALES/PURCHASE/AR/AP/GL/JE/OTHER, wherever `party_name` was confirmed-
mapped), plus the engagement's own `entity_name`.
What can actually be established: whether a party name matches a coarse
keyword list (director, promoter, relative, holding, subsidiary, etc.)
or closely resembles the engagement's own entity name — using the same
`shared_detectors.detect_related_party_candidates()` heuristic
documented there. This flags CANDIDATES for review; it never asserts
that a party is, in fact, a related party under AS 18/Ind AS 24's legal
definition, and it never asserts that disclosure is missing or
inadequate — no related-party master list, disclosure note, or flag
field exists anywhere in the schema to check disclosure completeness
against.
What cannot be established: the legal related-party status of any
counterparty, or whether existing disclosures (if any, outside the
uploaded transactional data) are complete.
Insufficient data: no row anywhere in the dataset has a `party_name`
value at all.
"""
from __future__ import annotations

from collections import defaultdict

from app.rules import wording
from app.rules.accounting.shared_detectors import detect_related_party_candidates
from app.rules.base_rule import ExceptionDraft, RuleOutcome

FRAMEWORK_RULE_IDS = {"AS": "AS18-RPT-009", "IND_AS": "INDAS24-RPT-009"}
TOPIC = "Related Party Disclosure — Candidate Identification"


def evaluate(engagement, dataset: dict[str, list], framework: str) -> RuleOutcome:
    rule_id = FRAMEWORK_RULE_IDS.get(framework, FRAMEWORK_RULE_IDS["AS"])
    outcome = RuleOutcome(rule_id=rule_id)

    any_party_name = any(
        row.values.get("party_name") for rows in dataset.values() for row in rows
    )
    if not any_party_name:
        outcome.insufficient_data_reason = (
            "No mapped row in this engagement's validated data has a Party Name value — related-party candidates "
            "cannot be identified without at least one party-bearing transaction file (e.g. Sales, Purchase, AR, AP)."
        )
        return outcome

    candidates = detect_related_party_candidates(dataset, engagement.entity_name)
    outcome.evaluated_count = len(candidates)
    if not candidates:
        return outcome  # party names exist, none matched the heuristic — nothing to flag

    by_party: dict[str, list] = defaultdict(list)
    for row in candidates:
        party_name = (row.values.get("party_name") or "").strip()
        by_party[party_name].append(row)

    for party_name, rows in by_party.items():
        reason = getattr(rows[0], "_related_party_reason", "matched the related-party keyword/name-similarity heuristic")
        total_amount = sum((r.values.get("debit_amount") or 0) + (r.values.get("credit_amount") or 0) for r in rows)
        outcome.exceptions.append(ExceptionDraft(
            label=wording.POTENTIAL_INCONSISTENCY,
            area=TOPIC,
            trigger_condition=(
                f'Party "{party_name}" appears in {len(rows)} transaction(s) and {reason}.'
            ),
            explanation=(
                f'The counterparty "{party_name}" was flagged as a related-party CANDIDATE because it {reason}. '
                f"This is a coarse text heuristic on the party name only — it does not establish related-party "
                f"status under this framework's legal definition, and it does not assess whether any required "
                f"disclosure is complete. A professional review is needed to confirm the actual relationship, if "
                f"any, and whether appropriate disclosure exists."
            ),
            suggested_query=(
                f'Please confirm the relationship, if any, between the entity and "{party_name}", and whether '
                f"related-party disclosures for this counterparty are complete."
            ),
            risk_level="MEDIUM",
            data_sources=[str(r.file_id) for r in rows],
            threshold_used={"transaction_count": len(rows), "total_amount_paise": total_amount},
            amount_paise=total_amount or None,
        ))

    return outcome
