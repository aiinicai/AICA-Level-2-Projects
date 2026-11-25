"""Rule-based forecast engine (pure: no database access; see ``loader.py`` for that).

Rules
- Lots come from ``lots.build_lots``. Only the current and forecast lots are calculated; locked
  actual lots are shown from saved snapshots.
- The current lot opens with the ERP bank total (other currencies at the manual rate). Every later
  lot opens with the previous lot's closing.
- Each item goes in the lot of its (effective) date. Unpaid items dated before the as-of date go in the
  current lot. Items dated after the horizon are left out (status ``beyond_horizon``).
- Closing = opening + inflows - outflows. Funding position = closing + facility. Gap = MIN(0, FP).
- Overrides, applied in this order: recategorise, reduce, defer (to a lot) or redate, exclude,
  bill discounted (inflows), risk-adjusted (scenario may exclude), hold.
- Holds never change rows B-F. Block G takes the held amount out of the cheque's lot and puts it back
  in the lot of the next honouring date (open-ended or after the horizon: not re-presented).
  Closing after holds = closing + cumulative hold effect; Net funding position after holds =
  closing after holds + facility.
All money is Decimal at 3 dp; every figure is a plain sum, so the Excel export can rebuild it with
formulas and get exactly the same numbers.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from app.core.config import BusinessDefaults
from app.core.money import round_money
from app.engine.lots import Lot, build_lots, forecast_lots, lot_index

ZERO = Decimal("0.000")
INFLOW, OUTFLOW = "inflow", "outflow"

# how a line is carried into month / horizon total columns
LINE_RULES: dict[str, str] = {
    "opening": "first", "inflows": "sum", "outflows": "sum", "net": "sum", "closing": "last",
    "facility": "last", "fp_before": "last", "gap_before": "min",
    "hold_out": "sum", "hold_in": "sum", "hold_net": "sum", "hold_cum": "last",
    "closing_after": "last", "fp_after": "last", "shortfall_after": "min",
    "risk_excluded": "sum", "deferred_in": "sum", "holds_open": "sum",
}
LINE_LABELS = {
    "opening": "Opening bank balance", "inflows": "Total inflows", "outflows": "Total outflows",
    "net": "Net cash flow", "closing": "Closing balance (as per ERP items)", "facility": "Bank facility available",
    "fp_before": "Funding position before holds", "gap_before": "Funding gap before holds",
    "hold_out": "Add: PDCs put on hold", "hold_in": "Less: held PDCs re-presented", "hold_net": "Net hold effect",
    "hold_cum": "Cumulative hold effect", "closing_after": "Closing balance after holds",
    "fp_after": "NET FUNDING POSITION AFTER HOLDS", "shortfall_after": "Shortfall after holds",
    "risk_excluded": "Risk-adjusted collections excluded", "deferred_in": "Amounts deferred into this lot",
    "holds_open": "Held, not re-presented within horizon",
}
NO_GAP, COVERED, NOT_SUFFICIENT = "No gap", "Covered by holds", "NOT sufficient"
_STATUS_RANK = {NO_GAP: 0, COVERED: 1, NOT_SUFFICIENT: 2}


# ------------------------------------------------------------------ inputs
@dataclass
class ItemIn:
    line_item_id: int
    source: str
    key: str
    category_id: int
    direction: str
    planned_date: date
    amount: Decimal
    counterparty: str = ""
    reference: str = ""
    project: str = ""
    bank: str = ""
    currency: str = "OMR"
    is_paid: bool = False
    risk_flag: bool = False
    bill_discounted: bool = False
    note: str = ""


@dataclass
class OverrideIn:
    id: int
    source: str
    key: str
    action: str
    new_date: date | None = None
    target_lot_start: date | None = None
    new_amount: Decimal | None = None
    new_category_id: int | None = None
    reason: str = ""
    approval: str = "not_required"
    created_by: str = ""
    created_at: datetime | None = None
    times_extended: int = 0


@dataclass
class CategoryIn:
    id: int
    name: str
    direction: str
    group: str
    order: int
    treatment: str = "fixed"
    active: bool = True


@dataclass
class BalanceIn:
    bank: str
    account: str
    currency: str
    as_of: date
    balance: Decimal
    rate: Decimal = Decimal(1)

    @property
    def omr(self) -> Decimal:
        return round_money(self.balance * self.rate)


@dataclass
class FacilityIn:
    bank: str
    facility_type: str
    as_of: date
    available: Decimal
    limit: Decimal | None = None
    utilised: Decimal | None = None


@dataclass
class Inputs:
    as_of: date
    settings: BusinessDefaults
    items: list[ItemIn]
    categories: list[CategoryIn]
    overrides: list[OverrideIn] = field(default_factory=list)
    balances: list[BalanceIn] = field(default_factory=list)
    facilities: list[FacilityIn] = field(default_factory=list)
    scenario: str = "Base"
    scenario_id: int | None = None
    exclude_risk: bool = False
    date_hints: dict[tuple[str, str], tuple[date, str]] = field(default_factory=dict)  # delay model
    locked: dict[date, dict] = field(default_factory=dict)        # actual lot start -> snapshot column
    previous: dict | None = None                                  # previous snapshot: as_of, opening, daily_net
    warnings: list[str] = field(default_factory=list)


# ------------------------------------------------------------------ outputs
@dataclass
class HoldInfo:
    override_id: int
    amount: Decimal
    honour_date: date | None
    out_lot: int
    honour_lot: int | None          # None: open-ended or after the horizon
    days_held: int | None
    times_extended: int
    reason: str
    held_by: str
    held_at: datetime | None
    warnings: list[str] = field(default_factory=list)

    @property
    def open_ended(self) -> bool:
        return self.honour_date is None


@dataclass
class ItemOut:
    item: ItemIn
    category_id: int
    category: str
    eff_date: date
    eff_amount: Decimal
    lot: int | None = None
    status: str = "active"   # active | paid | other_currency | excluded | bill_discounted | risk_excluded | beyond_horizon
    flags: list[str] = field(default_factory=list)
    hold: HoldInfo | None = None
    memo_lot: int | None = None      # lot of a risk-excluded item (memo line only, not in totals)

    @property
    def source(self) -> str:
        return self.item.source

    @property
    def key(self) -> str:
        return self.item.key

    @property
    def direction(self) -> str:
        return self.item.direction


@dataclass
class CategoryRow:
    category_id: int
    name: str
    group: str
    direction: str
    order: int
    values: list[Decimal]


@dataclass
class Column:
    kind: str                 # lot | month | horizon
    label: str
    lots: list[int]           # forecast-lot indexes summarised by this column
    month: date | None = None
    partial: bool = False
    band: str = ""            # period heading: 'November 2026' or '05 Nov-04 Dec 2026'


@dataclass
class Forecast:
    as_of: date
    scenario: str
    scenario_id: int | None
    exclude_risk: bool
    settings: BusinessDefaults
    lots: list[Lot]                      # everything shown (locked actuals first)
    fc_lots: list[Lot]                   # current + forecast lots (calculated)
    inflow_rows: list[CategoryRow]
    outflow_rows: list[CategoryRow]
    lines: dict[str, list[Decimal]]
    lot_status: list[str]
    items: list[ItemOut]
    holds: list[ItemOut]
    columns: list[Column]
    erp_opening: Decimal
    facility_total: Decimal
    balances: list[BalanceIn]
    facilities: list[FacilityIn]
    daily_net: dict[date, Decimal]
    kpis: dict
    tieout: dict
    locked: dict[date, dict]
    warnings: list[str]

    # -- values for any column (lot, month total, horizon total)
    def line(self, name: str, col: Column) -> Decimal:
        vals = self.lines[name]
        return _summarise([vals[i] for i in col.lots], LINE_RULES[name])

    def row(self, row: CategoryRow, col: Column) -> Decimal:
        return sum((row.values[i] for i in col.lots), ZERO)

    def status(self, col: Column) -> str:
        return max((self.lot_status[i] for i in col.lots), key=_STATUS_RANK.get)

    @property
    def rows(self) -> list[CategoryRow]:
        return self.inflow_rows + self.outflow_rows

    def to_dict(self) -> dict:
        """JSON-safe copy for snapshots (amounts as 3-dp strings)."""
        s = str
        return {
            "as_of": self.as_of.isoformat(), "scenario": self.scenario, "exclude_risk": self.exclude_risk,
            "erp_opening": s(self.erp_opening), "facility": s(self.facility_total),
            "lots": [{"start": lt.start.isoformat(), "end": lt.end.isoformat(), "label": lt.label,
                      "status": lt.status, "funding_status": self.lot_status[i],
                      "lines": {k: s(v[i]) for k, v in self.lines.items()},
                      "categories": {r.name: s(r.values[i]) for r in self.rows}}
                     for i, lt in enumerate(self.fc_lots)],
            "daily_net": {d.isoformat(): s(v) for d, v in sorted(self.daily_net.items())},
            "kpis": _jsonable(self.kpis),
            "holds": [{"source": h.source, "key": h.key, "amount": s(h.hold.amount),
                       "honour_date": h.hold.honour_date.isoformat() if h.hold.honour_date else None}
                      for h in self.holds],
        }


def _jsonable(v):
    if isinstance(v, dict):
        return {k: _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, (Decimal, date)):
        return str(v)
    return v


def _summarise(vals: list[Decimal], rule: str) -> Decimal:
    if not vals:
        return ZERO
    if rule == "sum":
        return sum(vals, ZERO)
    if rule == "first":
        return vals[0]
    if rule == "last":
        return vals[-1]
    return min(vals)


def build_columns(fc: list[Lot], show_month_totals: bool) -> list[Column]:
    cols: list[Column] = []
    by_month: dict[date, list[int]] = defaultdict(list)
    for i, lt in enumerate(fc):
        by_month[lt.month].append(i)
    for m, idx in by_month.items():
        first = fc[idx[0]]
        band = first.band
        cols += [Column("lot", fc[i].label, [i], m, band=band) for i in idx]
        if show_month_totals:
            partial = first.start != (first.period_start or m)
            name = f"{m:%b %Y}" if (first.period_start or m).day == 1 else band
            cols.append(Column("month", f"{name} total" + (" *" if partial else ""), idx, m, partial, band))
    cols.append(Column("horizon", "Horizon total", list(range(len(fc)))))
    return cols


# ------------------------------------------------------------------ engine
def compute(inp: Inputs) -> Forecast:
    s = inp.settings
    warnings = list(inp.warnings)
    lots = build_lots(inp.as_of, s)
    fc = forecast_lots(lots)
    n = len(fc)
    cats = {c.id: c for c in inp.categories}

    ovr: dict[tuple[str, str], dict[str, OverrideIn]] = defaultdict(dict)
    pending: dict[tuple[str, str], list[str]] = defaultdict(list)
    for o in inp.overrides:
        if o.approval in ("pending", "rejected"):
            pending[(o.source, o.key)].append(f"{o.action} {o.approval}")
            continue
        ovr[(o.source, o.key)][o.action] = o

    cat_vals: dict[int, list[Decimal]] = defaultdict(lambda: [ZERO] * n)
    lines = {k: [ZERO] * n for k in LINE_RULES}
    daily: dict[date, Decimal] = defaultdict(lambda: ZERO)
    items_out: list[ItemOut] = []
    holds: list[ItemOut] = []

    for it in inp.items:
        k = (it.source, it.key)
        o = ovr.get(k, {})
        cid = it.category_id
        out = ItemOut(it, cid, cats[cid].name if cid in cats else "?", it.planned_date, it.amount)
        items_out.append(out)
        out.flags += [f"pending approval: {p}" for p in pending.get(k, [])]
        if it.is_paid:
            out.status = "paid"
            continue
        if it.currency != s.base_currency:
            out.status = "other_currency"
            warnings.append(f"{it.source} {it.reference or it.key}: {it.currency} item left out "
                            f"(only {s.base_currency} flows are forecast).")
            continue

        if "recategorise" in o:
            new = cats.get(o["recategorise"].new_category_id)
            if new is not None and new.direction == it.direction:
                cid, out.category_id, out.category = new.id, new.id, new.name
                out.flags.append("recategorised")
            else:
                warnings.append(f"{it.key}: recategorise ignored (category missing or other direction).")

        amt = it.amount
        if "reduce" in o:
            amt = min(amt, o["reduce"].new_amount)
            out.flags.append("reduced")
        out.eff_amount = amt

        d, li = it.planned_date, None
        if "defer" in o:
            li = lot_index(fc, o["defer"].target_lot_start)
            out.flags.append("deferred")
            if li is not None:
                d = d if fc[li].contains(d) else fc[li].start
            else:
                d = o["defer"].target_lot_start
        elif "redate" in o:
            d = o["redate"].new_date
            out.flags.append("redated")
        elif k in inp.date_hints and it.source == "collections":
            d = inp.date_hints[k][0]
            out.flags.append("model date")
        out.eff_date = d
        if li is None and "defer" not in o:
            if d < inp.as_of:
                li = 0
                out.flags.append("overdue")
            else:
                li = lot_index(fc, d)

        if "exclude" in o:
            out.status = "excluded"
            continue
        if it.direction == INFLOW and (it.bill_discounted or "bill_discounted" in o):
            out.status = "bill_discounted"
            continue
        if it.risk_flag or "risk_adjusted" in o:
            out.flags.append("risk")
            if inp.exclude_risk:
                out.status = "risk_excluded"
                if li is not None:
                    lines["risk_excluded"][li] += amt
                    out.memo_lot = li
                continue
        if li is None:
            out.status = "beyond_horizon"
            continue

        out.lot = li
        cat_vals[cid][li] += amt
        cash_day = max(d, inp.as_of)
        daily[cash_day] += amt if it.direction == INFLOW else -amt
        if "defer" in o:
            lines["deferred_in"][li] += amt

        h = o.get("hold")
        if h is None:
            continue
        if it.direction != OUTFLOW:
            warnings.append(f"{it.key}: hold ignored (only payments can be held).")
            continue
        if amt <= 0:
            continue
        hw: list[str] = []
        held = amt if h.new_amount is None else min(h.new_amount, amt)
        if h.new_amount is not None and h.new_amount > amt:
            hw.append(f"Hold amount {h.new_amount:,.3f} is more than the cheque ({amt:,.3f}); capped.")
        hd, hl = h.new_date, None
        if hd is None:
            hw.append("Open-ended: no honouring date set.")
        else:
            if hd <= d:
                hw.append("Honouring date is not after the cheque date: the hold has no effect.")
                hl, back_day = li, cash_day
            elif hd < inp.as_of:
                hw.append("Honouring date has passed: treated as due in the current lot.")
                hl, back_day = 0, inp.as_of
            else:
                hl, back_day = lot_index(fc, hd), hd
                if hl is None:
                    hw.append(f"Honouring date {hd:%d-%b-%Y} is after the horizon: not re-presented in the grid.")
            if (hd - it.planned_date).days > s.cheque_validity_days:
                hw.append(f"More than {s.cheque_validity_days} days after the cheque date: the cheque may be "
                          "stale. Confirm with the bank.")
        lines["hold_out"][li] += held
        daily[cash_day] += held
        if hl is not None:
            lines["hold_in"][hl] += held
            daily[back_day] -= held
        else:
            lines["holds_open"][li] += held
        out.hold = HoldInfo(h.id, held, hd, li, hl, (hd - it.planned_date).days if hd else None,
                            h.times_extended, h.reason, h.created_by, h.created_at, hw)
        holds.append(out)

    # ---- category rows (all active categories, plus inactive ones that carry amounts)
    def rows_for(direction: str) -> list[CategoryRow]:
        rows = [CategoryRow(c.id, c.name, c.group, c.direction, c.order, list(cat_vals[c.id]) if c.id in cat_vals
                            else [ZERO] * n)
                for c in inp.categories if c.direction == direction and (c.active or c.id in cat_vals)]
        first = defaultdict(lambda: 10 ** 9)
        for r in rows:
            first[r.group] = min(first[r.group], r.order)
        return sorted(rows, key=lambda r: (first[r.group], r.group, r.order, r.name))

    inflow_rows, outflow_rows = rows_for(INFLOW), rows_for(OUTFLOW)

    # ---- lot arithmetic
    erp_opening = sum((b.omr for b in inp.balances), ZERO)
    facility = sum((f.available for f in inp.facilities), ZERO)
    opening, cum, lot_status = erp_opening, ZERO, []
    for i in range(n):
        tin = sum((r.values[i] for r in inflow_rows), ZERO)
        tout = sum((r.values[i] for r in outflow_rows), ZERO)
        closing = opening + tin - tout
        fpb = closing + facility
        hnet = lines["hold_out"][i] - lines["hold_in"][i]
        cum += hnet
        ca = closing + cum
        fpa = ca + facility
        for key, v in (("opening", opening), ("inflows", tin), ("outflows", tout), ("net", tin - tout),
                       ("closing", closing), ("facility", facility), ("fp_before", fpb),
                       ("gap_before", min(ZERO, fpb)), ("hold_net", hnet), ("hold_cum", cum),
                       ("closing_after", ca), ("fp_after", fpa), ("shortfall_after", min(ZERO, fpa))):
            lines[key][i] = v
        lot_status.append(NOT_SUFFICIENT if fpa < 0 else COVERED if fpb < 0 else NO_GAP)
        opening = closing

    for h in holds:
        hl = h.hold.honour_lot
        if hl is not None and hl != h.hold.out_lot and lines["fp_after"][hl] < 0:
            h.hold.warnings.append(f"Honouring lot {fc[hl].label} is in a gap after holds: the problem has "
                                   "only moved.")

    columns = build_columns(fc, s.show_month_totals)
    kpis = _kpis(fc, lines, lot_status, holds, Decimal(str(s.funding_alert_threshold)))
    tieout = _tieout(inp, erp_opening)
    return Forecast(inp.as_of, inp.scenario, inp.scenario_id, inp.exclude_risk, s, lots, fc, inflow_rows,
                    outflow_rows, lines, lot_status, items_out, holds, columns, erp_opening, facility,
                    inp.balances, inp.facilities, dict(daily), kpis, tieout, inp.locked, warnings)


def _kpis(fc, lines, lot_status, holds, threshold) -> dict:
    def worst(key):
        i = min(range(len(fc)), key=lambda j: lines[key][j])
        return {"value": lines[key][i], "lot": fc[i].label, "lot_index": i}

    def first_gap(key):
        return next((fc[i].label for i in range(len(fc)) if lines[key][i] < 0), None)

    return {
        "lowest_fp_before": worst("fp_before"), "lowest_fp_after": worst("fp_after"),
        "closing_at_horizon": lines["closing"][-1], "closing_after_at_horizon": lines["closing_after"][-1],
        "fp_after_at_horizon": lines["fp_after"][-1],
        "gap_lots_before": sum(1 for v in lines["fp_before"] if v < 0),
        "gap_lots_after": sum(1 for v in lines["fp_after"] if v < 0),
        "first_gap_before": first_gap("fp_before"), "first_gap_after": first_gap("fp_after"),
        "below_threshold": [fc[i].label for i in range(len(fc)) if lines["fp_after"][i] < threshold],
        "holds_count": len(holds), "holds_total": sum((h.hold.amount for h in holds), ZERO),
        "holds_not_represented": sum((h.hold.amount for h in holds if h.hold.honour_lot is None), ZERO),
        "holds_with_warnings": sum(1 for h in holds if h.hold.warnings),
        "overall": max(lot_status, key=_STATUS_RANK.get) if lot_status else NO_GAP,
    }


def _tieout(inp: Inputs, erp_total: Decimal) -> dict:
    out = {"erp_total": erp_total, "model_opening": erp_total, "previous": None}
    p = inp.previous
    if p:
        prev_as_of = date.fromisoformat(p["as_of"])
        moved = sum((Decimal(v) for d, v in p["daily_net"].items()
                     if prev_as_of <= date.fromisoformat(d) < inp.as_of), ZERO)
        expected = Decimal(p["opening"]) + moved
        out["previous"] = {"as_of": prev_as_of, "opening": Decimal(p["opening"]), "movement": moved,
                           "expected": expected, "variance": erp_total - expected}
    return out
