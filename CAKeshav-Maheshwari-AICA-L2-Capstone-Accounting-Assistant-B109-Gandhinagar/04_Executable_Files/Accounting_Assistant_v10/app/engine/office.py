"""Office dashboard: every company on one screen, from local data only (fast; nothing is asked from Tally).

Due dates used (monthly filers): TDS deposit 7th of next month (March: 30 April); GSTR-1 11th; GSTR-3B 20th.
'Done' comes from the month-end close checklist ticks, so ticking there clears the dashboard."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db.models import BankLine, Company, Invoice, MasterCache
from .compliance import due_date


@dataclass
class Due:
    label: str
    due: str            # YYYYMMDD
    done: bool
    days_left: int

    @property
    def state(self) -> str:
        if self.done:
            return "ok"
        return "err" if self.days_left < 0 else "warn" if self.days_left <= 7 else "info"

    @property
    def short(self) -> str:
        if self.done:
            return "✓ done"
        if self.days_left < 0:
            return f"overdue {-self.days_left}d"
        return f"due {self.due[6:8]}-{self.due[4:6]} ({self.days_left}d)"

    @property
    def text(self) -> str:
        d = f"{self.due[6:8]}-{self.due[4:6]}"
        if self.done:
            return f"✓ {self.label}"
        if self.days_left < 0:
            return f"{self.label}: overdue {-self.days_left}d (due {d})"
        return f"{self.label}: due {d} ({self.days_left}d)"


@dataclass
class Row:
    company_id: str
    name: str
    invoices: int = 0
    bank: dict = field(default_factory=dict)            # bank ledger -> unposted lines
    last_sync: datetime | None = None
    check: dict = field(default_factory=dict)            # {"at", "err", "warn"} from Check company
    dues: list = field(default_factory=list)
    close_done: int = 0
    close_total: int = 0
    month: str = ""                                      # YYYYMM being closed (previous month)
    lock_until: str = ""
    attention: list = field(default_factory=list)       # besides the due dates (they have their own columns)
    urgent: int = 0                                      # due dates overdue / within a week

    @property
    def bank_total(self) -> int:
        return sum(self.bank.values())


def previous_month(today: date) -> str:
    first = today.replace(day=1) - timedelta(days=1)
    return f"{first.year}{first.month:02d}"


def _gst_due(month: str, day: int) -> str:
    y, m = int(month[:4]), int(month[4:6])
    ny, nm = (y + (m == 12), m % 12 + 1)
    return f"{ny}{nm:02d}{day:02d}"


def build(session: Session, today: date | None = None, companies: list[Company] | None = None) -> list[Row]:
    today = today or date.today()
    month = previous_month(today)
    companies = companies if companies is not None else list(session.scalars(select(Company).order_by(Company.name)))
    inv = dict(session.execute(select(Invoice.company_id, func.count()).where(
        Invoice.status.not_in(["posted", "exception"])).group_by(Invoice.company_id)).all())
    bank: dict = {}
    for cid, bl, n in session.execute(select(BankLine.company_id, BankLine.bank_ledger, func.count()).where(
            BankLine.status == "new").group_by(BankLine.company_id, BankLine.bank_ledger)):
        bank.setdefault(cid, {})[bl] = n
    sync = dict(session.execute(select(MasterCache.company_id, func.max(MasterCache.synced_at))
                                .group_by(MasterCache.company_id)).all())
    rows = []
    for c in companies:
        s = c.settings or {}
        r = Row(c.id, c.name, inv.get(c.id, 0), bank.get(c.id, {}), sync.get(c.id), dict(s.get("last_check", {})),
                month=month, lock_until=s.get("lock_until", ""))
        ticks = s.get("close", {}).get(month, {})
        done = lambda k: bool(ticks.get(k, {}).get("done"))
        days = lambda d: (date(int(d[:4]), int(d[4:6]), int(d[6:8])) - today).days
        for label, due, key in (("TDS", due_date(month), "tds"), ("GSTR-1", _gst_due(month, 11), "gst_returns"),
                                ("GSTR-3B", _gst_due(month, 20), "gst_returns")):
            r.dues.append(Due(label, due, done(key), days(due)))
        from .compliance import CLOSE_ITEMS
        r.close_total = len(CLOSE_ITEMS)
        r.close_done = sum(1 for k, _l in CLOSE_ITEMS if done(k))
        # what needs attention, most urgent first
        r.urgent = sum(1 for d in r.dues if d.state in ("err", "warn"))
        if r.check.get("err"):
            r.attention.append(f"Check company: {r.check['err']} problem(s)")
        if r.last_sync is None:
            r.attention.append("Never synced")
        elif (datetime.now(timezone.utc).replace(tzinfo=None) - r.last_sync).days >= 3:
            r.attention.append(f"Last sync {(datetime.now(timezone.utc).replace(tzinfo=None) - r.last_sync).days} days ago")
        if r.invoices:
            r.attention.append(f"{r.invoices} invoice(s) waiting")
        if r.bank_total:
            r.attention.append(f"{r.bank_total} bank line(s) to post")
        rows.append(r)
    rows.sort(key=lambda r: (-(len(r.attention) + r.urgent), r.name.lower()))
    return rows


def to_excel(rows: list[Row], path) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    ws = wb.active
    ws.title = "Office"
    hdr = ["Company", "Invoices waiting", "Bank lines to post", "Last sync", "Check company", "TDS", "GSTR-1",
           "GSTR-3B", "Close checklist", "Locked up to", "Needs attention"]
    ws.append(hdr)
    for c in ws[1]:
        c.font = Font(bold=True)
    for r in rows:
        ws.append([r.name, r.invoices, r.bank_total, r.last_sync.strftime("%d-%m-%Y %H:%M") if r.last_sync else "",
                   (f"{r.check.get('err', 0)} problem(s), {r.check.get('warn', 0)} warning(s) on {r.check.get('at', '')}"
                    if r.check else "not run")] + [d.text for d in r.dues] +
                  [f"{r.close_done}/{r.close_total}",
                   f"{r.lock_until[6:8]}-{r.lock_until[4:6]}-{r.lock_until[:4]}" if r.lock_until else "",
                   "; ".join([d.text for d in r.dues if d.state in ("err", "warn")] + r.attention)])
    for col, w in zip("ABCDEFGHIJK", (38, 10, 10, 17, 30, 26, 26, 26, 10, 12, 60)):
        ws.column_dimensions[col].width = w
    wb.save(path)
