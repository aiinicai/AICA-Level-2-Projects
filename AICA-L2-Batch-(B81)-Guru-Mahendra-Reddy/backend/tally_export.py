#!/usr/bin/env python
"""Write Tally-importable XML for the demonstration company.

    python tally_export.py            # writes to ../demo-tally/
    python tally_export.py --check    # trial balance only, writes nothing

Seventeen months — FY 2025-26 in full plus FY 2026-27 to 31-Aug-2026 — so the
tool has a prior year to compare against.

Three files, and the order matters:

  1. `Northwind_Masters.xml`   groups, ledgers, opening balances
  2. `Northwind_Vouchers.xml`  receipts, payments and transfers
  3. `Northwind_Sales.xml`     sales invoices, with bill-by-bill references

Masters first: a voucher naming a ledger Tally does not have is rejected, and
Tally reports that as an unhelpful "Could not set value" line. The sales file
is last and separate because bill-wise references are the fussiest part of
Tally's import — if that one fails, everything the cash screens need is
already in.

The data comes from `app/seed/tallydata.py`, which the mock endpoint also
serves, so the two ways of demonstrating the connector cannot drift apart.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.seed import tallydata as T           # noqa: E402
from app.seed.tallycheck import run as trial_balance   # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "demo-tally"
COMPANY = "Northwind Robotics Pvt Ltd"
FY_START = T.FY_START


# Tally's XML reader is not a conforming parser. Given no encoding declaration
# it reads bytes as ANSI, so a UTF-8 em-dash arrives as three stray characters
# in the middle of a narration — and a hand-rolled parser that loses its place
# there reports the failure against whatever tag it was expecting next. Every
# narration in this file carried one. They are transliterated, and the file now
# declares its encoding.
_ASCII = {
    "—": "-", "–": "-", "‘": "'", "’": "'",
    "“": '"', "”": '"', "₹": "Rs.", " ": " ",
    "…": "...",
}


def esc(s) -> str:
    if s is None:
        return ""
    s = str(s)
    for bad, good in _ASCII.items():
        s = s.replace(bad, good)
    # Anything still outside ASCII would be a new character someone added to a
    # narration; drop it rather than ship a file Tally may or may not read.
    s = s.encode("ascii", "replace").decode("ascii")
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def td(d: date) -> str:
    return d.strftime("%Y%m%d")


# ---------------------------------------------------------------------------
# Chart of accounts
# ---------------------------------------------------------------------------
# (ledger, Tally parent group). Opening balances come from the model, so they
# cannot be edited here into something that does not balance.
LEDGERS: list[tuple[str, str]] = [
    (T.BANK, "Bank Accounts"),
    (T.COLLECTIONS, "Bank Accounts"),
    (T.PAYROLL_BANK, "Bank Accounts"),
    ("Kotak Bank - Tax 6620", "Bank Accounts"),
    ("HDFC FD - BG Margin 9014", "Deposits (Asset)"),
    ("Petty Cash", "Cash-in-Hand"),

    *[(c, "Sundry Debtors") for c in T.ALL_CUSTOMERS],

    ("Sensedge Instruments", "Sundry Creditors"),
    ("Amazon Web Services India", "Sundry Creditors"),
    ("Prestige Office Ventures", "Sundry Creditors"),
    ("Kanoria and Associates", "Sundry Creditors"),
    ("Trilok Contracting", "Sundry Creditors"),
    ("Meridian Media", "Sundry Creditors"),
    ("Bharat Electric Utility", "Sundry Creditors"),
    ("Sundaram Insurance Brokers", "Sundry Creditors"),
    ("Talent Bridge Consulting", "Sundry Creditors"),

    ("GST Payable", "Duties & Taxes"),
    ("TDS Payable", "Duties & Taxes"),
    ("Provident Fund Payable", "Duties & Taxes"),
    ("ESI Payable", "Duties & Taxes"),
    ("Professional Tax Payable", "Duties & Taxes"),

    ("HDFC Term Loan", "Secured Loans"),
    ("Share Capital", "Capital Account"),
    ("Securities Premium", "Reserves & Surplus"),
    ("Accumulated Losses", "Reserves & Surplus"),

    ("Product and Service Income", "Sales Accounts"),
    ("Other Income", "Indirect Incomes"),

    ("Salaries and Wages", "Indirect Expenses"),
    ("Staff Welfare", "Indirect Expenses"),
    ("Recruitment Fees", "Indirect Expenses"),
    ("Cloud Hosting - AWS", "Indirect Expenses"),
    ("Software Subscriptions", "Indirect Expenses"),
    ("Components and Sensors", "Direct Expenses"),
    ("Site Commissioning Charges", "Direct Expenses"),
    ("Office Rent", "Indirect Expenses"),
    ("Electricity and Utilities", "Indirect Expenses"),
    ("Marketing and Advertising", "Indirect Expenses"),
    ("Legal and Professional Fees", "Indirect Expenses"),
    ("Interest on Term Loan", "Indirect Expenses"),
    ("Bank Charges", "Indirect Expenses"),
    ("Insurance", "Indirect Expenses"),
    ("Travel and Conveyance", "Indirect Expenses"),
    # Two deliberately obscure ones. Every real Tally company has a handful,
    # and the ledger-mapping screen exists precisely because the classifier
    # cannot be trusted to guess them.
    ("Misc Exp 2", "Indirect Expenses"),
    ("PROJ-B ADJ", "Indirect Expenses"),
]

BILLWISE_GROUPS = {"Sundry Debtors", "Sundry Creditors"}


def _envelope(report: str, body: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<ENVELOPE>\n'
        '<HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>\n'
        '<BODY><IMPORTDATA>\n'
        f'<REQUESTDESC><REPORTNAME>{report}</REPORTNAME>\n'
        f'<STATICVARIABLES><SVCURRENTCOMPANY>{esc(COMPANY)}</SVCURRENTCOMPANY>'
        '</STATICVARIABLES></REQUESTDESC>\n'
        '<REQUESTDATA>\n' + body + '\n</REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>\n'
    )


def masters_xml(opening: dict[str, float]) -> str:
    parts = []
    for name, parent in LEDGERS:
        bal = opening.get(name, 0.0)
        # In the model a positive balance is a debit. Tally wants the opposite
        # sign in OPENINGBALANCE, and ISDEEMEDPOSITIVE to say which side.
        deemed = "Yes" if bal >= 0 else "No"
        parts.append(
            f'<TALLYMESSAGE xmlns:UDF="TallyUDF">'
            f'<LEDGER NAME="{esc(name)}" ACTION="Create">'
            f'<NAME>{esc(name)}</NAME>'
            f'<PARENT>{esc(parent)}</PARENT>'
            f'<ISDEEMEDPOSITIVE>{deemed}</ISDEEMEDPOSITIVE>'
            f'<OPENINGBALANCE>{-bal:.2f}</OPENINGBALANCE>'
            f'<ISBILLWISEON>{"Yes" if parent in BILLWISE_GROUPS else "No"}</ISBILLWISEON>'
            f'</LEDGER></TALLYMESSAGE>')
    return _envelope("All Masters", "\n".join(parts))


# ---------------------------------------------------------------------------
# Vouchers
# ---------------------------------------------------------------------------
def _bill_allocations(v: T.Voucher, ledger: str) -> str:
    """Bill-by-bill references, on the party line only."""
    if not v.bills or ledger != v.party:
        return ""
    out = []
    for ref, kind, amount in v.bills:
        # Same sign rule as the ledger line it sits inside.
        signed = -amount if v.vtype == "Sales" else amount
        due = f"<BILLCREDITPERIOD>{(v.due_date - v.when).days} Days</BILLCREDITPERIOD>" \
            if (v.due_date and kind == "New Ref") else ""
        out.append(
            f'<BILLALLOCATIONS.LIST>'
            f'<NAME>{esc(ref)}</NAME>'
            f'<BILLTYPE>{kind}</BILLTYPE>{due}'
            f'<AMOUNT>{signed:.2f}</AMOUNT>'
            f'</BILLALLOCATIONS.LIST>')
    return "".join(out)


def voucher_xml(v: T.Voucher) -> str:
    lines = []
    for l in v.lines:
        # Tally: negative AMOUNT is a debit. The model stores a debit as
        # positive, so the sign flips on the way out.
        lines.append(
            f'<ALLLEDGERENTRIES.LIST>'
            f'<LEDGERNAME>{esc(l.ledger)}</LEDGERNAME>'
            f'<ISDEEMEDPOSITIVE>{"Yes" if l.amount > 0 else "No"}</ISDEEMEDPOSITIVE>'
            f'<AMOUNT>{-l.amount:.2f}</AMOUNT>'
            f'{_bill_allocations(v, l.ledger)}'
            f'</ALLLEDGERENTRIES.LIST>')
    # Tag order follows Tally's own export, which is the one order its importer
    # is certain to accept. Two things are deliberately absent:
    #
    #   EFFECTIVEDATE  — meaningful only when "Use effective dates for vouchers"
    #                    is switched on in F11. In a default company Tally reads
    #                    it, finds the feature off, and the voucher can end up
    #                    with no usable date at all. DATE alone is what a
    #                    straightforward cash voucher needs.
    #   PARTYLEDGERNAME on a Contra — a transfer between the company's own
    #                    accounts has no party. Naming a bank ledger there is
    #                    not what the field means.
    # …and the field is only written when the party is a ledger the voucher
    # actually posts to. The MSME incentive receipt carries a descriptive
    # counterparty the company has no ledger for; naming it here would point
    # Tally at an account that does not exist.
    party = ""
    if v.vtype != "Contra" and any(l.ledger == v.party for l in v.lines):
        party = f'<PARTYLEDGERNAME>{esc(v.party)}</PARTYLEDGERNAME>'
    return (
        f'<TALLYMESSAGE xmlns:UDF="TallyUDF">'
        f'<VOUCHER VCHTYPE="{esc(v.vtype)}" ACTION="Create" '
        f'OBJVIEW="Accounting Voucher View">'
        f'<DATE>{td(v.when)}</DATE>'
        f'<NARRATION>{esc(v.narration)}</NARRATION>'
        f'<VOUCHERTYPENAME>{esc(v.vtype)}</VOUCHERTYPENAME>'
        f'<VOUCHERNUMBER>{esc(v.number)}</VOUCHERNUMBER>'
        + party +
        f'<PERSISTEDVIEW>Accounting Voucher View</PERSISTEDVIEW>'
        + "".join(lines) +
        f'</VOUCHER></TALLYMESSAGE>')


def vouchers_xml(vouchers: list[T.Voucher]) -> str:
    return _envelope("Vouchers", "\n".join(voucher_xml(v) for v in vouchers))


# ---------------------------------------------------------------------------
def main() -> int:
    check = "--check" in sys.argv
    result = trial_balance(verbose=True)
    if not result["ok"]:
        print("  The books do not balance. Nothing written.\n")
        return 1
    if check:
        return 0

    model = result["model"]
    vouchers = model["vouchers"]
    cash = [v for v in vouchers if v.vtype in ("Receipt", "Payment", "Contra")]
    sales = [v for v in vouchers if v.vtype == "Sales"]

    # Split on the financial year. Tally imports into the company's *current
    # period*, and a freshly created company's period is one year wide — so a
    # single file spanning two years asks Tally to accept vouchers it is not
    # currently open for. Two files, imported either side of Alt+F2, removes
    # the guesswork: if year one lands clean and year two does not, the period
    # is the problem and nothing else is.
    FY_SPLIT = date(2026, 4, 1)
    y1 = [v for v in cash if v.when < FY_SPLIT]
    y2 = [v for v in cash if v.when >= FY_SPLIT]
    s1 = [v for v in sales if v.when < FY_SPLIT]
    s2 = [v for v in sales if v.when >= FY_SPLIT]

    OUT.mkdir(parents=True, exist_ok=True)
    files = [
        ("Northwind_Masters.xml", masters_xml(result["opening"]),
         f"{len(LEDGERS)} ledgers"),
        ("Northwind_Vouchers_FY2526.xml", vouchers_xml(y1),
         f"{len(y1)} vouchers, Apr-25 to Mar-26"),
        ("Northwind_Vouchers_FY2627.xml", vouchers_xml(y2),
         f"{len(y2)} vouchers, Apr-26 to Aug-26"),
        ("Northwind_Sales_FY2526.xml", vouchers_xml(s1),
         f"{len(s1)} invoices, Apr-25 to Mar-26"),
        ("Northwind_Sales_FY2627.xml", vouchers_xml(s2),
         f"{len(s2)} invoices, Apr-26 to Aug-26"),
    ]
    for name, xml, note in files:
        (OUT / name).write_text(xml, encoding="utf-8")

    print(f"  Written to {OUT}\n")
    for name, _xml, note in files:
        print(f"    {name:<26} {note}")

    print(f"""
  In Tally Prime
  --------------
    1. Create a company called '{COMPANY}',
       financial year beginning {FY_START:%d-%b-%Y}, books from the same date.
    2. Gateway of Tally > Import > Masters   -> Northwind_Masters.xml
    3. Gateway of Tally > Import > Vouchers  -> Northwind_Vouchers_FY2526.xml
    4. Gateway of Tally > Import > Vouchers  -> Northwind_Sales_FY2526.xml
    5. Alt+F2, change the period to 1-Apr-2026 to 31-Aug-2026.
       Tally imports into the period it is currently open for; year two
       will not go in until you do this.
    6. Import Northwind_Vouchers_FY2627.xml, then Northwind_Sales_FY2627.xml
    7. Alt+F2 again, 1-Apr-2025 to 31-Aug-2026, to see both years at once.
    8. F1 > Settings > Connectivity > Client/Server configuration:
       acts as Both, ODBC on, port 9000.

  Then in Cash Runway: Setup > Tally > Test connection.
  Full instructions, including what to do when it complains:
  docs/TALLY_IMPORT.md
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
