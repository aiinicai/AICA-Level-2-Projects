"""Trial balance over the generated vouchers.

Run before shipping the XML. Three things it proves: every voucher balances,
the trial balance balances, and no payable has drifted onto the debit side —
which is the first thing anyone will notice if it is wrong.
"""
from __future__ import annotations

from app.seed import tallydata as T

# Ledgers that must not end up on the wrong side, and the side they belong on.
EXPECTED_SIGN = {
    "GST Payable": "credit",
    "TDS Payable": "credit",
    "Provident Fund Payable": "credit",
    "HDFC Term Loan": "credit",
    "Share Capital": "credit",
    "Securities Premium": "credit",
    "Product and Service Income": "credit",
    "HDFC Bank - Current 4471": "debit",
    "ICICI Bank - Collections 8802": "debit",
    "Axis Bank - Payroll 1156": "debit",
}
TOLERANCE = 1.0          # rupees; rounding to the nearest 100 accumulates


def run(verbose: bool = True) -> dict:
    model = T.build()
    vouchers = model["vouchers"]

    unbalanced = [v for v in vouchers
                  if abs(sum(l.amount for l in v.lines)) > TOLERANCE]

    movement: dict[str, float] = {}
    for v in vouchers:
        for l in v.lines:
            movement[l.ledger] = movement.get(l.ledger, 0.0) + l.amount

    opening = dict(model["opening_bank"])
    opening["HDFC FD - BG Margin 9014"] = T.FD_BALANCE
    opening["Petty Cash"] = 85_000.0
    opening["HDFC Term Loan"] = -32_000_000.0
    opening["Share Capital"] = -100_000.0
    opening["Securities Premium"] = -179_900_000.0
    # The plug: what the company had already spent before this book opens.
    opening["Accumulated Losses"] = -sum(opening.values())

    closing = dict(opening)
    for k, v in movement.items():
        closing[k] = closing.get(k, 0.0) + v

    total = sum(closing.values())

    # A bank account that finishes healthy can still have been overdrawn in
    # March. Walk the balance forward day by day.
    banks = [T.BANK, T.COLLECTIONS, T.PAYROLL_BANK]
    running = {b: opening.get(b, 0.0) for b in banks}
    lowest = {b: (running[b], None) for b in banks}
    for v in sorted(vouchers, key=lambda v: v.when):
        for l in v.lines:
            if l.ledger in running:
                running[l.ledger] += l.amount
                if running[l.ledger] < lowest[l.ledger][0]:
                    lowest[l.ledger] = (running[l.ledger], v.when)
    overdrawn = [(b, *lowest[b]) for b in banks if lowest[b][0] < 0]
    wrong_side = []
    for ledger, side in EXPECTED_SIGN.items():
        bal = closing.get(ledger, 0.0)
        if side == "credit" and bal > TOLERANCE:
            wrong_side.append((ledger, "should be credit, is debit", bal))
        if side == "debit" and bal < -TOLERANCE:
            wrong_side.append((ledger, "should be debit, is credit", bal))

    if verbose:
        print(f"\n  Trial balance as at {T.PERIOD_END:%d-%b-%Y}\n")
        print(f"  {'Ledger':<34}{'Opening':>16}{'Movement':>16}{'Closing':>16}")
        print("  " + "-" * 82)
        for ledger in sorted(set(opening) | set(movement),
                             key=lambda k: -abs(closing.get(k, 0))):
            o, mv, cl = opening.get(ledger, 0), movement.get(ledger, 0), closing.get(ledger, 0)
            if abs(cl) < 1 and abs(mv) < 1:
                continue
            print(f"  {ledger[:33]:<34}{o:>16,.0f}{mv:>16,.0f}{cl:>16,.0f}")
        print("  " + "-" * 82)
        print(f"  {'TOTAL (must be zero)':<34}{'':>32}{total:>16,.2f}")
        print()
        print(f"  vouchers                  {len(vouchers):,}")
        print(f"  unbalanced vouchers       {len(unbalanced)}")
        print(f"  ledgers on the wrong side {len(wrong_side)}")
        print(f"  accounts ever overdrawn   {len(overdrawn)}")
        for b, bal, when in overdrawn:
            print(f"      {b} fell to {bal:,.0f} on {when:%d-%b-%y}")
        for b in banks:
            print(f"      lowest: {b[:28]:<30}{lowest[b][0]:>14,.0f}"
                  f"  ({lowest[b][1]:%b-%y})" if lowest[b][1] else "")
        for w in wrong_side:
            print(f"      {w[0]} — {w[1]} ({w[2]:,.0f})")
        print(f"  receivables at close      {model['receivables_at_end']:,.0f}")
        print()
        for label, s in T.summary(model).items():
            print(f"  {label:<20} {s['months']:>2} mo   "
                  f"collections {s['collections'] / 1e7:>5.2f} Cr "
                  f"({s['collections_per_month'] / 1e5:>5.1f} L/mo)   "
                  f"net burn {s['net_burn_per_month'] / 1e5:>5.1f} L/mo")
        print()

    return {"ok": (not unbalanced and not wrong_side and not overdrawn
                   and abs(total) < TOLERANCE),
            "overdrawn": overdrawn, "lowest": lowest,
            "total": total, "unbalanced": unbalanced, "wrong_side": wrong_side,
            "opening": opening, "closing": closing, "model": model}


if __name__ == "__main__":
    import sys
    sys.exit(0 if run()["ok"] else 1)
