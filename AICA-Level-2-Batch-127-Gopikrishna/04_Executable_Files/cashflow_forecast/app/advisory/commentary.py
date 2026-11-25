"""Template commentary for each lot and for the whole horizon (plain text, no AI service)."""
from __future__ import annotations

from decimal import Decimal

from app.core.money import fmt_money
from app.engine.forecast import NOT_SUFFICIENT, ZERO, Forecast


def _m(v: Decimal) -> str:
    return fmt_money(v) if v >= 0 else f"({fmt_money(-v)})"


def lot_commentary(fc: Forecast) -> list[str]:
    threshold = Decimal(str(fc.settings.funding_alert_threshold))
    out = []
    for i, lt in enumerate(fc.fc_lots):
        L = {k: v[i] for k, v in fc.lines.items()}
        parts = [f"Lot {lt.label} closes at {_m(L['closing'])} {fc.settings.base_currency}."]
        top = max(fc.outflow_rows, key=lambda r: r.values[i], default=None)
        if top is not None and top.values[i] > 0:
            share = top.values[i] / L["outflows"] * 100 if L["outflows"] else 0
            parts.append(f"The largest outflow is {top.name} ({_m(top.values[i])}, {share:.0f}% of payments).")
        if L["hold_out"] or L["hold_in"]:
            parts.append(f"Holds take out {_m(L['hold_out'])} and re-present {_m(L['hold_in'])} here.")
        fpa = L["fp_after"]
        if fpa < 0:
            parts.append(f"Funding position after holds is {_m(fpa)}: a gap of {_m(-fpa)} still to cover.")
        elif L["fp_before"] < 0:
            parts.append(f"The gap of {_m(-L['fp_before'])} before holds is covered by the holds "
                         f"(after holds {_m(fpa)}).")
        elif fpa < threshold:
            parts.append(f"Funding position {_m(fpa)} is below the alert level by {_m(threshold - fpa)}.")
        else:
            parts.append(f"Funding position after holds is {_m(fpa)}.")
        out.append(" ".join(parts))
    return out


def summary_commentary(fc: Forecast) -> str:
    k = fc.kpis
    low = k["lowest_fp_after"]
    text = [f"As of {fc.as_of:%d %b %Y} ({fc.scenario}): the tightest point is {low['lot']} with a funding "
            f"position after holds of {_m(low['value'])}."]
    if k["gap_lots_before"] and not k["holds_count"]:
        text.append(f"{k['gap_lots_before']} lot(s) show a funding gap, first in {k['first_gap_before']}. "
                    "No cheques are on hold yet.")
    elif k["gap_lots_before"] or k["gap_lots_after"]:
        text.append(f"{k['gap_lots_before']} lot(s) show a gap before holds; {k['gap_lots_after']} after holds.")
        text.append("The holds are NOT sufficient." if k["overall"] == NOT_SUFFICIENT
                    else "The holds cover every gap.")
    else:
        text.append("No funding gap over the horizon.")
    if k["holds_count"]:
        text.append(f"{k['holds_count']} cheque(s) on hold for {_m(k['holds_total'])}"
                    + (f", of which {_m(k['holds_not_represented'])} is not re-presented within the horizon."
                       if k["holds_not_represented"] > ZERO else "."))
    prev = fc.tieout.get("previous")
    if prev:
        text.append(f"Bank balance vs. forecast from {prev['as_of']:%d %b}: variance {_m(prev['variance'])}.")
    return " ".join(text)
