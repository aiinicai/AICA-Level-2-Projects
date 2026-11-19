"""Post approved vouchers to Tally one at a time, under the company lock, with audit."""
from __future__ import annotations

from decimal import Decimal

from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..db import locks
from ..db.models import AuditLog, Company, Invoice as InvoiceRow, Posting
from ..tally.client import TallyClient, TallyError
from ..tally import xml_requests as rq
from .voucher import Voucher, to_xml


@dataclass
class PostResult:
    ok: bool
    message: str
    tally_id: str = ""
    xml: str = ""
    locked: bool = False            # refused because of the company's period lock (needs a reason)


def dry_run(v: Voucher, known_ledgers: set[str], known_items: set[str]) -> tuple[list[str], str]:
    xml = to_xml(v)
    return v.problems(known_ledgers, known_items), xml


def post(session: Session, lock_session: Session, client: TallyClient, company: Company, v: Voucher,
         holder: str, invoice_row: InvoiceRow | None = None, known_ledgers: set[str] | None = None,
         known_items: set[str] | None = None, stale_seconds: int = 300, override_reason: str = "",
         extra_problems: list[str] | None = None, remote_id: str = "") -> PostResult:
    from .entry import PeriodLocked, check_lock
    problems = v.problems(known_ledgers, known_items) + list(extra_problems or [])
    if problems:
        return PostResult(False, "; ".join(problems))
    try:
        check_lock(session, company, v, override_reason, holder)
    except PeriodLocked as e:
        return PostResult(False, str(e), locked=True)
    problems = []
    if problems:
        return PostResult(False, "; ".join(problems))
    locks.acquire(lock_session, company.id, holder, stale_seconds)       # raises LockHeld
    import copy
    from . import numbering
    # REMOTEID makes a repeat post update the same voucher instead of creating a second one - important when
    # Tally crashed after saving but before replying. Every caller now passes one.
    remote = invoice_row.id if invoice_row else remote_id
    variants = dict((company.settings or {}).get("post_variants", {}))
    learned = variants.get(v.vtype, "")
    try:
        method = (_masters_for(session, company.id).voucher_types.get(v.vtype, {}) or {}).get("NUMBERINGMETHOD", "")
    except Exception:
        method = ""

    live_cache: list = []

    def live_numbers() -> list:
        if not live_cache:
            fy = int(v.date[:4]) if int(v.date[4:6]) >= 4 else int(v.date[:4]) - 1
            try:
                live_cache.append(client.voucher_numbers(company.name, v.vtype, f"{fy}0401", f"{fy + 1}0331"))
            except Exception:
                live_cache.append([])
        return live_cache[0]

    def variant(kind: str) -> Voucher:
        w = copy.deepcopy(v)
        if kind in ("number", "number+order") and not w.number:
            w.number = numbering.next_number(session, company.id, w.vtype, w.date, live_numbers())
        if kind in ("order", "number+order"):
            w.lines = [l for l in w.lines if not l.dr] + [l for l in w.lines if l.dr]   # credits first, like Tally
        return w
    first = learned or ("number" if numbering.needs_number(method) else "")
    ladder = [first] + [k for k in ("number", "order", "number+order") if k != first]
    tried, res, sent = [], None, v
    try:
        for kind in ladder:
            sent = variant(kind) if kind else v
            fragment = to_xml(sent, remote_id=remote)
            envelope = rq.import_vouchers_envelope(company.name, [fragment])
            res = client.import_vouchers(company.name, [fragment])
            tried.append(kind or "as is")
            created = (res["created"] >= 1 or (remote and res["altered"] >= 1)) and res["errors"] == 0 \
                and not res["exceptions"]
            if created or res["errors"] or res["line_errors"] or not res["exceptions"]:
                break                     # only a silent 'exception' is worth another try
        else:
            # still a silent refusal with a number: most often that number is taken (entered in Tally after the
            # last Sync). Try the next few numbers - safe, because REMOTEID makes a repeat update, not duplicate.
            if remote and sent.number:
                for _k in range(3):
                    sent = copy.deepcopy(sent)
                    sent.number = numbering.bump(sent.number)
                    fragment = to_xml(sent, remote_id=remote)
                    envelope = rq.import_vouchers_envelope(company.name, [fragment])
                    res = client.import_vouchers(company.name, [fragment])
                    tried.append(f"number {sent.number}")
                    if res["created"] or res["altered"] or res["errors"] or res["line_errors"] or \
                            not res["exceptions"]:
                        break
    except TallyError as e:
        session.add(Posting(company_id=company.id, invoice_id=invoice_row.id if invoice_row else None,
                            voucher_xml=envelope, response=str(e), ok=False, updated_by=holder))
        session.commit()
        return PostResult(False, str(e), xml=envelope)
    finally:
        locks.heartbeat(lock_session, company.id, holder)
    already = bool(remote) and res["altered"] >= 1 and not res["created"]
    ok = (res["created"] >= 1 or already) and res["errors"] == 0 and not res["exceptions"]
    win = "number+order" if tried[-1].startswith("number ") and "order" in tried else \
        ("number" if tried[-1].startswith("number ") else tried[-1])
    if ok and win != (learned or "as is") and win != "as is":
        variants[v.vtype] = win               # remember what this company's Tally accepts
        company.settings = {**(company.settings or {}), "post_variants": variants}
    v = sent
    if ok:
        msg = ("Was already in Tally - updated" if already else "Created in Tally") + \
            (f" (voucher id {res['last_vch_id']})" if res["last_vch_id"] else "") + \
            (f", No. {sent.number}" if sent.number else "")
    elif res["line_errors"] or res["errors"]:
        msg = "Tally rejected the voucher: " + ("; ".join(res["line_errors"]) or f"{res['errors']} error(s)")
    else:
        msg = ("Tally refused the voucher without giving a reason (import 'exception'), even after retrying with a "
               f"voucher number and with the entries in Tally's order. Enter one {v.vtype} by hand in Tally on "
               f"{v.date[6:8]}-{v.date[4:6]}-{v.date[:4]} with the same ledgers: the message Tally shows there is "
               "the cause (often a voucher-type setting, a period/security lock, or a ledger restriction).")
    session.add(Posting(company_id=company.id, invoice_id=invoice_row.id if invoice_row else None,
                        voucher_xml=envelope, response=str(res), tally_master_id=res["last_vch_id"] or "",
                        ok=ok, updated_by=holder))
    session.add(AuditLog(company_id=company.id, action="posted" if ok else "post_failed", entity="invoices",
                         entity_id=invoice_row.id if invoice_row else "",
                         after={"result": msg, "vtype": v.vtype, "date": v.date, "amount": str(v.dr_total)},
                         updated_by=holder))
    if invoice_row is not None and ok:
        invoice_row.status = "posted"
    if ok:
        record_history(session, company.id, v, res["last_vch_id"] or "")
    session.commit()
    return PostResult(ok, msg, res["last_vch_id"] or "", envelope)


def record_history(session: Session, company_id: str, v: Voucher, tally_id: str = "") -> None:
    """Add a just-posted voucher to the local copy of Tally's history, so duplicate checks, bank balance,
    party balances and red flags see it immediately (the next Sync replaces it with Tally's own copy)."""
    from collections import OrderedDict
    from ..db.models import VoucherHistory
    from . import history
    ents: "OrderedDict[tuple, Decimal]" = OrderedDict()
    for l in v.lines:
        ents[(l.ledger, l.dr)] = ents.get((l.ledger, l.dr), Decimal(0)) + l.amount
    for i in v.inventory:
        ents[(i.purchase_ledger, i.dr)] = ents.get((i.purchase_ledger, i.dr), Decimal(0)) + i.amount
    session.add(VoucherHistory(company_id=company_id, guid=f"app:{tally_id or id(v)}", masterid=tally_id,
                               date=v.date, voucher_type=v.vtype, number=v.number or "", party=v.party or "",
                               reference=v.reference or "", narration=v.narration or "",
                               entries=[{"ledger": k[0], "amount": str(a), "dr": k[1]} for k, a in ents.items()]))
    history.invalidate(company_id)


def _masters_for(session: Session, company_id: str):
    from . import masters as masters_mod
    return masters_mod.load(session, company_id)
