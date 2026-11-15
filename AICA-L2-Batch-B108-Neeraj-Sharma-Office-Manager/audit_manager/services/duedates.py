"""Due-date master. Standard statutory dates for the rest of FY 2026-27 are loaded once; the firm can add, edit or delete any of them.
Dates are the normal statutory dates. The Government sometimes extends them, so check and edit when a notification comes."""
from datetime import date

from ..models import DueDate, db

CATEGORIES = {"gst": "GST", "income_tax": "Income Tax", "tds": "TDS / TCS", "roc": "ROC / MCA", "labour": "PF / ESI", "other": "Other"}
_M = {11: "Nov 2026", 12: "Dec 2026", 1: "Jan 2027", 2: "Feb 2027", 3: "Mar 2027"}


def _prev(y, m):
    return (y - 1, 12) if m == 1 else (y, m - 1)


def standard_dates() -> list[tuple]:
    """(title, category, period, date, notes) from 15 Nov 2026 to 31 Mar 2027."""
    out = []
    names = {10: "Oct 2026", 11: "Nov 2026", 12: "Dec 2026", 1: "Jan 2027", 2: "Feb 2027"}
    for y, m in ((2026, 11), (2026, 12), (2027, 1), (2027, 2), (2027, 3)):
        py, pm = _prev(y, m)
        per = names[pm]
        monthly = [
            (7, "TDS / TCS deposit", "tds", ""),
            (10, "GSTR-7 / GSTR-8", "gst", "TDS deductors and e-commerce operators under GST"),
            (11, "GSTR-1 (monthly)", "gst", ""),
            (13, "GSTR-1 IFF (QRMP) / GSTR-5 / GSTR-6", "gst", "IFF is optional for QRMP taxpayers"),
            (15, "PF and ESI contribution", "labour", ""),
            (20, "GSTR-3B (monthly)", "gst", ""),
            (25, "PMT-06 GST payment (QRMP)", "gst", "For the first two months of a quarter"),
        ]
        for day, title, cat, note in monthly:
            if title.startswith("PMT-06") and pm in (12,):  # third month of a quarter is paid with the quarterly GSTR-3B
                continue
            if title.startswith("GSTR-1 IFF") and pm == 12:
                continue
            out.append((title, cat, per, date(y, m, day), note))
    out += [
        ("MGT-7 / MGT-7A annual return (ROC)", "roc", "FY 2025-26", date(2026, 11, 29), "60 days from the AGM; 29 Nov if the AGM was on 30 Sep"),
        ("Income tax return - transfer pricing cases", "income_tax", "AY 2026-27", date(2026, 11, 30), ""),
        ("Advance tax - 3rd instalment (75%)", "income_tax", "FY 2026-27", date(2026, 12, 15), ""),
        ("GSTR-9 / GSTR-9C annual return", "gst", "FY 2025-26", date(2026, 12, 31), ""),
        ("Belated income tax return", "income_tax", "AY 2026-27", date(2026, 12, 31), ""),
        ("GSTR-1 (quarterly, QRMP)", "gst", "Oct-Dec 2026", date(2027, 1, 13), ""),
        ("TCS return (quarterly)", "tds", "Oct-Dec 2026", date(2027, 1, 15), ""),
        ("CMP-08 (composition)", "gst", "Oct-Dec 2026", date(2027, 1, 18), ""),
        ("GSTR-3B (quarterly, QRMP)", "gst", "Oct-Dec 2026", date(2027, 1, 22), "22nd or 24th depending on the State; check yours and edit"),
        ("TDS return (quarterly)", "tds", "Oct-Dec 2026", date(2027, 1, 31), ""),
        ("TDS certificates (Form 16A)", "tds", "Oct-Dec 2026", date(2027, 2, 15), ""),
        ("Advance tax - final instalment (100%)", "income_tax", "FY 2026-27", date(2027, 3, 15), ""),
        ("Revised income tax return", "income_tax", "AY 2026-27", date(2027, 3, 31), ""),
        ("Financial year end - close books, tax-saving investments", "other", "FY 2026-27", date(2027, 3, 31), ""),
    ]
    return sorted((r for r in out if r[3] >= date(2026, 11, 15)), key=lambda r: r[3])


def load_standard() -> int:
    """Add any standard date that is not already there (same title, period and date). Returns how many were added."""
    have = {(d.title, d.period or "", d.original_date or d.due_date) for d in DueDate.query.all()}
    added = 0
    for title, cat, period, due, note in standard_dates():
        if (title, period, due) not in have:
            db.session.add(DueDate(title=title, category=cat, period=period, due_date=due, notes=note or None))
            added += 1
    return added


def seed_due_dates() -> None:
    if DueDate.query.count() == 0:
        load_standard()


def options(today: date | None = None) -> list[dict]:
    """For the message screen: upcoming dates first (the last week's dates are kept in case a reminder is still wanted)."""
    from datetime import timedelta

    today = today or date.today()
    rows = DueDate.query.filter(DueDate.due_date >= today - timedelta(days=7)).order_by(DueDate.due_date, DueDate.title).limit(200).all()
    return [{"label": f"{d.due_date:%d-%b-%Y} - {d.title}" + (f" ({d.period})" if d.period else "") + (" - date passed" if d.due_date < today else ""),
             "work": d.title, "period": d.period or "", "due_date": f"{d.due_date:%d-%b-%Y}"} for d in rows]
