"""Seventeen months of Northwind Robotics, as Tally would hold it.

FY 2025-26 in full, plus FY 2026-27 to 31-Aug-2026 — so the tool has a prior
year to compare against rather than a single quarter hanging in space.

The point of this module is that **nothing is asserted**. Sales are billed,
receipts settle those bills oldest-first, and what is still outstanding on
31-Aug-2026 is whatever the arithmetic leaves — not a number typed in to look
right. Opening cash is back-solved so the closing position lands on the figure
the rest of the demonstration uses. If you change a multiplier below, every
downstream figure moves with it, which is the property that makes the
demonstration defensible when a CA reads the trial balance.

One source, two consumers: `tally_export.py` writes importable XML from this,
and `mock_tally.py` serves the same data over HTTP. A demo whose two paths
disagreed would be worse than one path.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from app.seed.exampledata import _MONTHLY_IN, _MONTHLY_OUT

# ---------------------------------------------------------------------------
# The period
# ---------------------------------------------------------------------------
FY_START = date(2025, 4, 1)          # company's books begin here
PERIOD_END = date(2026, 8, 31)

MONTHS: list[tuple[int, int]] = (
    [(2025, m) for m in range(4, 13)] +
    [(2026, m) for m in range(1, 9)]
)                                     # Apr-25 … Aug-26 = 17 months

# Where the cash has to land on 31-Aug-2026, matching every other screen.
TARGET_CLOSING_BANK = 41_700_000.0    # excludes the lien-marked FD
FD_BALANCE = 4_500_000.0

# ---------------------------------------------------------------------------
# The shape of the two years
#
# FY25-26 is the year after the Series A: hiring runs ahead of revenue, so burn
# widens through the middle of the year and only starts to close as collections
# catch up. FY26-27 is the company at its current scale. That curve is the
# whole reason for shipping two years — a flat ramp would compare to nothing.
#
#                     (revenue multiplier, cost multiplier), 1.00 = today
# ---------------------------------------------------------------------------
SHAPE: dict[tuple[int, int], tuple[float, float]] = {
    (2025, 4):  (0.38, 0.52),
    (2025, 5):  (0.42, 0.57),
    (2025, 6):  (0.45, 0.62),
    (2025, 7):  (0.50, 0.68),
    (2025, 8):  (0.54, 0.73),
    (2025, 9):  (0.58, 0.79),
    (2025, 10): (0.63, 0.84),
    (2025, 11): (0.66, 0.88),
    (2025, 12): (0.70, 0.91),
    (2026, 1):  (0.74, 0.94),
    (2026, 2):  (0.80, 0.96),
    (2026, 3):  (0.92, 0.97),      # year-end collection push
    (2026, 4):  (0.88, 0.96),
    (2026, 5):  (0.93, 0.98),
    (2026, 6):  (1.00, 1.00),      # from here the figures are identical to the
    (2026, 7):  (1.00, 1.00),      # worked-example workbook, so the two demo
    (2026, 8):  (1.00, 1.00),      # paths agree where they overlap
}

# Billed above collected, so receivables build to roughly the ₹ 4.8 Cr the rest
# of the demonstration quotes. Verified by `python tally_export.py --check`.
BILL_OVER_COLLECT = 1.03
SETTLE_LAG_MONTHS = 2                 # ≈ 60-day DSO
SETTLE_RATE = 0.99                    # the rest ages
EARLY_SETTLE_RATE = 0.55              # first two months, collected on delivery

CREDIT_TERMS = {
    "Bharat Metro Rail Corporation": 45,
    "Sterling Cement Ltd": 30,
    "Aurora Pharma Pvt Ltd": 30,
    "Vidyut Grid Solutions": 45,
    "Coastal Logistics Park": 30,
    "Nandi Infra Projects": 45,
    "Peninsula Ports Authority": 60,
}

# Customers who are not there for the whole period. A client that stops paying
# is what makes an ageing screen worth looking at.
FIRST_MONTH = {"Peninsula Ports Authority": (2026, 4)}
LAST_MONTH = {"Nandi Infra Projects": (2026, 2)}      # insolvency admitted Jul-26

CORE_CUSTOMERS = [name for name, _, _ in _MONTHLY_IN]
ALL_CUSTOMERS = CORE_CUSTOMERS + ["Nandi Infra Projects", "Peninsula Ports Authority"]

# Share of monthly billing, by customer.
_BASE_IN = {name: amt for name, amt, _ in _MONTHLY_IN}
_BASE_IN["Nandi Infra Projects"] = 1_400_000.0
_BASE_IN["Peninsula Ports Authority"] = 1_900_000.0

GST_RATE = 0.18
PF_LEDGER = "Provident Fund Payable"
TDS_LEDGER = "TDS Payable"
GST_LEDGER = "GST Payable"
PAYROLL_EXPENSE = "Salaries and Wages"

BANK = "HDFC Bank - Current 4471"
COLLECTIONS = "ICICI Bank - Collections 8802"
PAYROLL_BANK = "Axis Bank - Payroll 1156"
SALES_LEDGER = "Product and Service Income"

# Which expense ledger each recurring payment hits, and from which bank.
EXPENSE_LEDGER: dict[str, tuple[str, str]] = {
    "Payroll": ("Salaries and Wages", PAYROLL_BANK),
    "Provident fund and ESI": ("Provident Fund Payable", PAYROLL_BANK),
    "AWS India": ("Cloud Hosting - AWS", BANK),
    "Atlassian / Figma / GitHub": ("Software Subscriptions", BANK),
    "Embedded components": ("Components and Sensors", BANK),
    "Site commissioning contractors": ("Site Commissioning Charges", BANK),
    "Office rent": ("Office Rent", BANK),
    "Electricity and facilities": ("Electricity and Utilities", BANK),
    "Digital campaigns": ("Marketing and Advertising", BANK),
    "Statutory audit and CS retainer": ("Legal and Professional Fees", BANK),
    "Term loan interest": ("Interest on Term Loan", BANK),
    "Insurance, travel and sundries": ("Insurance", BANK),
    "GST payment": ("GST Payable", BANK),
    "TDS payment": ("TDS Payable", BANK),
}

# One-off items, excluded from normalised burn. Two in the prior year so the
# year-on-year comparison is not distorted by one side having none.
ONE_OFFS: list[tuple[date, str, str, str, float, str]] = [
    (date(2025, 4, 22), "Payment", "Kanoria and Associates",
     "Legal and Professional Fees", 2_150_000,
     "Series A completion — legal, diligence and filing fees. One-off."),
    (date(2025, 9, 16), "Payment", "Prestige Office Ventures",
     "Office Rent", 3_400_000,
     "Whitefield office fit-out and deposit. Capital in nature, one-off."),
    (date(2026, 1, 28), "Receipt", "Karnataka State - MSME incentive",
     "Other Income", 1_250_000,
     "Capital incentive under the state electronics policy. One-off."),
    (date(2026, 6, 18), "Payment", "Kanoria and Associates",
     "Legal and Professional Fees", 1_450_000,
     "Series B diligence — legal and financial vendor due diligence. One-off."),
    (date(2026, 7, 9), "Payment", "Sensedge Instruments",
     "Components and Sensors", 2_100_000,
     "Bulk sensor purchase ahead of a price revision. One-off, not a run-rate."),
]


# ---------------------------------------------------------------------------
# Voucher model — source-system agnostic, so the XML writer and the mock
# endpoint render the same objects rather than each inventing their own.
# ---------------------------------------------------------------------------
@dataclass
class Line:
    ledger: str
    amount: float                     # +ve debit, -ve credit (Tally's sign is
                                      # applied at render time)


@dataclass
class Voucher:
    vtype: str                        # Receipt | Payment | Sales
    number: str
    when: date
    narration: str
    party: str
    lines: list[Line]
    # Bill-wise references, for ledgers with bill-by-bill tracking on.
    bills: list[tuple[str, str, float]] = field(default_factory=list)
    # (ref name, "New Ref" | "Agst Ref", amount)
    due_date: date | None = None


def _day(y: int, m: int, d: int) -> date:
    return date(y, m, min(d, 28))


def _month_index(y: int, m: int) -> int:
    return MONTHS.index((y, m))


def _active(customer: str, ym: tuple[int, int]) -> bool:
    first = FIRST_MONTH.get(customer)
    last = LAST_MONTH.get(customer)
    if first and ym < first:
        return False
    if last and ym > last:
        return False
    return True


# ---------------------------------------------------------------------------
def build() -> dict:
    """Every voucher, plus the opening balances that make it all balance."""
    vouchers: list[Voucher] = []
    seq: dict[str, int] = {"Sales": 0, "Receipt": 0, "Payment": 0, "Contra": 0}

    def number(kind: str) -> str:
        seq[kind] += 1
        return {"Sales": "SL", "Receipt": "RV", "Payment": "PV",
                "Contra": "CN"}[kind] + f"{seq[kind]:04d}"

    # -- sales ---------------------------------------------------------------
    # One invoice per customer per month, raised on the 25th.
    billed: dict[str, dict[tuple[int, int], float]] = {c: {} for c in ALL_CUSTOMERS}
    open_bills: dict[str, list[list]] = {c: [] for c in ALL_CUSTOMERS}
    invoice_meta: dict[str, tuple[str, date, date, float]] = {}

    for ym in MONTHS:
        y, m = ym
        r, _ = SHAPE[ym]
        for cust in ALL_CUSTOMERS:
            if not _active(cust, ym):
                continue
            amount = round(_BASE_IN[cust] * r * BILL_OVER_COLLECT, -2)
            if amount <= 0:
                continue
            when = _day(y, m, 25)
            terms = CREDIT_TERMS[cust]
            due = when + timedelta(days=terms)
            ref = f"NW/{str(y)[2:]}-{str(y + 1)[2:]}/{m:02d}{ALL_CUSTOMERS.index(cust) + 1:02d}"
            billed[cust][ym] = amount
            open_bills[cust].append([ref, amount, when, due])
            invoice_meta[ref] = (cust, when, due, amount)
            # The invoice is raised gross. Splitting out output GST is what
            # keeps GST Payable on the credit side of the trial balance, and
            # it is the first thing a CA looks for.
            gst = round(amount * GST_RATE / (1 + GST_RATE), 2)
            vouchers.append(Voucher(
                "Sales", number("Sales"), when,
                f"Services and systems billed — {when:%b-%y}", cust,
                [Line(cust, amount), Line(SALES_LEDGER, -(amount - gst)),
                 Line(GST_LEDGER, -gst)],
                bills=[(ref, "New Ref", amount)], due_date=due))

    # -- receipts ------------------------------------------------------------
    # What was billed two months ago, mostly, settled oldest-first. The
    # shortfall is what ages into the receivables screen.
    for ym in MONTHS:
        y, m = ym
        i = _month_index(y, m)
        # The first two months have nothing billed two months ago, because the
        # books start here. Leaving them empty would show two months of
        # apparently catastrophic burn that never happened — an artefact of
        # where the file begins, not of how the company traded. Early-stage
        # work was largely collected on delivery, so those months settle
        # against their own invoices, partially.
        if i < SETTLE_LAG_MONTHS:
            src, rate = ym, EARLY_SETTLE_RATE
        else:
            src, rate = MONTHS[i - SETTLE_LAG_MONTHS], SETTLE_RATE
        for cust in ALL_CUSTOMERS:
            target = billed[cust].get(src, 0.0) * rate
            if target < 1000:
                continue
            # A client heading into insolvency stops paying before it is public.
            if cust == "Nandi Infra Projects" and ym >= (2026, 1):
                continue
            allocations: list[tuple[str, str, float]] = []
            remaining = target
            for bill in open_bills[cust]:
                if remaining <= 0:
                    break
                take = min(bill[1], remaining)
                if take <= 0:
                    continue
                allocations.append((bill[0], "Agst Ref", take))
                bill[1] -= take
                remaining -= take
            open_bills[cust] = [b for b in open_bills[cust] if b[1] > 0.5]
            paid = target - remaining
            if paid < 1000:
                continue
            when = _day(y, m, 6 + ALL_CUSTOMERS.index(cust) * 5)
            vouchers.append(Voucher(
                "Receipt", number("Receipt"), when,
                f"Collection against invoices — {when:%b-%y}", cust,
                [Line(COLLECTIONS, paid), Line(cust, -paid)],
                bills=allocations))

    # -- payments ------------------------------------------------------------
    # Payroll is not a simple payment. Gross salary cost is what is charged to
    # the P&L; the bank pays the net, and PF and TDS are withheld and settled
    # separately in the same month. Recording it as one net payment would leave
    # both payables sitting in debit — which is exactly the sort of thing that
    # makes a demonstration fall apart when someone opens the trial balance.
    scaled = {}
    for ym in MONTHS:
        _, c = SHAPE[ym]
        scaled[ym] = {name.split(" — ")[0]: round(base * c, -2)
                      for name, _cat, _nature, base, _d in _MONTHLY_OUT}

    for ym in MONTHS:
        y, m = ym
        _, c = SHAPE[ym]
        amounts = scaled[ym]
        net_pay = amounts["Payroll"]
        pf = amounts["Provident fund and ESI"]
        tds = amounts["TDS payment"]

        vouchers.append(Voucher(
            "Payment", number("Payment"), _day(y, m, 1),
            f"Payroll — {date(y, m, 1):%b-%y}. Net paid; PF and TDS withheld.",
            PAYROLL_EXPENSE,
            [Line(PAYROLL_EXPENSE, net_pay + pf + tds),
             Line(PAYROLL_BANK, -net_pay),
             Line(PF_LEDGER, -pf), Line(TDS_LEDGER, -tds)]))

        for name, _cat, _nature, base, dom in _MONTHLY_OUT:
            label = name.split(" — ")[0]
            if label == "Payroll":
                continue                      # already posted, above
            ledger, bank = EXPENSE_LEDGER[label]
            amount = amounts[label]
            if amount <= 0:
                continue
            when = _day(y, m, dom)
            vouchers.append(Voucher(
                "Payment", number("Payment"), when,
                f"{label} — {when:%b-%y}", ledger,
                [Line(ledger, amount), Line(bank, -amount)]))

    # -- transfers between the company's own accounts -------------------------
    # Receipts land in the collections account and payroll goes out of the
    # payroll account. Without the sweeps a company actually runs, two of the
    # three accounts finish deeply overdrawn — which is not a rounding problem,
    # it is a missing business process.
    receipts_by_month: dict[tuple[int, int], float] = {}
    for v in vouchers:
        if v.vtype == "Receipt":
            key = (v.when.year, v.when.month)
            receipts_by_month[key] = receipts_by_month.get(key, 0.0) + sum(
                l.amount for l in v.lines if l.ledger == COLLECTIONS)

    for i, ym in enumerate(MONTHS):
        y, m = ym
        amounts = scaled[ym]

        # Sweep the month's collections into the operating account at month end,
        # which is what a treasury actually does — leaving the collections
        # account holding only its float.
        swept = round(receipts_by_month.get(ym, 0.0), -2)
        if swept > 1000:
            vouchers.append(Voucher(
                "Contra", number("Contra"), _day(y, m, 28),
                f"Month-end sweep of collections to the operating account "
                f"— {date(y, m, 1):%b-%y}", COLLECTIONS,
                [Line(BANK, swept), Line(COLLECTIONS, -swept)]))

        # Fund the payroll account for the month.
        need = round(amounts["Payroll"] + amounts["Provident fund and ESI"], -2)
        vouchers.append(Voucher(
            "Contra", number("Contra"), _day(y, m, 1),
            f"Funding the payroll account — {date(y, m, 1):%b-%y}", BANK,
            [Line(PAYROLL_BANK, need), Line(BANK, -need)]))

    # -- one-offs ------------------------------------------------------------
    for when, kind, party, ledger, amount, note in ONE_OFFS:
        if kind == "Payment":
            vouchers.append(Voucher("Payment", number("Payment"), when, note, ledger,
                                    [Line(ledger, amount), Line(BANK, -amount)]))
        else:
            vouchers.append(Voucher("Receipt", number("Receipt"), when, note, party,
                                    [Line(COLLECTIONS, amount), Line(ledger, -amount)]))

    vouchers.sort(key=lambda v: (v.when, v.vtype, v.number))

    # -- back-solve the opening bank position --------------------------------
    # Cash moved is known; the closing position is fixed by the rest of the
    # demonstration; so the opening balance is not a choice.
    bank_ledgers = {BANK, COLLECTIONS, PAYROLL_BANK}
    net_movement = sum(l.amount for v in vouchers for l in v.lines
                       if l.ledger in bank_ledgers)
    opening_bank = TARGET_CLOSING_BANK - net_movement

    # Split across the three accounts in the proportions the demo shows, then
    # correct the largest so the total is exact rather than nearly right.
    # Nearly all of it sits in the operating account; the other two are
    # funded from it as the month runs.
    split = {BANK: 0.92, COLLECTIONS: 0.04, PAYROLL_BANK: 0.04}
    openings = {k: round(opening_bank * s, -2) for k, s in split.items()}
    openings[BANK] += opening_bank - sum(openings.values())

    receivable_open = sum(b[1] for c in ALL_CUSTOMERS for b in open_bills[c])

    return {
        "vouchers": vouchers,
        "opening_bank": openings,
        "opening_bank_total": opening_bank,
        "closing_bank_total": opening_bank + net_movement,
        "receivables_at_end": receivable_open,
        "open_bills": {c: [b for b in open_bills[c]] for c in ALL_CUSTOMERS},
        "invoice_meta": invoice_meta,
        "net_movement": net_movement,
    }


# ---------------------------------------------------------------------------
def summary(model: dict | None = None) -> dict:
    """Year-on-year figures, for checking the shape is worth demonstrating."""
    model = model or build()
    years = {"FY25-26": (date(2025, 4, 1), date(2026, 3, 31)),
             "FY26-27 (to Aug)": (date(2026, 4, 1), date(2026, 8, 31))}
    bank_ledgers = {BANK, COLLECTIONS, PAYROLL_BANK}
    out = {}
    for label, (a, b) in years.items():
        # Transfers between the company's own accounts are not collections and
        # not spend. Counting them would treble the reported inflow.
        vs = [v for v in model["vouchers"]
              if a <= v.when <= b and v.vtype != "Contra"]
        inflow = sum(l.amount for v in vs for l in v.lines
                     if l.ledger in bank_ledgers and l.amount > 0)
        outflow = -sum(l.amount for v in vs for l in v.lines
                       if l.ledger in bank_ledgers and l.amount < 0)
        months = (b.year - a.year) * 12 + b.month - a.month + 1
        out[label] = {
            "months": months,
            "collections": inflow,
            "outflow": outflow,
            "net_burn": outflow - inflow,
            "net_burn_per_month": (outflow - inflow) / months,
            "collections_per_month": inflow / months,
        }
    return out
