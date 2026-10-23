"""Generate a fictional Tally-style Day Book XML (FY 2025-26) with deliberately seeded issues.

Usage: python samples/make_sample.py
"""
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

V: list[tuple] = []  # (date, type, narration, [(ledger, amount, "Dr"/"Cr")])


def add(d, vtype, narr, *lines):
    V.append((d, vtype, narr, list(lines)))


# ---- routine activity -------------------------------------------------------------
add(date(2025, 4, 1), "Contra", "Cash withdrawn for office use", ("Cash", 200_000, "Dr"), ("HDFC Bank", 200_000, "Cr"))
for m in range(12):
    y, mo = (2025, 4 + m) if 4 + m <= 12 else (2026, 4 + m - 12)
    month = date(y, mo, 1).strftime("%B %Y")
    rent_tds = 5_000 if m != 6 else 0  # October: TDS missed (seeded)
    add(date(y, mo, 5), "Payment", f"Office rent for {month}", ("Office Rent", 50_000, "Dr"),
        *([("TDS Payable", rent_tds, "Cr")] if rent_tds else []), ("HDFC Bank", 50_000 - rent_tds, "Cr"))
    if m == 4:  # August sale: IGST and CGST charged together (seeded)
        add(date(y, mo, 10), "Sales", f"Sales invoice {month}", ("Alpha Industries", 127_000, "Dr"),
            ("Sales", 100_000, "Cr"), ("CGST", 9_000, "Cr"), ("IGST", 18_000, "Cr"))
    else:
        add(date(y, mo, 10), "Sales", f"Sales invoice {month}", ("Alpha Industries", 118_000, "Dr"),
            ("Sales", 100_000, "Cr"), ("CGST", 9_000, "Cr"), ("SGST", 9_000, "Cr"))
    add(date(y, mo, 20), "Receipt", f"Received from Alpha Industries for {month}", ("HDFC Bank", 118_000, "Dr"),
        ("Alpha Industries", 118_000, "Cr"))
    add(date(y, mo, 27), "Journal", f"Salary for {month}", ("Salaries", 148_750 + m * 125, "Dr"),
        ("Salary Payable", 148_750 + m * 125, "Cr"))
    for wk in (3, 12, 17, 24):
        add(date(y, mo, wk), "Payment", "Tea and refreshments", ("Staff Welfare", 1_200, "Dr"), ("Cash", 1_200, "Cr"))

# ---- seeded issues ----------------------------------------------------------------
add(date(2025, 6, 12), "Payment", "Payment for materials", ("Sharma Traders", 45_000, "Dr"), ("Cash", 45_000, "Cr"))
for _ in range(3):
    add(date(2025, 7, 14), "Payment", "Freight charges", ("Verma Transport", 9_500, "Dr"), ("Cash", 9_500, "Cr"))
add(date(2025, 7, 30), "Payment", "Loading charges", ("Kumar Loaders", 9_800, "Dr"), ("Cash", 9_800, "Cr"))
for d in (date(2025, 8, 22), date(2025, 8, 24)):
    add(d, "Payment", "Consultancy fees to Delta Consultants", ("Professional Fees", 80_000, "Dr"), ("HDFC Bank", 80_000, "Cr"))
add(date(2025, 9, 28), "Journal", "", ("Miscellaneous Expenses", 500_000, "Dr"), ("Suspense A/c", 500_000, "Cr"))
add(date(2025, 11, 3), "Payment", "Purchase of Dell laptop for director's personal use",
    ("Repairs & Maintenance", 85_000, "Dr"), ("HDFC Bank", 85_000, "Cr"))
add(date(2025, 12, 15), "Receipt", "Part payment received", ("Cash", 250_000, "Dr"), ("Gupta Enterprises", 250_000, "Cr"))
add(date(2026, 1, 18), "Payment", "Insurance premium", ("Insurance", 12_000, "Dr"), ("HDFC Bank", 11_000, "Cr"))
add(date(2026, 2, 10), "Payment", "Advance for raw material", ("Sharma Traders", 350_000, "Dr"), ("Cash", 350_000, "Cr"))
add(date(2026, 4, 5), "Payment", "Electricity charges", ("Electricity", 8_400, "Dr"), ("HDFC Bank", 8_400, "Cr"))


# ---- narration and amount-shape issues (kept apart so the financial statements built from V are unchanged) ----
EXTRA: list[tuple] = []


def add_extra(d, vtype, narr, *lines):
    EXTRA.append((d, vtype, narr, list(lines)))


add_extra(date(2025, 9, 5), "Payment", "Consultancy fee", ("Professional Fees", 49_999, "Dr"), ("HDFC Bank", 49_999, "Cr"))      # 999 and just under 50,000
add_extra(date(2025, 9, 15), "Payment", "Freight", ("Freight Outward", 9_999, "Dr"), ("Cash", 9_999, "Cr"))                    # just under the cash limit
add_extra(date(2025, 10, 5), "Payment", "Cleaning services", ("Shine Cleaners", 7_500, "Dr"), ("HDFC Bank", 7_500, "Cr"))      # three identical amounts
add_extra(date(2025, 10, 12), "Payment", "Cleaning services", ("Shine Cleaners", 7_500, "Dr"), ("HDFC Bank", 7_500, "Cr"))
add_extra(date(2025, 10, 19), "Payment", "Cleaning services", ("Shine Cleaners", 7_500, "Dr"), ("HDFC Bank", 7_500, "Cr"))
add_extra(date(2025, 11, 1), "Payment", "Diwali gifts to key customers", ("Business Promotion", 24_500, "Dr"), ("HDFC Bank", 24_500, "Cr"))
add_extra(date(2025, 11, 5), "Payment", "Penalty paid to GST department for late filing of GSTR-3B",
          ("Penalty and Fines", 12_300, "Dr"), ("HDFC Bank", 12_300, "Cr"))
add_extra(date(2025, 11, 25), "Payment", "Machinery spares", ("Repairs and Maintenance", 199_999, "Dr"), ("HDFC Bank", 199_999, "Cr"))
add_extra(date(2025, 12, 2), "Payment", "Donation to Shree Ram Mandir Trust", ("Donations", 51_000, "Dr"), ("HDFC Bank", 51_000, "Cr"))
add_extra(date(2025, 12, 18), "Payment", "No penalty was levied; interest paid on time", ("Interest Paid", 15_000, "Dr"), ("HDFC Bank", 15_000, "Cr"))  # must NOT flag
add_extra(date(2026, 1, 2), "Journal", "Entry passed as instructed by MD; bill to follow", ("Sundry Expenses", 75_000, "Dr"), ("Accrued Expenses", 75_000, "Cr"))
add_extra(date(2026, 1, 25), "Payment", "Director's family holiday to Goa", ("Staff Welfare", 60_000, "Dr"), ("HDFC Bank", 60_000, "Cr"))
add_extra(date(2026, 2, 2), "Payment", "Facilitation payment to municipal officer for approval, under the table",
          ("Sundry Expenses", 40_000, "Dr"), ("HDFC Bank", 40_000, "Cr"))
add_extra(date(2026, 2, 20), "Journal", "Misappropriation by cashier detected, amount written off", ("Loss by Fraud", 18_000, "Dr"), ("Staff Advances", 18_000, "Cr"))
add_extra(date(2026, 3, 10), "Journal", "Suspense balance cleared, unexplained difference in bank", ("Sundry Expenses", 22_000, "Dr"), ("Suspense A/c", 22_000, "Cr"))


def numbered(extra: bool = True):
    """(date, type, voucher number, narration, lines) in date order, numbered per type, with two payment numbers skipped."""
    vouchers = sorted(V + (EXTRA if extra else []), key=lambda t: t[0])
    counters: dict[str, int] = {}
    for d, vtype, narr, lines in vouchers:
        counters[vtype] = counters.get(vtype, 0) + 1
        if vtype == "Payment" and d >= date(2025, 10, 1) and counters.get("_gap") is None:
            counters["_gap"], counters[vtype] = 1, counters[vtype] + 2  # skip two numbers (seeded)
        yield d, vtype, counters[vtype], narr, lines


def build(extra: bool = True) -> str:
    out = ['<?xml version="1.0" encoding="UTF-8"?>', "<ENVELOPE><BODY><IMPORTDATA><REQUESTDATA>"]
    for d, vtype, no, narr, lines in numbered(extra):
        out.append(f'<TALLYMESSAGE><VOUCHER VCHTYPE="{vtype}" ACTION="Create">'
                   f"<DATE>{d:%Y%m%d}</DATE><VOUCHERTYPENAME>{vtype}</VOUCHERTYPENAME>"
                   f"<VOUCHERNUMBER>{no}</VOUCHERNUMBER><NARRATION>{escape(narr)}</NARRATION>")
        for ledger, amt, side in lines:
            signed = -amt if side == "Dr" else amt
            out.append(f"<ALLLEDGERENTRIES.LIST><LEDGERNAME>{escape(ledger)}</LEDGERNAME>"
                       f"<ISDEEMEDPOSITIVE>{'Yes' if side == 'Dr' else 'No'}</ISDEEMEDPOSITIVE>"
                       f"<AMOUNT>{signed:.2f}</AMOUNT></ALLLEDGERENTRIES.LIST>")
        out.append("</VOUCHER></TALLYMESSAGE>")
    out.append("</REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>")
    return "\n".join(out)


if __name__ == "__main__":
    path = Path(__file__).with_name("sample_daybook.xml")
    path.write_text(build(), encoding="utf-8")
    print(f"Wrote {path} with {len(V) + len(EXTRA)} vouchers")
