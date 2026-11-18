"""Stock valuation sources, replay and item analytics (ported from inventory.ts).

Source priority: Tally valuation snapshot -> imported snapshot -> opening master (before books start) -> moving
weighted-average replay (always labelled 'estimated'). Manual Stock-in-Hand ledgers win for 'ledger_closing_stock'.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .context import Ctx, balances_at, ints, memoize
from .periods import DateRange, add_days, month_end, months_in

RETURN_IN = {"Credit Note", "Rejections In"}


@dataclass
class StockValue:
    total_paise: int | None
    by_item: dict[int, tuple[int, int]]  # item id -> (qty_e4, value_paise)
    status: str
    source: str
    notes: list[str] = field(default_factory=list)


def _snap(state: dict[int, list]) -> dict[int, tuple[int, int]]:
    return {i: (s[0], _js_round(s[1])) for i, s in state.items()}


def _js_round(x: float) -> int:
    import math
    return math.floor(x + 0.5)


def replay(ctx: Ctx, dates: list[str]):
    def run():
        state: dict[int, list] = {}  # id -> [q, v, a]
        for it in ctx.store.rows("SELECT id, opening_qty_e4, opening_value_paise FROM stock_items WHERE company_id = ? ORDER BY id", [ctx.cid]):
            q, v = it["opening_qty_e4"], it["opening_value_paise"]
            state[it["id"]] = [q, v, v / q if q > 0 else 0]
        sorted_dates = sorted(set(dates))
        at: dict[str, dict] = {}
        line_cost: dict[int, int] = {}
        negative: list[tuple[int, str, int]] = []
        di = 0
        lines = ctx.store.rows(
            "SELECT il.id, il.stock_item_id, il.direction, il.qty_e4, il.value_paise, v.date, v.base_type "
            "FROM inventory_lines il JOIN vouchers v ON v.id = il.voucher_id "
            "WHERE v.company_id = ? AND v.is_inventory = 1 ORDER BY v.date, v.id, il.line_no", [ctx.cid])
        for l in lines:
            while di < len(sorted_dates) and sorted_dates[di] < l["date"]:
                at[sorted_dates[di]] = _snap(state)
                di += 1
            s = state.get(l["stock_item_id"]) or [0, 0, 0]
            avg = s[1] / s[0] if s[0] > 0 else s[2]
            if l["direction"] == "in":
                val = avg * l["qty_e4"] if l["base_type"] in RETURN_IN or l["value_paise"] == 0 else l["value_paise"]
                s[0] += l["qty_e4"]
                s[1] += val
                if s[0] > 0:
                    s[2] = s[1] / s[0]
            else:
                cost = avg * l["qty_e4"]
                line_cost[l["id"]] = _js_round(cost)
                s[0] -= l["qty_e4"]
                s[1] -= cost
                if s[0] < 0:
                    negative.append((l["stock_item_id"], l["date"], s[0]))
                if s[0] == 0:
                    s[1] = 0
            state[l["stock_item_id"]] = s
        while di < len(sorted_dates):
            at[sorted_dates[di]] = _snap(state)
            di += 1
        return at, line_cost, negative
    return memoize(ctx.store, ctx.cid, f"replay:{','.join(dates)}", run)


def standard_dates(ctx: Ctx) -> list[str]:
    to = ctx.data_to or ctx.books_from
    return [month_end(m) for m in months_in(DateRange(ctx.books_from, to))]


def replay_for(ctx: Ctx, extra: list[str] | None = None):
    std = standard_dates(ctx)
    need = [d for d in (extra or []) if d not in std]
    return replay(ctx, std + need if need else std)


def _opening_master(ctx: Ctx) -> StockValue:
    rows = ctx.store.rows("SELECT id, opening_qty_e4, opening_value_paise FROM stock_items WHERE company_id = ?", [ctx.cid])
    return StockValue(sum(r["opening_value_paise"] for r in rows),
                      {r["id"]: (r["opening_qty_e4"], r["opening_value_paise"]) for r in rows}, "actual", "opening_master",
                      ["Opening stock from stock item masters."])


def stock_value_at(ctx: Ctx, as_of: str) -> StockValue:
    if ctx.inventory_mode == "none":
        return StockValue(0, {}, "actual", "not_tracked",
                          ["Inventory is configured as not tracked; purchases are treated as consumed in the period."])
    if ctx.inventory_mode == "ledger_closing_stock":
        return manual_stock_at(ctx, as_of)

    def snapdate():
        r = ctx.store.one("SELECT MAX(as_of) AS d FROM stock_snapshots WHERE company_id = ? AND as_of <= ?", [ctx.cid, as_of])
        s = r["d"] if r else None
        if not s or s == as_of:
            return s
        moved = ctx.store.scalar(
            "SELECT COUNT(*) FROM inventory_lines il JOIN vouchers v ON v.id = il.voucher_id "
            "WHERE v.company_id = ? AND v.is_inventory = 1 AND v.date > ? AND v.date <= ?", [ctx.cid, s, as_of])
        return None if moved else s
    sd = memoize(ctx.store, ctx.cid, f"snapdate:{as_of}", snapdate)
    snaps = [] if sd is None else ctx.store.rows(
        "SELECT stock_item_id, qty_e4, value_paise, source FROM stock_snapshots WHERE company_id = ? AND as_of = ? ORDER BY stock_item_id",
        [ctx.cid, sd])
    if snaps:
        from_tally = all(s["source"] == "tally" for s in snaps)
        carried = [f"Valuation dated {sd}; no stock movements between then and {as_of}."] if sd != as_of else []
        return StockValue(sum(s["value_paise"] for s in snaps), {s["stock_item_id"]: (s["qty_e4"], s["value_paise"]) for s in snaps},
                          "actual", "tally_snapshot" if from_tally else "import_snapshot",
                          ["Valued by Tally (item costing methods) as at this date." if from_tally else "From imported stock valuation file.", *carried])
    if ctx.inventory_mode == "external":
        return StockValue(None, {}, "unavailable", "unavailable",
                          ["Stock is maintained outside Tally and no valuation was imported for this date. Import a stock valuation file to enable COGS and inventory metrics."])
    if as_of < ctx.books_from:
        return _opening_master(ctx)
    return estimated_stock_at(ctx, as_of)


def manual_stock_at(ctx: Ctx, as_of: str) -> StockValue:
    def run():
        ids = ctx.chart.ledgers_of("inventory")
        if not ids:
            return StockValue(0, {}, "actual", "stock_ledgers", ["No Stock-in-Hand ledgers: closing stock is nil."])
        bal = balances_at(ctx, as_of)
        opening_or_books = as_of < ctx.books_from
        total, exact, carried = 0, True, set()
        for i in ids:
            v = None if opening_or_books else ctx.store.one(
                "SELECT as_of, amount_paise FROM ledger_closing_values WHERE company_id = ? AND ledger_id = ? AND as_of <= ? AND as_of >= ? "
                "ORDER BY as_of DESC LIMIT 1", [ctx.cid, i, as_of, ctx.books_from])
            if v:
                total += v["amount_paise"]
                if v["as_of"] != as_of:
                    exact = False
                    carried.add(v["as_of"])
            else:
                total += bal.get(i, 0)
                if not opening_or_books:
                    exact = False
        notes = ["Manual closing stock from Stock-in-Hand ledger(s) — used for financial statements in preference to item-level stock records."]
        if opening_or_books:
            notes.append("Opening stock = Stock-in-Hand ledger opening balance.")
        elif carried:
            notes.append(f"No manual closing stock entered for {as_of}; last value entered on {sorted(carried)[-1]} is used.")
        elif not exact:
            notes.append(f"No manual closing stock entered since the books start; the opening value is used for {as_of}.")
        return StockValue(total, {}, "actual" if exact else "estimated", "stock_ledgers", notes)
    return memoize(ctx.store, ctx.cid, f"manualstock:{as_of}", run)


def estimated_stock_at(ctx: Ctx, as_of: str) -> StockValue:
    if as_of < ctx.books_from:
        return _opening_master(ctx)
    at, _, _ = replay_for(ctx, [as_of])
    by_item = at.get(as_of, {})
    return StockValue(sum(v[1] for v in by_item.values()), by_item, "estimated", "estimated_replay",
                      ["No usable Tally valuation for this date; estimated by replaying stock movements at moving weighted-average cost. Tally may use a different costing method per item."])


def item_level_stock_at(ctx: Ctx, as_of: str) -> StockValue:
    sv = stock_value_at(ctx, as_of)
    if sv.by_item or not ctx.has_items:
        return sv
    est = estimated_stock_at(ctx, as_of)
    return StockValue(est.total_paise, est.by_item, est.status, est.source,
                      [*est.notes, "Item-level values are estimates from stock records; financial statements use the manual closing stock."])


def opening_stock_for(ctx: Ctx, r: DateRange) -> StockValue:
    return stock_value_at(ctx, add_days(r[0], -1))


def _is_snapshot(s: StockValue) -> bool:
    return s.source in ("tally_snapshot", "import_snapshot")


def period_stock(ctx: Ctx, r: DateRange) -> tuple[StockValue, StockValue]:
    """Opening and closing stock on one consistent basis (if either side is estimated, both are)."""
    opening, closing = opening_stock_for(ctx, r), stock_value_at(ctx, r[1])
    if _is_snapshot(opening) != _is_snapshot(closing) and "estimated_replay" in (opening.source, closing.source):
        o = estimated_stock_at(ctx, add_days(r[0], -1)) if _is_snapshot(opening) else opening
        c = estimated_stock_at(ctx, r[1]) if _is_snapshot(closing) else closing
        note = "Opening and closing stock both estimated so they are on the same basis (a Tally valuation was available for only one of them)."
        return (StockValue(o.total_paise, o.by_item, o.status, o.source, [*o.notes, note]),
                StockValue(c.total_paise, c.by_item, c.status, c.source, [*c.notes, note]))
    return opening, closing


# ------------------------------------------------------------------ item analytics (used by revenue analysis)
@dataclass
class ItemRow:
    item_id: int
    name: str
    group: str | None
    unit: str | None
    sales_qty: float = 0
    sales_value: int = 0
    return_qty: float = 0
    return_value: int = 0
    net_qty: float = 0
    net_sales: int = 0
    est_cost: float = 0
    gross_profit: float = 0
    margin_pct: float | None = None
    avg_selling_price: float | None = None
    avg_cost: float | None = None
    purchase_qty: float = 0
    purchase_value: int = 0
    avg_purchase_rate: float | None = None
    units: list[str] = field(default_factory=list)
    closing_qty: float | None = None
    closing_value: int | None = None
    last_outward: str | None = None
    last_inward: str | None = None
    outward_count: int = 0


def item_analytics(ctx: Ctx, r: DateRange) -> list[ItemRow]:
    def run():
        _, line_cost, _ = replay_for(ctx, [r[1]])
        close = item_level_stock_at(ctx, r[1])
        items = ctx.store.rows("SELECT id, name, group_name, base_unit FROM stock_items WHERE company_id = ? ORDER BY name", [ctx.cid])
        rows = ctx.store.rows(
            "SELECT il.id, il.stock_item_id, il.direction, il.qty_e4, il.value_paise, v.base_type, il.unit, v.date "
            "FROM inventory_lines il JOIN vouchers v ON v.id = il.voucher_id "
            "WHERE v.company_id = ? AND v.is_inventory = 1 AND v.date BETWEEN ? AND ? ORDER BY il.id", [ctx.cid, r[0], r[1]])
        last = {x["stock_item_id"]: x for x in ctx.store.rows(
            "SELECT il.stock_item_id, MAX(CASE WHEN il.direction='out' THEN v.date END) AS lo, "
            "MAX(CASE WHEN il.direction='in' THEN v.date END) AS li, "
            "SUM(CASE WHEN il.direction='out' AND v.date BETWEEN ? AND ? THEN 1 ELSE 0 END) AS n "
            "FROM inventory_lines il JOIN vouchers v ON v.id = il.voucher_id "
            "WHERE v.company_id = ? AND v.is_inventory = 1 AND v.date <= ? GROUP BY il.stock_item_id", [r[0], r[1], ctx.cid, r[1]])}
        acc: dict[int, ItemRow] = {}
        for it in items:
            c = close.by_item.get(it["id"])
            lx = last.get(it["id"])
            acc[it["id"]] = ItemRow(it["id"], it["name"], it["group_name"], it["base_unit"],
                                    closing_qty=c[0] / 1e4 if c else None, closing_value=c[1] if c else None,
                                    last_outward=lx["lo"] if lx else None, last_inward=lx["li"] if lx else None,
                                    outward_count=int(lx["n"]) if lx and lx["n"] is not None else 0)
        pending: list[tuple[ItemRow, float]] = []
        for l in rows:
            row = acc.get(l["stock_item_id"])
            if row is None:
                continue
            q = l["qty_e4"] / 1e4
            if l["unit"] and l["unit"] not in row.units:
                row.units.append(l["unit"])
            bt, d = l["base_type"], l["direction"]
            if bt == "Sales" and d == "out":
                row.sales_qty += q
                row.sales_value += l["value_paise"]
                row.est_cost += line_cost.get(l["id"], 0)
            elif bt == "Credit Note" and d == "in":
                row.return_qty += q
                row.return_value += l["value_paise"]
                pending.append((row, q))
            elif bt == "Purchase" and d == "in":
                row.purchase_qty += q
                row.purchase_value += l["value_paise"]
            elif bt == "Debit Note" and d == "out":
                row.purchase_qty -= q
                row.purchase_value -= l["value_paise"]
        for row, q in pending:
            row.est_cost -= (row.est_cost / row.sales_qty) * q if row.sales_qty > 0 else 0
        for row in acc.values():
            row.net_qty = row.sales_qty - row.return_qty
            row.net_sales = row.sales_value - row.return_value
            row.est_cost = _js_round(row.est_cost)
            row.gross_profit = row.net_sales - row.est_cost
            row.margin_pct = (row.gross_profit / row.net_sales) * 100 if row.net_sales > 0 else None
            row.avg_selling_price = row.sales_value / row.sales_qty if row.sales_qty > 0 else None
            row.avg_cost = row.est_cost / row.net_qty if row.net_qty > 0 else None
            row.avg_purchase_rate = row.purchase_value / row.purchase_qty if row.purchase_qty > 0 else None
        return list(acc.values())
    return memoize(ctx.store, ctx.cid, f"items:{r[0]}:{r[1]}", run)
