"""One in-memory index of a company's synced Tally vouchers, built once and reused by every screen until the
history changes (sync / new postings). Scanning 10,000+ vouchers per invoice or per bank line was what made
pages slow; with the index each lookup is a dictionary hit."""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db.models import VoucherHistory

_CACHE: dict = {}


class HistoryIndex:
    def __init__(self, rows: list):
        self.vouchers = rows
        self.by_ref: dict[str, list] = defaultdict(list)          # normalised reference -> vouchers
        self.credited: dict[str, list] = defaultdict(list)        # ledger credited -> vouchers
        self.by_ledger: dict[str, list] = defaultdict(list)       # ledger -> vouchers
        from .gstr2b import norm_no
        for v in rows:
            if v.reference:
                self.by_ref[norm_no(v.reference)].append(v)
            seen = set()
            for e in v.entries or []:
                led = e["ledger"]
                if led not in seen:
                    self.by_ledger[led].append(v)
                    seen.add(led)
                if not e["dr"]:
                    self.credited[led].append(v)


_GEN: dict = {}


def stamp(session: Session, company_id: str) -> tuple:
    # generation: bumped on every sync / posting. count + max(id) alone can repeat after a full re-sync
    # (SQLite reuses row ids), which left screens showing the old history.
    return (_GEN.get(company_id, 0),) + tuple(session.execute(select(func.count(), func.max(VoucherHistory.id))
                                 .where(VoucherHistory.company_id == company_id)).one())


def index(session: Session, company_id: str) -> HistoryIndex:
    st = stamp(session, company_id)
    hit = _CACHE.get(company_id)
    if hit and hit[0] == st:
        return hit[1]
    from types import SimpleNamespace
    cols = (VoucherHistory.id, VoucherHistory.guid, VoucherHistory.masterid, VoucherHistory.date,
            VoucherHistory.voucher_type, VoucherHistory.number, VoucherHistory.party, VoucherHistory.reference,
            VoucherHistory.narration, VoucherHistory.entries, VoucherHistory.company_id)
    # plain copies, not ORM objects: safe across sessions and never re-loaded one by one
    rows = [SimpleNamespace(id=r[0], guid=r[1], masterid=r[2] or "", date=r[3], voucher_type=r[4], number=r[5],
                            party=r[6] or "", reference=r[7] or "", narration=r[8] or "", entries=r[9] or [],
                            company_id=r[10])
            for r in session.execute(select(*cols).where(VoucherHistory.company_id == company_id)
                                     .order_by(VoucherHistory.date))]
    idx = HistoryIndex(rows)
    _CACHE[company_id] = (st, idx)
    return idx


def vouchers(session: Session, company_id: str, frm: str = "", to: str = "") -> list:
    """The company's vouchers (oldest first), optionally within dates YYYYMMDD - served from the index."""
    import bisect
    rows = index(session, company_id).vouchers
    if not frm and not to:
        return rows
    dates = index(session, company_id).__dict__.setdefault("_dates", [v.date for v in rows])
    lo = bisect.bisect_left(dates, frm) if frm else 0
    hi = bisect.bisect_right(dates, to) if to else len(rows)
    return rows[lo:hi]


def invalidate(company_id: str | None = None) -> None:
    if company_id:
        _CACHE.pop(company_id, None)
        _GEN[company_id] = _GEN.get(company_id, 0) + 1
    else:
        _CACHE.clear()
        for k in list(_GEN):
            _GEN[k] += 1
