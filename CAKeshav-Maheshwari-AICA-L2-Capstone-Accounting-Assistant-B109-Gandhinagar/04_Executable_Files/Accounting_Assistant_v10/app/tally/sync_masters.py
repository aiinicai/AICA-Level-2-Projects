"""Pull masters + voucher history for one company into the local cache.

Also registers / updates the company row (keyed by Tally GUID) and flags mapping
rules whose target ledger or stock item no longer exists in Tally.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from collections import Counter
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import app_dir
from ..gst_states import state_code
from ..db.models import AuditLog, Company, MappingRule, MasterCache, VoucherHistory, utcnow
from .client import TallyClient

MASTER_KINDS = ["group", "ledger", "stock_item", "unit", "godown", "voucher_type"]


@dataclass
class SyncReport:
    company_id: str = ""
    counts: dict = field(default_factory=dict)
    vouchers: int = 0
    vouchers_by_type: dict = field(default_factory=dict)
    vouchers_by_month: dict = field(default_factory=dict)
    skipped: int = 0
    first_last: tuple = ("", "")
    period: tuple = ("", "")
    gstin: str = ""
    gstin_note: str = ""
    orphaned_rules: list = field(default_factory=list)


def _months_back(d: date, months: int) -> date:
    """Same calendar day, N months earlier (e.g. 27-10-26 -> 27-10-25)."""
    y, m = d.year, d.month - months
    while m <= 0:
        m += 12
        y -= 1
    for day in (d.day, 30, 29, 28):
        try:
            return date(y, m, day)
        except ValueError:
            continue
    raise ValueError(d)


def _dump_diagnostics(company: str, raws: dict[str, bytes]) -> None:
    """Raw XML kept on this PC only (never uploaded) to troubleshoot field names."""
    try:
        d = app_dir() / "diagnostics"
        d.mkdir(exist_ok=True)
        safe = "".join(ch if ch.isalnum() else "_" for ch in company)[:60]
        for label, raw in raws.items():
            (d / f"{safe}_{label}.xml").write_bytes(raw)
    except OSError:
        pass


def _gst_probe_file():
    from ..config import app_dir
    return app_dir() / "gst_probe_skip.json"


def _gst_probe_skips() -> set:
    import json
    try:
        return set(json.loads(_gst_probe_file().read_text()))
    except (OSError, ValueError):
        return set()


def _gst_probe_mark(name: str, on: bool) -> None:
    import json
    s = _gst_probe_skips()
    (s.add if on else s.discard)(name)
    try:
        _gst_probe_file().write_text(json.dumps(sorted(s)))
    except OSError:
        pass


def upsert_company(session: Session, info: dict, host: str, port: int, default_style: str = "") -> Company:
    comp = session.scalar(select(Company).where(Company.tally_guid == info["guid"]))
    if comp is None:
        comp = Company(tally_guid=info["guid"], name=info["name"], tally_host=host, tally_port=port,
                       voucher_style=default_style or "purchase_accounting")
        session.add(comp)
    comp.name = info["name"]
    comp.gstin = info.get("gstin") or comp.gstin
    comp.state = info.get("state") or comp.state
    comp.tally_host, comp.tally_port = host, port
    session.commit()
    return comp


def sync_company(session: Session, client: TallyClient, info: dict, history_months: int = 12,
                 today: date | None = None, progress=lambda msg: None, default_style: str = "",
                 start: date | None = None, end: date | None = None) -> SyncReport:
    """start/end: voucher history period chosen with the period picker (default: last `history_months`)."""
    info = dict(info)
    gst_note = ""
    skip = _gst_probe_skips()
    if not info.get("gstin") and info["name"] in skip:
        gst_note = "GSTIN not read from Tally (that step upset Tally last time) - set it in Setup > Company."
    elif not info.get("gstin"):
        _gst_probe_mark(info["name"], True)          # stays marked if Tally falls over during the probe
        found, raws = client.company_gstins(info["name"], state_code(info.get("state", "")))
        _gst_probe_mark(info["name"], False)
        _dump_diagnostics(info["name"], raws)
        if found:
            info["gstin"] = found[0]
            if len(found) > 1:
                gst_note = f"{len(found)} GST registrations found; using {found[0]} (matches company state)"
        else:
            gst_note = "No GSTIN found in Tally. Check F11 > GST, or set it in company settings."
    comp = upsert_company(session, info, client.host, client.port, default_style)
    rep = SyncReport(company_id=comp.id, gstin=comp.gstin, gstin_note=gst_note)
    now = utcnow()

    for kind in MASTER_KINDS:
        progress(f"Fetching {kind.replace('_', ' ')}s")
        rows = client.masters(kind, comp.name)
        session.execute(delete(MasterCache).where(MasterCache.company_id == comp.id, MasterCache.kind == kind))
        session.add_all(MasterCache(company_id=comp.id, kind=kind, guid=r["guid"], name=r["name"],
                                    parent=r["parent"], data=r["data"], synced_at=now) for r in rows)
        rep.counts[kind] = len(rows)
    session.commit()

    today = today or date.today()
    start = start or _months_back(today, history_months)
    # always pull right up to today and at least the whole current FY: a period picker left on an old
    # period used to make Sync skip everything entered since then
    fy = date(today.year if today.month >= 4 else today.year - 1, 4, 1)
    start = min(start, fy)
    frm, to = start.strftime("%Y%m%d"), today.strftime("%Y%m%d")
    # all types: history feeds learning + reconciliation
    vchs = client.vouchers_range(comp.name, start, today, progress=progress)
    session.execute(delete(VoucherHistory).where(VoucherHistory.company_id == comp.id))
    session.add_all(VoucherHistory(company_id=comp.id, **v) for v in vchs if v["guid"])
    rep.vouchers = len(vchs)
    rep.skipped = getattr(client, "skipped", 0)
    rep.vouchers_by_type = dict(Counter(v["voucher_type"] or "(no type)" for v in vchs).most_common())
    rep.vouchers_by_month = dict(sorted(Counter(v["date"][:6] for v in vchs).items()))
    rep.first_last = (vchs[0]["date"], vchs[-1]["date"]) if vchs else ("", "")
    rep.period = (frm, to)
    session.commit()

    # rules pointing at masters that vanished -> deactivate + audit (never auto-replace)
    names = {(m.kind, m.name) for m in session.scalars(
        select(MasterCache).where(MasterCache.company_id == comp.id,
                                  MasterCache.kind.in_(["ledger", "stock_item"])))}
    for rule in session.scalars(select(MappingRule).where(MappingRule.company_id == comp.id,
                                                          MappingRule.active.is_(True))):
        kind = "ledger" if rule.target_kind == "ledger" else "stock_item"
        if (kind, rule.target_name) not in names:
            rule.active = False
            rep.orphaned_rules.append(rule.target_name)
            session.add(AuditLog(company_id=comp.id, action="rule_orphaned", entity="mapping_rules",
                                 entity_id=rule.id, before={"target": rule.target_name}))
    session.commit()
    from ..engine import history
    history.invalidate(comp.id)
    return rep
