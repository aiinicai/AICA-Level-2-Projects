"""DCF scenario analysis — Module 7 (Bear/Base/Bull).

The spec is explicit: never present DCF output as an objectively
correct price. This module's entire purpose is to make a single-point
DCF estimate impossible to present in isolation — run_scenarios always
returns three results together, and the report layer (Module 14) is
expected to render all three, not just "Base."
"""

from __future__ import annotations

from pydantic import BaseModel

from app.core.models import FinancialStatement
from app.valuation.dcf import DCFAssumptions, DCFResult, run_dcf


class ScenarioSet(BaseModel):
    """Bear/Base/Bull results bundled together — this is the unit the
    report generator consumes, never a single DCFResult in isolation."""

    bear: DCFResult | None
    base: DCFResult | None
    bull: DCFResult | None
    bear_status_note: str | None = None
    base_status_note: str | None = None
    bull_status_note: str | None = None


def run_scenarios(
    base_statement: FinancialStatement,
    *,
    bear_assumptions: DCFAssumptions,
    base_assumptions: DCFAssumptions,
    bull_assumptions: DCFAssumptions,
) -> ScenarioSet:
    """Run all three scenarios against the same base-year statement.

    Each scenario's assumptions are supplied explicitly by the caller
    (not auto-derived by, say, +/- 20% adjustments to Base) so every
    number in every scenario remains a stated, labeled assumption per
    Principle 4 (no silent assumptions) — auto-derivation would hide
    where the bear/bull deltas actually came from.
    """
    results = {}
    notes = {}
    for label, assumptions in (
        ("bear", bear_assumptions), ("base", base_assumptions), ("bull", bull_assumptions),
    ):
        outcome = run_dcf(base_statement, assumptions)
        if isinstance(outcome, DCFResult):
            results[label] = outcome
            notes[label] = None
        else:
            results[label] = None
            notes[label] = "; ".join(outcome.data_quality_notes) or "DCF could not be computed."

    return ScenarioSet(
        bear=results["bear"], base=results["base"], bull=results["bull"],
        bear_status_note=notes["bear"], base_status_note=notes["base"], bull_status_note=notes["bull"],
    )


def build_conservative_bear_case(base: DCFAssumptions, *, growth_haircut: float, margin_haircut: float) -> DCFAssumptions:
    """Convenience constructor: derive a Bear case from Base by explicit,
    labeled haircuts to growth and margin (both must be passed by the
    caller — this function does not choose default haircut magnitudes,
    since that would itself be a silent assumption)."""
    return base.model_copy(
        update={
            "revenue_growth_rate": _apply_haircut(base.revenue_growth_rate, growth_haircut),
            "ebitda_margin": _apply_haircut(base.ebitda_margin, margin_haircut),
        }
    )


def build_optimistic_bull_case(base: DCFAssumptions, *, growth_uplift: float, margin_uplift: float) -> DCFAssumptions:
    """Convenience constructor: derive a Bull case from Base by explicit,
    labeled uplifts to growth and margin."""
    return base.model_copy(
        update={
            "revenue_growth_rate": _apply_haircut(base.revenue_growth_rate, -growth_uplift),
            "ebitda_margin": _apply_haircut(base.ebitda_margin, -margin_uplift),
        }
    )


def _apply_haircut(value: float | list[float], haircut: float) -> float | list[float]:
    if isinstance(value, list):
        return [max(v - haircut, 0.0) for v in value]
    return max(value - haircut, 0.0)
