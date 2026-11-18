"""Calculation context and shared helpers (ported from context.ts and cache.ts)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
import decimal
from decimal import ROUND_HALF_UP, Decimal

from ..model.store import Store
from .periods import DateRange, add_days
from .taxonomy import Chart, build_chart

# decimal.js defaults: 20 significant digits, round half up. DefaultContext is copied by every new thread.
decimal.DefaultContext.prec = 20
decimal.DefaultContext.rounding = ROUND_HALF_UP
decimal.setcontext(decimal.DefaultContext)

_MEMO: dict[tuple, object] = {}


def memoize(store: Store, company_id: int, key: str, fn):
    k = (id(store), company_id, store.data_version.get(company_id, 0), key)
    if k in _MEMO:
        return _MEMO[k]
    v = fn()
    if len(_MEMO) > 400:
        _MEMO.clear()
    _MEMO[k] = v
    return v


class NotFoundError(Exception):
    pass


def ints(ids) -> str:
    """Comma-separated integer ids for an SQL IN list (ids are always integers we generated, never user text)."""
    return ",".join(str(int(i)) for i in ids) or "NULL"


@dataclass
class Ctx:
    store: Store
    company_id: int
    company: dict
    settings: dict
    chart: Chart
    books_from: str
    data_to: str | None
    inventory_mode: str
    inventory_mode_source: str
    has_items: bool
    cost_centre_id: int | None = None

    @property
    def cid(self) -> int:
        return self.company_id


def make_ctx(store: Store, company_id: int, cost_centre: str | None = None) -> Ctx:
    company = store.one("SELECT * FROM companies WHERE id = ?", [company_id])
    if not company:
        raise NotFoundError("Company not found")
    settings = json.loads(company["settings_json"] or "{}")
    span = memoize(store, company_id, "span", lambda: store.one(
        "SELECT MIN(date) AS min, MAX(date) AS max FROM vouchers WHERE company_id = ? AND is_accounting = 1", [company_id]))
    books_from = company["books_from"] or span["min"] or date.today().isoformat()
    chart = memoize(store, company_id, "chart", lambda: build_chart(store, company_id))
    mode, source = company["inventory_mode"], "configured"
    if mode == "auto":
        source = "auto"
        mode = memoize(store, company_id, "invmode", lambda: detect_inventory_mode(store, company_id, chart))
    cc_id = None
    if cost_centre:
        r = store.one("SELECT id FROM cost_centres WHERE company_id = ? AND name = ?", [company_id, cost_centre])
        cc_id = r["id"] if r else -1
    has_items = memoize(store, company_id, "hasitems", lambda: has_item_records(store, company_id))
    return Ctx(store, company_id, company, settings, chart, books_from, span["max"], mode, source, has_items, cc_id)


def has_item_records(store: Store, cid: int) -> bool:
    items = store.one("SELECT COUNT(*) AS n, COALESCE(SUM(ABS(opening_qty_e4)),0) AS v FROM stock_items WHERE company_id = ?", [cid])
    if not items["n"]:
        return False
    return items["v"] > 0 or store.scalar("SELECT COUNT(*) FROM inventory_lines WHERE company_id = ?", [cid]) > 0


def detect_inventory_mode(store: Store, cid: int, chart: Chart) -> str:
    stock_ledgers = chart.ledgers_of("inventory")
    if stock_ledgers:
        ids = ints(stock_ledgers)
        manual = store.scalar(
            f"SELECT (SELECT COUNT(*) FROM ledger_closing_values WHERE company_id = ? AND ledger_id IN ({ids})) "
            f"+ (SELECT COUNT(*) FROM ledgers WHERE id IN ({ids}) AND opening_paise <> 0)", [cid])
        if manual > 0:
            return "ledger_closing_stock"
    if has_item_records(store, cid):
        return "tally_integrated"
    return "ledger_closing_stock" if stock_ledgers else "none"


# ------------------------------------------------------------------ numeric helpers
def rupees(paise) -> float | None:
    """paise -> rupees (JavaScript Math.round semantics, so values match the Node app exactly)."""
    if paise is None:
        return None
    import math
    return math.floor(paise + 0.5) / 100 + 0


def js_num(x):
    """Return ints for whole floats like JSON.stringify does (3.0 -> 3)."""
    if isinstance(x, float) and x.is_integer() and abs(x) < 1e15:
        return int(x)
    return x


def _dp(d: Decimal, places: int) -> float:
    return float(d.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP))


def div(a, b, dp: int = 6):
    if a is None or b is None or b == 0:
        return None
    return _dp(Decimal(a) / Decimal(b), dp)


def pct(a, b):
    if a is None or b is None or b <= 0:
        return None
    return _dp(Decimal(a) / Decimal(b) * 100, 4)


def pct_change(cur, prev) -> dict:
    if cur is None or prev is None:
        return {"pct": None, "note": "Comparison unavailable"}
    if prev == 0:
        return {"pct": None, "note": "Base is zero — % change not meaningful"}
    if prev < 0:
        return {"pct": None, "note": "Base is negative — % change not meaningful; see absolute change"}
    if cur < 0:
        return {"pct": None, "note": "Changed sign — % change not meaningful; see absolute change"}
    return {"pct": _dp((Decimal(cur) - Decimal(prev)) / Decimal(prev) * 100, 4), "note": None}


# ------------------------------------------------------------------ ledger movements and balances
def movements(ctx: Ctx, r: DateRange) -> dict[int, int]:
    """Net movement (Dr +) per ledger over a date range from accounting vouchers (optionally one cost centre)."""
    def run():
        if ctx.cost_centre_id is not None:
            rows = ctx.store.rows(
                "SELECT ca.ledger_id, SUM(ca.amount_paise) AS amt FROM cost_allocations ca JOIN vouchers v ON v.id = ca.voucher_id "
                "WHERE v.company_id = ? AND v.is_accounting = 1 AND v.date BETWEEN ? AND ? AND ca.cost_centre_id = ? GROUP BY ca.ledger_id",
                [ctx.cid, r[0], r[1], ctx.cost_centre_id])
        else:
            rows = ctx.store.rows(
                "SELECT vl.ledger_id, SUM(vl.amount_paise) AS amt FROM voucher_lines vl JOIN vouchers v ON v.id = vl.voucher_id "
                "WHERE v.company_id = ? AND v.is_accounting = 1 AND v.date BETWEEN ? AND ? GROUP BY vl.ledger_id",
                [ctx.cid, r[0], r[1]])
        return {x["ledger_id"]: int(x["amt"]) for x in rows}
    return memoize(ctx.store, ctx.cid, f"mov:{r[0]}:{r[1]}:{ctx.cost_centre_id}", run)


def balances_at(ctx: Ctx, as_of: str) -> dict[int, int]:
    """Closing balance (Dr +) per ledger at the end of `as_of` = master opening + all movements up to and including it."""
    def run():
        out = {e.ledger_id: e.opening_paise for e in ctx.chart.entries.values()}
        if as_of < ctx.books_from:
            return out
        rows = ctx.store.rows(
            "SELECT vl.ledger_id, SUM(vl.amount_paise) AS amt FROM voucher_lines vl JOIN vouchers v ON v.id = vl.voucher_id "
            "WHERE v.company_id = ? AND v.is_accounting = 1 AND v.date <= ? GROUP BY vl.ledger_id", [ctx.cid, as_of])
        for x in rows:
            out[x["ledger_id"]] = out.get(x["ledger_id"], 0) + int(x["amt"])
        return out
    return memoize(ctx.store, ctx.cid, f"bal:{as_of}", run)


def sum_of(m: dict[int, int], ids) -> int:
    return sum(m.get(i, 0) for i in ids)


def day_before(iso: str) -> str:
    return add_days(iso, -1)
