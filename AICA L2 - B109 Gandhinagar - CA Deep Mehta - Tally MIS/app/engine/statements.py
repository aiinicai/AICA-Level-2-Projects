"""Profit & loss and balance-sheet figures (ported from statements.ts).

Storage is debit-positive paise; statement lines are shown so their *normal* balance is positive (income and
expenses both positive in the P&L; assets, liabilities and equity positive in the balance sheet).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .context import Ctx, balances_at, ints, memoize, movements, sum_of
from .inventory import StockValue, period_stock, stock_value_at
from .periods import DateRange
from .taxonomy import CLASS_BY_CODE, OPEX_CLASSES, SECTION_LABELS, is_current


@dataclass
class Figure:
    paise: int | float | None
    status: str = "actual"
    notes: list[str] = field(default_factory=list)


def fig(paise, status="actual", notes=None) -> Figure:
    return Figure(paise, status, list(notes or []))


def _worst(*s: str) -> str:
    return "unavailable" if "unavailable" in s else "estimated" if "estimated" in s else "calculated" if "calculated" in s else "actual"


def _uniq(items):
    return list(dict.fromkeys(items))


def combine(status: list[str], parts: list[Figure], value) -> Figure:
    st = _worst(*status, *[p.status for p in parts])
    if any(p.paise is None for p in parts) or st == "unavailable":
        return fig(None, "unavailable", _uniq([n for p in parts for n in p.notes]))
    return fig(value(), "calculated" if st == "actual" else st, _uniq([n for p in parts for n in p.notes]))


def ledger_lines(ctx: Ctx, mv: dict[int, int], code: str, sign: int) -> list[dict]:
    lines = [{"key": f"L{e.ledger_id}", "label": e.name, "amount": sign * mv.get(e.ledger_id, 0), "classCode": code,
              "ledgerId": e.ledger_id, "unverified": e.status != "verified"} for e in ctx.chart.by_code.get(code, [])]
    lines = [l for l in lines if l["amount"] != 0]
    lines.sort(key=lambda l: -abs(l["amount"]))
    return lines


def returns_on_revenue_ledgers(ctx: Ctx, r: DateRange) -> int:
    ids = ctx.chart.ledgers_of("revenue_operating")
    if not ids or ctx.cost_centre_id is not None:
        return 0

    def run():
        row = ctx.store.one(
            "SELECT SUM(vl.amount_paise) AS s FROM voucher_lines vl JOIN vouchers v ON v.id = vl.voucher_id "
            f"WHERE v.company_id = ? AND v.is_accounting = 1 AND v.base_type = 'Credit Note' AND v.date BETWEEN ? AND ? "
            f"AND vl.amount_paise > 0 AND vl.ledger_id IN ({ints(ids)})", [ctx.cid, r[0], r[1]])
        return int(row["s"]) if row and row["s"] is not None else 0
    return memoize(ctx.store, ctx.cid, f"ret:{r[0]}:{r[1]}", run)


FIGURE_KEYS = ["revenue", "grossSales", "salesReturns", "otherIncome", "purchases", "directExpenses", "openingStock",
               "closingStock", "cogs", "grossProfit", "opex", "ebitda", "depreciation", "ebit", "financeCost", "exceptional",
               "pbt", "tax", "netProfit", "employeeCost", "rent", "freight", "utilities", "selling", "admin", "otherOpex"]


@dataclass
class PnL:
    range: DateRange
    sections: list[dict]
    figures: dict[str, Figure]
    unclassified: list[dict]
    reliability: dict
    stock_source: dict


def profit_and_loss(ctx: Ctx, r: DateRange) -> PnL:
    return memoize(ctx.store, ctx.cid, f"pnl:{r[0]}:{r[1]}:{ctx.cost_centre_id}", lambda: _pnl(ctx, r))


def _pnl(ctx: Ctx, r: DateRange) -> PnL:
    mv = movements(ctx, r)

    def by_class(code: str) -> int:
        c = CLASS_BY_CODE[code]
        return (-1 if c.side == "income" else 1) * sum_of(mv, ctx.chart.ledgers_of(code)) + 0

    total = unverified = low = 0
    for e in ctx.chart.entries.values():
        if not e.code or CLASS_BY_CODE[e.code].statement != "PL":
            continue
        a = abs(mv.get(e.ledger_id, 0))
        total += a
        if e.status != "verified":
            unverified += a
        if e.status != "verified" and e.confidence < 0.7:
            low += a
    unverified_pct = (unverified / total) * 100 if total else 0
    low_pct = (low / total) * 100 if total else 0
    from .periods import js_to_fixed
    class_note = [f"{js_to_fixed(low_pct, 0)}% of P&L activity uses low-confidence automatic classifications; review mappings."] if low_pct > 10 else []

    rev_op = by_class("revenue_operating")
    contra_deduction = -by_class("revenue_contra")
    revenue = rev_op - contra_deduction
    returns_on_rev = returns_on_revenue_ledgers(ctx, r)
    sales_returns = contra_deduction + returns_on_rev

    purchases = by_class("cogs_purchases")
    direct = by_class("cogs_direct")
    cc = ctx.cost_centre_id is not None
    os_, cs_ = (None, None) if cc else period_stock(ctx, r)
    opening_stock = fig(os_.total_paise, os_.status, os_.notes) if os_ else fig(0, "estimated", ["Stock adjustments cannot be allocated to a cost centre; COGS shows purchases and direct costs only."])
    closing_stock = fig(cs_.total_paise, cs_.status, cs_.notes) if cs_ else fig(0, "estimated", [])
    cogs = combine([], [opening_stock, closing_stock], lambda: purchases + direct + opening_stock.paise - closing_stock.paise)
    if ctx.inventory_mode == "none" and purchases != 0:
        cogs.notes.append("Inventory not tracked: COGS assumes all purchases were consumed in the period.")

    rev = fig(revenue, "actual", class_note)
    gross_profit = combine([], [rev, cogs], lambda: revenue - cogs.paise)
    opex_parts = {c: by_class(c) for c in OPEX_CLASSES}
    opex = sum(opex_parts.values())
    depreciation, finance_cost, exceptional, tax, other_income = (by_class(c) for c in
        ("depreciation", "finance_cost", "exceptional", "tax_expense", "income_other"))

    ebitda_notes = list(class_note)
    if not ctx.chart.ledgers_of("depreciation"):
        ebitda_notes.append("No depreciation ledger identified — EBITDA may equal EBIT.")
    ebitda = combine(["estimated" if low_pct > 10 else "calculated"], [gross_profit], lambda: gross_profit.paise - opex)
    ebitda.notes.extend(ebitda_notes)
    ebit = combine([], [ebitda], lambda: ebitda.paise - depreciation)
    pbt = combine([], [ebit], lambda: ebit.paise + other_income - finance_cost - exceptional)
    net_profit = combine([], [pbt], lambda: pbt.paise - tax)

    unclassified = [{"ledgerId": e.ledger_id, "name": e.name, "movement": mv[e.ledger_id]}
                    for e in ctx.chart.entries.values() if not e.code and mv.get(e.ledger_id, 0) != 0]

    def section_of(codes: list[str]) -> list[dict]:
        out = []
        for code in codes:
            c = CLASS_BY_CODE[code]
            children = ledger_lines(ctx, mv, code, -1 if c.side == "income" else 1)
            amount = sum(l["amount"] for l in children)
            if amount != 0 or children:
                out.append({"key": code, "label": c.label, "amount": amount, "classCode": code, "children": children})
        return out

    sections = [{"key": "revenue", "label": SECTION_LABELS["revenue"], "total": revenue, "lines": section_of(["revenue_operating", "revenue_contra"])}]
    cogs_lines = []
    if opening_stock.paise:
        cogs_lines.append({"key": "opening_stock", "label": "Opening stock", "amount": opening_stock.paise, "status": opening_stock.status})
    cogs_lines += section_of(["cogs_purchases", "cogs_direct"])
    if closing_stock.paise:
        cogs_lines.append({"key": "closing_stock", "label": "Less: closing stock", "amount": -closing_stock.paise, "status": closing_stock.status})
    sections.append({"key": "cogs", "label": SECTION_LABELS["cogs"], "total": cogs.paise or 0, "lines": cogs_lines})
    sections.append({"key": "opex", "label": SECTION_LABELS["opex"], "total": opex, "lines": section_of(OPEX_CLASSES)})
    sections.append({"key": "da", "label": SECTION_LABELS["da"], "total": depreciation, "lines": section_of(["depreciation"])})
    sections.append({"key": "other_income", "label": SECTION_LABELS["other_income"], "total": other_income, "lines": section_of(["income_other"])})
    sections.append({"key": "finance", "label": SECTION_LABELS["finance"], "total": finance_cost, "lines": section_of(["finance_cost"])})
    sections.append({"key": "exceptional", "label": SECTION_LABELS["exceptional"], "total": exceptional, "lines": section_of(["exceptional"])})
    sections.append({"key": "tax", "label": SECTION_LABELS["tax"], "total": tax, "lines": section_of(["tax_expense"])})

    figures = {
        "revenue": rev,
        "grossSales": fig(revenue + sales_returns, "calculated", ["Includes credit-note debits posted to sales ledgers as returns."] if returns_on_rev else []),
        "salesReturns": fig(sales_returns, "calculated"), "otherIncome": fig(other_income), "purchases": fig(purchases),
        "directExpenses": fig(direct), "openingStock": opening_stock, "closingStock": closing_stock, "cogs": cogs,
        "grossProfit": gross_profit, "opex": fig(opex, "actual", class_note), "ebitda": ebitda, "depreciation": fig(depreciation),
        "ebit": ebit, "financeCost": fig(finance_cost), "exceptional": fig(exceptional), "pbt": pbt, "tax": fig(tax),
        "netProfit": net_profit, "employeeCost": fig(opex_parts["opex_employee"]), "rent": fig(opex_parts["opex_rent"]),
        "freight": fig(opex_parts["opex_freight"]), "utilities": fig(opex_parts["opex_utilities"]),
        "selling": fig(opex_parts["opex_selling"]), "admin": fig(opex_parts["opex_admin"]), "otherOpex": fig(opex_parts["opex_other"]),
    }
    return PnL(r, sections, figures, unclassified,
               {"unverifiedSharePct": unverified_pct, "lowConfidenceSharePct": low_pct},
               {"opening": os_.source if os_ else "not_tracked", "closing": cs_.source if cs_ else "not_tracked"})


# ------------------------------------------------------------------ balance sheet
def balance_sheet(ctx: Ctx, as_of: str) -> dict:
    return memoize(ctx.store, ctx.cid, f"bs:{as_of}", lambda: _bs(ctx, as_of))


def _bs(ctx: Ctx, as_of: str) -> dict:
    bal = balances_at(ctx, as_of)
    notes: list[str] = []
    sec: dict[str, list[dict]] = {}

    def push(section: str, line: dict):
        sec.setdefault(section, []).append(line)

    pl_cum = unclassified = debt = short_debt = neg_cash_bank = non_quick = 0
    by_code_totals: dict[str, int] = {}
    manual_stock = ctx.inventory_mode == "ledger_closing_stock"
    stock_ledger_balance = 0
    unclassified_lines: list[dict] = []

    for e in ctx.chart.entries.values():
        b = bal.get(e.ledger_id, 0)
        if not e.code:
            if b != 0:
                unclassified += -b
                unclassified_lines.append({"key": f"L{e.ledger_id}", "label": e.name, "amount": -b, "ledgerId": e.ledger_id, "unverified": True})
            continue
        c = CLASS_BY_CODE[e.code]
        if c.statement == "PL":
            pl_cum += -b
            continue
        if b == 0:
            continue
        if e.code == "pl_account":
            pl_cum += -b
            continue
        tax_debit = e.code == "tax_balance" and b > 0
        side = "asset" if tax_debit else c.side
        section = "current_assets" if tax_debit else c.section
        amount = b if side == "asset" else -b
        code = "tax_balance_debit" if tax_debit else e.code
        cur = is_current(e)
        if cur is not None and not tax_debit and side == "asset":
            section = "current_assets" if cur else "noncurrent_assets"
        if cur is not None and not tax_debit and side == "liability":
            section = "current_liabilities" if cur else "noncurrent_liabilities"
        if e.code in ("cash", "bank") and b < 0:
            neg_cash_bank += b
        ib = e.attrs.get("interestBearing")
        if ib is None:
            ib = e.code in ("borrowing_long", "borrowing_short")
        if ib and side == "liability":
            debt += -b
            if section == "current_liabilities":
                short_debt += -b
        if manual_stock and e.code == "inventory":
            stock_ledger_balance += b
            continue
        if e.attrs.get("nonQuick") and section == "current_assets":
            non_quick += amount
        by_code_totals[code] = by_code_totals.get(code, 0) + amount
        push(section, {"key": f"L{e.ledger_id}", "label": e.name, "amount": amount, "classCode": code, "ledgerId": e.ledger_id,
                       "unverified": e.status != "verified"})

    inventory = by_code_totals.get("inventory", 0)
    inventory_status = "actual"
    stock_adj = 0
    if ctx.inventory_mode in ("tally_integrated", "external"):
        sv = stock_value_at(ctx, as_of)
        inventory_status = sv.status
        notes.extend(sv.notes)
        base = ctx.store.scalar("SELECT COALESCE(SUM(opening_value_paise),0) FROM stock_items WHERE company_id = ?", [ctx.cid])
        if sv.total_paise is None:
            inventory = None
            notes.append("Inventory value unavailable: balance sheet excludes stock and accumulated profit excludes the stock adjustment.")
        else:
            push("current_assets", {"key": "stock_items", "label": "Inventories (stock items)", "amount": sv.total_paise, "classCode": "inventory", "status": sv.status})
            inventory = (inventory or 0) + sv.total_paise
            stock_adj = sv.total_paise - base
    if manual_stock:
        sv = stock_value_at(ctx, as_of)
        inventory_status = sv.status
        notes.extend(sv.notes)
        push("current_assets", {"key": "manual_stock", "label": "Inventories (manual closing stock)", "amount": sv.total_paise or 0, "classCode": "inventory", "status": sv.status})
        inventory = sv.total_paise or 0
        stock_adj = inventory - stock_ledger_balance
    opening_stock_base = ctx.store.scalar("SELECT COALESCE(SUM(opening_value_paise),0) FROM stock_items WHERE company_id = ?", [ctx.cid]) \
        if ctx.inventory_mode == "tally_integrated" else 0
    opening_difference = sum(e.opening_paise for e in ctx.chart.entries.values()) + opening_stock_base

    accumulated = pl_cum + stock_adj
    push("equity", {"key": "accumulated_pl", "label": "Profit & Loss A/c (accumulated, incl. current period)", "amount": accumulated,
                    "classCode": "pl_account", "status": "estimated" if inventory_status == "estimated" else "calculated"})
    if opening_difference != 0:
        push("other", {"key": "opening_diff", "label": "Difference in opening balances", "amount": opening_difference, "status": "calculated"})
        notes.append('Ledger opening balances do not net to zero — Tally shows this as "Difference in opening balances".')
    if unclassified_lines:
        unclassified_lines.sort(key=lambda l: -abs(l["amount"]))
        push("other", {"key": "unclassified", "label": "Unclassified balances (map these ledgers)", "amount": unclassified, "children": unclassified_lines})

    order = [("equity", "liabilities"), ("noncurrent_liabilities", "liabilities"), ("current_liabilities", "liabilities"),
             ("other", "liabilities"), ("noncurrent_assets", "assets"), ("current_assets", "assets")]
    sections = []
    for key, side in order:
        flat = sec.get(key, [])
        groups: dict[str, dict] = {}
        loose: list[dict] = []
        for l in flat:
            if "ledgerId" not in l or not l.get("classCode"):
                loose.append(l)
                continue
            cc = l["classCode"]
            label = "Duties & taxes (debit balances / input credits)" if cc == "tax_balance_debit" else (CLASS_BY_CODE[cc].label if cc in CLASS_BY_CODE else cc)
            g = groups.setdefault(cc, {"key": cc, "label": label, "amount": 0, "classCode": cc, "children": []})
            g["amount"] += l["amount"]
            g["children"].append(l)
        for g in groups.values():
            g["children"].sort(key=lambda x: -abs(x["amount"]))
        lines = sorted([*groups.values(), *loose], key=lambda x: -abs(x["amount"]))
        sections.append({"key": key, "label": SECTION_LABELS[key], "side": side, "total": sum(l["amount"] for l in lines), "lines": lines})

    tot = lambda k: next(s for s in sections if s["key"] == k)["total"]
    total_assets = tot("noncurrent_assets") + tot("current_assets")
    total_liabilities = tot("noncurrent_liabilities") + tot("current_liabilities")
    equity, other = tot("equity"), tot("other")
    difference = total_assets - (total_liabilities + equity + other)
    if abs(difference) > 100:
        notes.append("Assets do not equal liabilities + equity: check unbalanced vouchers in Data Quality.")
    current_assets = tot("current_assets")
    g = lambda c: by_code_totals.get(c, 0)
    return {
        "asOf": as_of, "sections": sections, "notes": _uniq(notes),
        "totals": {
            "totalAssets": total_assets, "totalLiabilities": total_liabilities, "equity": equity, "currentAssets": current_assets,
            "currentLiabilities": tot("current_liabilities"), "nonCurrentAssets": tot("noncurrent_assets"),
            "nonCurrentLiabilities": tot("noncurrent_liabilities"), "cash": g("cash"), "bank": g("bank"),
            "tradeReceivables": g("trade_receivable"), "tradePayables": g("trade_payable"), "inventory": inventory,
            "inventoryStatus": inventory_status, "debt": debt, "shortTermDebt": short_debt, "longTermDebt": debt - short_debt,
            "fixedAssets": g("fixed_asset"), "accumulatedProfit": accumulated, "openingDifference": opening_difference,
            "suspenseAndOther": other, "unclassified": unclassified, "difference": difference,
            "quickAssets": None if inventory is None else current_assets - inventory - non_quick, "negativeCashBank": neg_cash_bank,
        },
    }
