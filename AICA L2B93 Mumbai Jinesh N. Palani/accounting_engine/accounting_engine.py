"""
Accounting engine: normalized trade dict (from broker_parsers) -> a set of
balanced TallyPrime vouchers (Purchase / Sales / Journal).

Client profile (per capstone brief): pure trading business, no capital
gains treatment. Every contract note's trades are split four ways:

  - Speculation      : intraday equity (MIS), netted same-day
  - Equity           : delivery-based equity, treated as stock-in-trade
  - Futures          : kept separate from options
  - Options          : kept separate from futures

Charges: brokerage, exchange transaction charges and SEBI charges attract
GST and are booked with an input-credit line; STT and stamp duty are
pure-agent pass-throughs (per Zerodha's own note wording) and are booked
as a straight expense with no GST leg.

The broker's running account with the client is used as the balancing
("plug") ledger so every voucher is Dr = Cr by construction -- this
mirrors how the capstone's original engine was validated (see project
progress log: "balances Dr=Cr=...").

Equity DELIVERY trades (genuine stock-in-trade) are posted as Purchase /
Sales vouchers with per-scrip stock-item inventory allocations, rather
than a single rupee-value ledger line, so TallyPrime actually tracks
quantity-wise inventory per symbol (visible in Stock Summary) -- a plain
Journal voucher has no concept of inventory at all, so a ledger-only
posting could never create a stock entry no matter which group it sits
under. Everything else (speculation, futures, options, charges, GST,
STT/stamp duty) stays on a plain Journal voucher, since none of those are
actual deliverable stock.

Deliberately NOT tagged for GST anywhere in this module: under Schedule
III of the CGST Act, "securities" are excluded from the definition of
both goods and services, so trading in listed shares is outside GST's
scope entirely. The Purchase/Sales ledgers and stock items created here
carry no GST-applicability or HSN/SAC tags, so they can never be picked
up by a GST return even if the client's Tally company has GST enabled for
other business lines.
"""
from __future__ import annotations

SEGMENT_LEDGERS = {
    "equity_intraday": "Speculation Profit and Loss A/c",
    "futures": "Futures Trading Account",
    "options": "Options Trading Account",
}

# Parent group for each fixed ledger this app posts to -- used to
# auto-create the ledger in TallyPrime (under one of Tally's own built-in
# primary/sub groups, so no group setup is needed first either) the first
# time it's referenced, so the practice never has to pre-create ledgers by
# hand for a hands-off pipeline. The broker running-account ledger's name
# is dynamic (one per broker+client), so its group is added separately,
# below, wherever the voucher is built.
LEDGER_GROUPS = {
    SEGMENT_LEDGERS["equity_intraday"]: "Indirect Incomes",
    SEGMENT_LEDGERS["futures"]: "Indirect Incomes",
    SEGMENT_LEDGERS["options"]: "Indirect Incomes",
    "Brokerage & Transaction Charges": "Indirect Expenses",
    "GST Input Credit": "Duties & Taxes",
    "STT & Stamp Duty (Statutory Levies)": "Indirect Expenses",
}
BROKER_LEDGER_GROUP = "Sundry Creditors"

# Equity-delivery stock-in-trade: booked as Purchase/Sales vouchers with
# inventory, not a plain ledger (see module docstring).
STOCK_GROUP_NAME = "Equity Shares - Stock in Trade"
STOCK_UOM_NAME = "Shares"
PURCHASE_LEDGER = "Purchase - Equity Shares"
SALES_LEDGER = "Sales - Equity Shares"
LEDGER_GROUPS[PURCHASE_LEDGER] = "Purchase Accounts"
LEDGER_GROUPS[SALES_LEDGER] = "Sales Accounts"


def _round2(x: float) -> float:
    return round(x + 1e-9, 2)


def split_equity_speculation(trades: list[dict]) -> dict:
    """Group trades by segment, netting equity_intraday (speculation)
    same-day, and net buy/sell value for futures/options. Equity delivery
    keeps buy and sell legs separate (stock-in-trade), since a stock
    ledger should reflect actual gross purchases and sales, not a net."""
    by_segment: dict[str, list[dict]] = {"equity_intraday": [], "equity_delivery": [], "futures": [], "options": []}
    for t in trades:
        seg = t.get("segment")
        if seg not in by_segment:
            raise ValueError(f"Unknown trade segment: {seg}")
        by_segment[seg].append(t)
    return by_segment


def _plug(lines: list[dict], broker_ledger: str) -> None:
    """Appends whatever broker-ledger line is needed to make `lines`
    balance on its own (Dr total == Cr total) -- used independently for
    each Tally voucher (Purchase, Sales, Journal), since Tally requires
    every individual voucher to balance by itself, not just the contract
    note as a whole."""
    total_dr = _round2(sum(l["amount"] for l in lines if l["dr_cr"] == "Dr"))
    total_cr = _round2(sum(l["amount"] for l in lines if l["dr_cr"] == "Cr"))
    diff = _round2(total_dr - total_cr)
    if diff > 0:
        lines.append({"ledger": broker_ledger, "dr_cr": "Cr", "amount": diff})
    elif diff < 0:
        lines.append({"ledger": broker_ledger, "dr_cr": "Dr", "amount": abs(diff)})


def build_voucher(normalized: dict, broker_ledger_prefix: str = "Broker") -> dict:
    trades = normalized.get("trades", [])
    charges = normalized.get("charges", {})
    by_segment = split_equity_speculation(trades)
    broker = normalized.get("broker", "").title()
    account_code = normalized.get("account_code", "UNKNOWN")
    note_no = normalized.get("contract_note_no", "UNKNOWN")
    trade_date = normalized.get("trade_date", "")
    broker_ledger = f"{broker_ledger_prefix} - {broker} ({account_code})"
    base_narration = f"Contract note {note_no} dated {trade_date} - {broker} ({account_code}) - auto-posted by AutoContract2Tally"

    # --- Equity delivery: per-scrip stock-item inventory, Purchase (buys) / Sales (sells) ---
    buy_rows = [t for t in by_segment["equity_delivery"] if t["buy_sell"] == "B"]
    sell_rows = [t for t in by_segment["equity_delivery"] if t["buy_sell"] == "S"]
    stock_items: dict[str, str] = {t["symbol"]: STOCK_GROUP_NAME for t in by_segment["equity_delivery"]}

    vouchers = []
    if buy_rows:
        inv_lines = [
            {"stock_item": t["symbol"], "quantity": t["quantity"], "rate": t["price"], "amount": _round2(t["value"])}
            for t in buy_rows
        ]
        purchase_total = _round2(sum(l["amount"] for l in inv_lines))
        vouchers.append({
            "voucher_type": "Purchase",
            "narration": base_narration + " (equity delivery -- purchase)",
            "party_ledger": broker_ledger,
            "party_amount": purchase_total,  # Cr broker (money paid out to buy)
            "inventory_lines": inv_lines,
            "inventory_ledger": PURCHASE_LEDGER,
        })
    if sell_rows:
        inv_lines = [
            {"stock_item": t["symbol"], "quantity": t["quantity"], "rate": t["price"], "amount": _round2(t["value"])}
            for t in sell_rows
        ]
        sales_total = _round2(sum(l["amount"] for l in inv_lines))
        vouchers.append({
            "voucher_type": "Sales",
            "narration": base_narration + " (equity delivery -- sale)",
            "party_ledger": broker_ledger,
            "party_amount": sales_total,  # Dr broker (money received from selling)
            "inventory_lines": inv_lines,
            "inventory_ledger": SALES_LEDGER,
        })

    # --- Everything else: a plain Journal voucher ---
    journal_lines = []
    for seg in ("equity_intraday", "futures", "options"):
        seg_trades = by_segment[seg]
        if not seg_trades:
            continue
        buys = sum(t["value"] for t in seg_trades if t["buy_sell"] == "B")
        sells = sum(t["value"] for t in seg_trades if t["buy_sell"] == "S")
        net = _round2(sells - buys)
        if net == 0:
            continue
        ledger = SEGMENT_LEDGERS[seg]
        if net > 0:
            journal_lines.append({"ledger": ledger, "dr_cr": "Cr", "amount": net})  # net profit
        else:
            journal_lines.append({"ledger": ledger, "dr_cr": "Dr", "amount": abs(net)})  # net loss

    brokerage_bucket = _round2(
        charges.get("brokerage", 0) + charges.get("exchange_txn_charges", 0) + charges.get("sebi_charges", 0)
    )
    if brokerage_bucket:
        journal_lines.append({"ledger": "Brokerage & Transaction Charges", "dr_cr": "Dr", "amount": brokerage_bucket})

    gst = _round2(charges.get("gst", 0))
    if gst:
        journal_lines.append({"ledger": "GST Input Credit", "dr_cr": "Dr", "amount": gst})

    pure_agent = _round2(charges.get("stt", 0) + charges.get("stamp_duty", 0))
    if pure_agent:
        journal_lines.append({"ledger": "STT & Stamp Duty (Statutory Levies)", "dr_cr": "Dr", "amount": pure_agent})

    if journal_lines:
        _plug(journal_lines, broker_ledger)  # this voucher's own share of the broker running account
        vouchers.append({
            "voucher_type": "Journal",
            "narration": base_narration,
            "lines": journal_lines,
        })

    # --- Ledgers to auto-create (masters-before-vouchers) ---
    ledger_groups = {broker_ledger: BROKER_LEDGER_GROUP}
    for l in journal_lines:
        if l["ledger"] != broker_ledger:
            ledger_groups[l["ledger"]] = LEDGER_GROUPS.get(l["ledger"], "Indirect Expenses")
    if buy_rows:
        ledger_groups[PURCHASE_LEDGER] = LEDGER_GROUPS[PURCHASE_LEDGER]
    if sell_rows:
        ledger_groups[SALES_LEDGER] = LEDGER_GROUPS[SALES_LEDGER]

    # --- Flattened view across every voucher, for the dashboard's Tally
    # Accounting step and as an overall Dr=Cr sanity check -- shows the
    # whole contract note's effect in one balanced table even though it's
    # actually posted to Tally as separate, individually-balanced Purchase
    # /Sales/Journal vouchers (Tally requires inventory allocations to live
    # on a Purchase/Sales voucher, never a Journal). ---
    flat_lines = []
    for t in buy_rows:
        flat_lines.append({"ledger": f"{t['symbol']} (Stock Item — Purchase)", "dr_cr": "Dr", "amount": _round2(t["value"])})
    for t in sell_rows:
        flat_lines.append({"ledger": f"{t['symbol']} (Stock Item — Sale)", "dr_cr": "Cr", "amount": _round2(t["value"])})
    flat_lines.extend(l for l in journal_lines if l["ledger"] != broker_ledger)
    _plug(flat_lines, broker_ledger)  # single combined broker figure, for an overall reconciliation view

    return {
        "date": trade_date,
        "narration": base_narration,
        "vouchers": vouchers,
        "ledger_groups": ledger_groups,
        "stock_items": stock_items,
        "stock_group": STOCK_GROUP_NAME,
        "stock_uom": STOCK_UOM_NAME,
        "lines": flat_lines,
        # Needed so the XML builder can attach a bill (BILLALLOCATIONS.LIST
        # "New Ref") to every ledger entry against the broker -- Tally's
        # default "Sundry Creditors" group has bill-wise tracking switched
        # on, and a bill-wise ledger entry with no bill reference gets
        # rejected outright ("Voucher totals do not match" was the actual
        # symptom, confirmed live against a real Tally instance -- Tally
        # simply doesn't count that entry into the voucher total at all
        # without a bill allocation). contract_note_no is the base for a
        # unique bill name per voucher (this note can produce up to three
        # separate vouchers against the same broker ledger, so each needs
        # its own distinct "New Ref" name).
        "broker_ledger": broker_ledger,
        "contract_note_no": note_no,
    }
