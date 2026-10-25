"""
scoring.py
==========
Weighted internal risk scorecard (Grade A-E) and NBFC policy-guardrail compliance checks.

Scoring mechanics
-----------------
1. Each metric is mapped linearly to 0-100 between a "worst" and a "best" value (config.SCORING_SPEC).
2. Metrics are weighted within their pillar; pillars are weighted (config.PILLAR_WEIGHTS).
3. A small trend adjustment (+/- 3 pts) rewards or penalises the 3-year direction of revenue and margins.
4. Hard overrides cap the grade: TNW <= 0 -> E ; pro-forma DSCR < 1.0x -> no better than D.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import GRADE_BANDS, GRADE_ORDER, PILLAR_WEIGHTS, SCORING_SPEC, PolicyLimits
from .ingestion import ApplicantData
from .ratios import RatioBundle


def score_metric(value: float, worst: float, best: float) -> float:
    """Linear 0-100 score; NaN stays NaN so the metric can be excluded from its pillar."""
    if value is None or np.isnan(value):
        return np.nan
    if np.isinf(value):
        return 0.0 if (value > 0) == (worst > best) else 100.0
    return float(np.clip((value - worst) / (best - worst), 0, 1) * 100)


@dataclass
class Scorecard:
    metrics: pd.DataFrame            # pillar, metric, value, worst, best, weight, score
    pillar_scores: dict
    base_score: float
    trend_adjustment: float
    composite: float
    grade: str
    grade_label: str
    notes: list = field(default_factory=list)


def _trend_adjustment(bundle: RatioBundle) -> tuple[float, list]:
    rev, ebitda = bundle.fin["revenue"], bundle.fin["ebitda"]
    margin = bundle.ratios["ebitda_margin"]
    adj, notes = 0.0, []
    if rev.is_monotonic_increasing and margin.iloc[-1] >= margin.iloc[0]:
        adj += 3.0
        notes.append("+3 pts: revenue rising every year with stable/expanding EBITDA margin.")
    elif (rev.iloc[-1] < rev.iloc[0]) and (margin.iloc[-1] < margin.iloc[0]):
        adj -= 3.0
        notes.append("-3 pts: revenue and EBITDA margin both lower than three years ago.")
    elif ebitda.iloc[-1] < 0.85 * ebitda.iloc[0]:
        adj -= 2.0
        notes.append("-2 pts: absolute EBITDA down more than 15% over the period.")
    return adj, notes


def _grade_for(score: float) -> tuple[str, str]:
    for floor, grade, label in GRADE_BANDS:
        if score >= floor:
            return grade, label
    return GRADE_BANDS[-1][1], GRADE_BANDS[-1][2]


def build_scorecard(data: ApplicantData, bundle: RatioBundle, pf: dict) -> Scorecard:
    last = bundle.fin.iloc[-1]
    values = {k: bundle.latest(k) for k in bundle.ratios.columns}
    values.update(
        pf_debt_ebitda=pf["debt_ebitda"], pf_de=pf["de"], pf_icr=pf["icr"], pf_dscr=pf["dscr"],
        revenue=float(last["revenue"]), vintage=data.vintage_years, tnw=float(last["tnw"]),
        bureau_score=float(data.profile.get("bureau_score", np.nan)),
    )

    rows = []
    for pillar, spec in SCORING_SPEC.items():
        for key, label, w, worst, best in spec:
            v = values.get(key, np.nan)
            rows.append(dict(pillar=pillar, key=key, metric=label, value=v, worst=worst, best=best,
                             weight=w, score=score_metric(v, worst, best)))
    m = pd.DataFrame(rows)

    pillar_scores = {}
    for pillar, grp in m.groupby("pillar", sort=False):
        g = grp.dropna(subset=["score"])
        pillar_scores[pillar] = float((g["score"] * g["weight"]).sum() / g["weight"].sum()) if len(g) else 0.0

    base = sum(pillar_scores[p] * w for p, w in PILLAR_WEIGHTS.items())
    adj, notes = _trend_adjustment(bundle)
    composite = float(np.clip(base + adj, 0, 100))
    grade, label = _grade_for(composite)

    # Hard overrides
    if last["tnw"] <= 0:
        grade, label = "E", "Very high risk"
        notes.append("Override: tangible net worth is negative -> Grade E.")
    elif pf["dscr"] < 1.0 and GRADE_ORDER.index(grade) < GRADE_ORDER.index("D"):
        grade, label = "D", "High risk"
        notes.append("Override: pro-forma DSCR below 1.0x -> grade capped at D.")

    return Scorecard(m, pillar_scores, float(base), adj, composite, grade, label, notes)


# --------------------------------------------------------------------------- #
# Policy compliance
# --------------------------------------------------------------------------- #
def run_policy_checks(data: ApplicantData, bundle: RatioBundle, pf: dict, limits: PolicyLimits) -> pd.DataFrame:
    """
    One row per guardrail. 'Hard' breaches block a straight approval; 'Soft' breaches require mitigants.
    'Critical' marks breaches where the debt cannot be serviced or net worth is eroded.
    """
    amount = float(data.proposed["amount"])
    rows = []

    def add(check, basis, rule, actual, passed, severity, unit="x", critical=False):
        rows.append(dict(Check=check, Basis=basis, Rule=rule, Actual=actual, Passed=bool(passed),
                         Severity=severity, Unit=unit, Critical=critical and not passed))

    add("DSCR", "Pro-forma", f">= {limits.min_dscr:.2f}x", pf["dscr"], pf["dscr"] >= limits.min_dscr, "Hard",
        critical=pf["dscr"] < limits.critical_dscr)
    add("Debt / Tangible net worth", "Pro-forma", f"<= {limits.max_de:.2f}x", pf["de"], pf["de"] <= limits.max_de,
        "Hard", critical=pf["tnw"] <= 0)
    add("Interest coverage (ICR)", "Pro-forma", f">= {limits.min_icr:.2f}x", pf["icr"], pf["icr"] >= limits.min_icr,
        "Hard")
    add("Total debt / EBITDA", "Pro-forma", f"<= {limits.max_debt_ebitda:.2f}x", pf["debt_ebitda"],
        pf["debt_ebitda"] <= limits.max_debt_ebitda, "Hard")
    add("Facility size within ticket band", "Request", f"{limits.min_facility_cr:.0f}-{limits.max_facility_cr:.0f} Cr",
        amount, limits.min_facility_cr <= amount <= limits.max_facility_cr, "Hard", unit="cr")
    sc = pf["security_cover"]
    add("Collateral security cover", "Request", f">= {limits.min_security_cover:.2f}x", sc,
        (not np.isnan(sc)) and sc >= limits.min_security_cover, "Soft")
    hist_dscr = bundle.latest("dscr")
    add("DSCR - latest audited year", "Historical", f">= {limits.min_dscr:.2f}x", hist_dscr,
        (not np.isnan(hist_dscr)) and hist_dscr >= limits.min_dscr, "Soft")
    hist_icr = bundle.latest("icr")
    add("ICR - latest audited year", "Historical", f">= {limits.min_icr:.2f}x", hist_icr,
        (not np.isnan(hist_icr)) and hist_icr >= limits.min_icr, "Soft")
    bureau = data.profile.get("bureau_score")
    if bureau is not None and not pd.isna(bureau):
        add("Credit bureau score", "Bureau", f">= {limits.min_bureau_score:.0f}", float(bureau),
            bureau >= limits.min_bureau_score, "Soft", unit="score")
    return pd.DataFrame(rows)
