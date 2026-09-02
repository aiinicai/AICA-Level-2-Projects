"""
AUD-ACC-004 — Rare Account Combination.

Audit area: Unusual Account Combinations. Relevant SA: SA 315, SA 330.
Assertions: Classification, Occurrence.

SA Reference (authoritative — ICAI Standard on Auditing): SA 315,
SA 330. This citation identifies the risk-identification/response
context the check sits within; it does NOT mean either standard
prescribes a rarity count or a minimum-voucher-population size — both
are FinSight's own.
FinSight Analytical Test (created by FinSight, not prescribed by any
SA): within this engagement's own multi-line journal vouchers (grouped
by `reference_number`), flag an account combination occurring at most
a FinSight-configurable number of times (currently 1 —
`RARITY_COUNT_THRESHOLD`), computed only once at least a
FinSight-configurable minimum number of multi-line vouchers exist to
compare against (currently 5 — `MIN_MULTI_LINE_VOUCHERS`).

What data is required: `JE` rows grouped by `reference_number`
(voucher), each with `account_name`.
What can actually be established: how often a given (sorted) set of
distinct accounts touched together in one voucher recurs across THIS
ENGAGEMENT'S OWN journal-entry population — nothing more. A combination
that occurs only once (or at/below a configurable rarity count) among
vouchers touching 2+ distinct accounts is flagged as a candidate for
review.
What cannot be established: any statistical or industry baseline — this
is a within-engagement relative-frequency heuristic only, not a
benchmark against similar entities.
Insufficient data: no validated JE data, no `reference_number` values
present (nothing to group vouchers by), or fewer than a configurable
minimum number of multi-line vouchers exist to make relative frequency
meaningful.
"""
from __future__ import annotations

from collections import defaultdict

from app.rules import wording
from app.rules.base_rule import ExceptionDraft, RuleOutcome

RULE_ID = "AUD-ACC-004"
AUDIT_AREA = "Unusual Account Combinations"
RELATED_SA = "SA 315, SA 330"
ASSERTIONS = ("CLASSIFICATION", "OCCURRENCE")
TOPIC = "Rare Account Combination"

# FinSight-configurable, not SA requirements.
RARITY_COUNT_THRESHOLD = 1  # flag combinations occurring at most this many times
MIN_MULTI_LINE_VOUCHERS = 5


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    je_rows = dataset.get("JE", [])
    if not je_rows:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped Journal Entry data is available for this engagement."
        )
        return outcome

    by_voucher: dict[str, list] = defaultdict(list)
    for row in je_rows:
        ref = (row.values.get("reference_number") or "").strip()
        if ref:
            by_voucher[ref].append(row)

    if not by_voucher:
        outcome.insufficient_data_reason = (
            "No validated Journal Entry row has a Reference Number value — vouchers cannot be grouped without one."
        )
        return outcome

    multi_line_vouchers = {ref: rows for ref, rows in by_voucher.items() if len(rows) >= 2}
    if len(multi_line_vouchers) < MIN_MULTI_LINE_VOUCHERS:
        outcome.insufficient_data_reason = (
            f"Only {len(multi_line_vouchers)} multi-line voucher(s) were found — at least {MIN_MULTI_LINE_VOUCHERS} "
            f"are needed before a within-engagement rarity comparison is meaningful."
        )
        return outcome

    combination_counts: dict[tuple, int] = defaultdict(int)
    combination_examples: dict[tuple, list] = defaultdict(list)
    for ref, rows in multi_line_vouchers.items():
        accounts = tuple(sorted({(r.values.get("account_name") or "").strip() for r in rows if r.values.get("account_name")}))
        if len(accounts) < 2:
            continue
        combination_counts[accounts] += 1
        combination_examples[accounts].append((ref, rows))

    outcome.evaluated_count = len(multi_line_vouchers)

    for accounts, count in combination_counts.items():
        if count > RARITY_COUNT_THRESHOLD:
            continue
        ref, rows = combination_examples[accounts][0]
        total_amount = sum((r.values.get("debit_amount") or 0) + (r.values.get("credit_amount") or 0) for r in rows)
        outcome.exceptions.append(ExceptionDraft(
            label=wording.POTENTIAL_AUDIT_RISK,
            area=AUDIT_AREA,
            trigger_condition=(
                f"Account combination {list(accounts)} occurs in only {count} voucher(s) (reference "
                f"\"{ref}\") among this engagement's {len(multi_line_vouchers)} multi-line vouchers."
            ),
            explanation=(
                f"The combination of accounts {list(accounts)}, touched together in voucher \"{ref}\", occurs only "
                f"{count} time(s) across this engagement's own journal-entry population — a rarity signal relative "
                f"to this engagement's own data only, not any external or industry baseline. This does not itself "
                f"indicate an error; unusual account combinations warrant inspection of the underlying "
                f"documentation to assess whether the classification is appropriate."
            ),
            suggested_query=(
                f"Please explain the business rationale for combining accounts {list(accounts)} in voucher "
                f"\"{ref}\"."
            ),
            risk_level="MEDIUM",
            data_sources=[str(r.file_id) for r in rows],
            threshold_used={
                "occurrence_count": count,
                "rarity_count_threshold": RARITY_COUNT_THRESHOLD,
                "population_multi_line_vouchers": len(multi_line_vouchers),
                "baseline_is_within_engagement_only": True,
            },
            amount_paise=total_amount or None,
        ))

    return outcome
