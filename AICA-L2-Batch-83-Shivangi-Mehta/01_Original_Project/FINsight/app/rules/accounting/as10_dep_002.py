"""
AS10-DEP-002 / INDAS16-DEP-002 — Depreciation Rate Consistency, Year on
Year.

Framework: AS 10 (Property, Plant and Equipment) / Ind AS 16 (Property,
Plant and Equipment).

REPLACES AS6-DEP-002 (Stage 8 Round 2, correction #2). AS 6
("Depreciation Accounting") was withdrawn by ICAI — its provisions were
incorporated into revised AS 10 — via the Companies (Accounting
Standards) Amendment Rules, 2016 (G.S.R. 364(E), dated 30 March 2016),
effective for accounting periods commencing on or after 1 April 2017;
ICAI's own compendium of Accounting Standards no longer lists AS 6.
Source: MCA notification G.S.R. 364(E)/2016; ICAI "Accounting Standards
as on 1st Feb 2022." This rule's logic and analytical test are
unchanged from the withdrawn AS6-DEP-002 — only the standard reference
is corrected. `AS6-DEP-002` itself is retained in the catalogue,
`is_active=False`, purely as a withdrawn/superseded marker (see the
seed script) — it must never execute.

What data is required: `fixed_assets` rows for the same `asset_class`
in both the current engagement and a prior-year engagement for the SAME
entity (same `entity_name`, financial year immediately preceding this
one).
What can actually be established: whether the average book depreciation
rate recorded for an asset class this year differs from last year. This
is a rate-consistency check, not a claim about which method (SLM/WDV/
other) is being applied — the same `book_depreciation_rate` field is
compared without interpreting it as any specific method's rate.
What cannot be established: whether any rate change is backed by a
documented policy note — no such field or linked document exists
anywhere in the approved schema, so this is never asserted either way.
Insufficient data: no prior-year engagement exists for this entity, or
the prior engagement has no validated Fixed Asset data, or an asset
class present this year simply wasn't present last year (nothing to
compare — not itself a finding).
"""
from __future__ import annotations

from collections import defaultdict

from app.rules import wording
from app.rules.accounting.shared_detectors import find_prior_year_dataset
from app.rules.base_rule import ExceptionDraft, RuleOutcome

FRAMEWORK_RULE_IDS = {"AS": "AS10-DEP-002", "IND_AS": "INDAS16-DEP-002"}
TOPIC = "Depreciation Rate Consistency — Year on Year"


def _average_rate_by_class(rows: list) -> dict[str, float]:
    totals: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        asset_class = row.values.get("asset_class")
        rate = row.values.get("book_depreciation_rate")
        if asset_class and rate is not None:
            totals[asset_class.strip()].append(rate)
    return {k: sum(v) / len(v) for k, v in totals.items()}


def evaluate(engagement, dataset: dict[str, list], framework: str) -> RuleOutcome:
    rule_id = FRAMEWORK_RULE_IDS.get(framework, FRAMEWORK_RULE_IDS["AS"])
    outcome = RuleOutcome(rule_id=rule_id)

    current_assets = dataset.get("FIXED_ASSETS", [])
    if not current_assets:
        outcome.insufficient_data_reason = "No validated Fixed Asset Register data is available for this engagement."
        return outcome

    prior_dataset = find_prior_year_dataset(engagement)
    if prior_dataset is None:
        outcome.insufficient_data_reason = (
            f"No prior-year engagement was found for \"{engagement.entity_name}\" — depreciation-rate "
            f"consistency cannot be assessed without a comparable prior period."
        )
        return outcome
    prior_assets = prior_dataset.get("FIXED_ASSETS", [])
    if not prior_assets:
        outcome.insufficient_data_reason = (
            "A prior-year engagement for this entity exists, but it has no validated Fixed Asset Register data "
            "to compare against."
        )
        return outcome

    current_rates = _average_rate_by_class(current_assets)
    prior_rates = _average_rate_by_class(prior_assets)

    for asset_class, current_rate in current_rates.items():
        prior_rate = prior_rates.get(asset_class)
        if prior_rate is None:
            outcome.partial_insufficient_data_notes.append(
                f'Asset class "{asset_class}" has no comparable prior-year rate to compare against.'
            )
            continue

        outcome.evaluated_count += 1
        if abs(current_rate - prior_rate) > 1e-9:
            outcome.exceptions.append(ExceptionDraft(
                label=wording.POTENTIAL_INCONSISTENCY,
                area=TOPIC,
                trigger_condition=(
                    f'Average book depreciation rate for asset class "{asset_class}" changed from '
                    f"{prior_rate:.2f}% last year to {current_rate:.2f}% this year."
                ),
                explanation=(
                    f'The average recorded book depreciation rate for asset class "{asset_class}" differs between '
                    f"this engagement and the prior-year engagement for the same entity. Whether this change is "
                    f"supported by a documented change in accounting estimate or policy could not be established "
                    f"from the uploaded data — no policy-note field or linked document was available to check."
                ),
                suggested_query=(
                    f'Please provide the basis for the change in depreciation rate for asset class "{asset_class}" '
                    f"(from {prior_rate:.2f}% to {current_rate:.2f}%)."
                ),
                risk_level="MEDIUM",
                data_sources=[str(row.file_id) for row in current_assets if row.values.get("asset_class") == asset_class],
                threshold_used={"prior_rate_pct": round(prior_rate, 2), "current_rate_pct": round(current_rate, 2)},
            ))

    return outcome
