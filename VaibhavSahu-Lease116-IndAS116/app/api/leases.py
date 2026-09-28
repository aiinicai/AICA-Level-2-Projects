"""Lease APIs: master data, payments, events, calculation, schedules, workflow and lease-level exports."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..db.base import get_db
from ..db.models import (Approval, AuditLog, CalcRun, Company, Deposit, Document, Lease, LeaseAssessment, LeaseCost,
                         LeaseEventRow, LeaseOptionRow, PaymentScheduleRow, PeriodBalance, RestorationObligation, User)
from ..engine.calendar_utils import parse_date
from ..engine.decimal_utils import D, to_jsonable
from ..engine.lessee import EngineInputError
from ..services import audit
from ..services.export_service import (lease_memo_docx, lease_workpaper_xlsx, lessor_memo_docx, lessor_schedule_columns,
                                       lessor_workpaper_xlsx, table_csv, table_pdf, table_xlsx)
from ..services.extraction_service import save_document
from ..services.journal_service import lease_journals
from ..services.lease_service import (ServiceError, calculate, company_of, current_run, lease_dict, next_lease_code,
                                      preview_event, regenerate_payments, reporting_run)
from ..services.report_service import accessible_leases, is_current_lessor_run
from ..services.tax_service import tax_view
from ..services.workflow_service import is_locked, transition
from .deps import current_user, get_lease, require

router = APIRouter(prefix="/api/leases", tags=["leases"])

LEASE_FIELDS = {"description": str, "entity_id": int, "asset_class_id": int, "asset_description": str, "location": str,
                "business_unit": str, "cost_centre": str, "department": str, "project": str, "counterparty_id": int,
                "contract_number": str, "contract_date": date, "commencement_date": date, "availability_date": date,
                "contract_end": date, "enforceable_end": date, "enforceable_rationale": str, "currency": str,
                "payment_frequency": str, "payment_timing": str, "discount_rate_pct": Decimal, "rate_basis": str,
                "rate_source": str, "discount_rate_id": int, "useful_life_end": date, "ownership_transfers": bool,
                "non_lease_expedient": bool, "lease_type": str, "role": str, "head_lease_id": int, "notes": str,
                "generator_config": dict, "policy_overrides": dict, "opening_balance": dict, "lessor_details": dict,
                "slb_details": dict, "sublease_details": dict, "tax_settings": dict}


def _coerce(field: str, v):
    t = LEASE_FIELDS[field]
    if v in ("", None):
        return None
    if t is date:
        return parse_date(v)
    if t is Decimal:
        return D(v)
    if t is int:
        return int(v)
    if t is bool:
        return bool(v)
    return v


def _editable(lease: Lease):
    if lease.status not in ("Draft",):
        raise HTTPException(409, f"Lease is '{lease.status}'. After submission/approval, changes are made through Modifications "
                                 "or Reassessments, or by reopening the lease for correction (with reason).")


def _err(exc: ServiceError):
    raise HTTPException(exc.status, {"message": exc.message, "issues": exc.issues})


@router.get("")
def list_leases(search: str = "", entity_id: Optional[int] = None, status: str = "", asset_class: str = "", lease_type: str = "",
                role: str = "", page: int = 1, page_size: int = 50, sort: str = "lease_code", desc: bool = False,
                db: Session = Depends(get_db), user: User = Depends(require("lease.read"))):
    leases = accessible_leases(db, user, entity_id, include_archived=(status == "Archived"))
    rows = [lease_dict(db, l, full=False) for l in leases]
    if search:
        s = search.lower()
        rows = [r for r in rows if any(s in str(r.get(k) or "").lower() for k in
                                       ("lease_code", "description", "lessor", "location", "asset_class", "cost_centre", "contract_number"))]
    if status:
        rows = [r for r in rows if r["status"] == status]
    if asset_class:
        rows = [r for r in rows if r["asset_class"] == asset_class]
    if lease_type:
        rows = [r for r in rows if r["lease_type"] == lease_type]
    if role:
        rows = [r for r in rows if (r.get("role") or "LESSEE") == role.upper()]
    def key(r):
        v = r.get(sort)
        try:
            return (0, float(v)) if v not in (None, "") and sort in ("initial_liability", "liability_now", "rou_now",
                                                                     "discount_rate_pct", "net_investment_now",
                                                                     "accrued_income_now") else (0, str(v or ""))
        except Exception:
            return (0, str(v))
    rows.sort(key=key, reverse=desc)
    total = len(rows)
    start = (page - 1) * page_size
    return {"total": total, "page": page, "page_size": page_size, "rows": rows[start:start + page_size]}


@router.post("")
def create_lease(payload: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(require("lease.write"))):
    comp = company_of(db)
    lease = Lease(lease_code=payload.get("lease_code") or next_lease_code(db), company_id=comp.id, status="Draft",
                  created_by=user.id, currency=comp.functional_currency)
    if db.scalar(select(Lease.id).where(Lease.lease_code == lease.lease_code)):
        raise HTTPException(409, "Duplicate Lease ID")
    for f in LEASE_FIELDS:
        if f in payload:
            setattr(lease, f, _coerce(f, payload[f]))
    if not lease.entity_id:
        from ..db.models import Entity
        lease.entity_id = db.scalar(select(Entity.id).order_by(Entity.id))
    db.add(lease)
    db.flush()
    db.add(LeaseAssessment(lease_id=lease.id))
    audit.log(db, user, "CREATE", "Lease", lease.id, lease.lease_code, None, None, "Lease created")
    db.commit()
    return lease_dict(db, lease)


@router.get("/{lease_id}")
def get_one(lease_id: int, db: Session = Depends(get_db), user: User = Depends(require("lease.read"))):
    lease = get_lease(lease_id, db, user)
    d = lease_dict(db, lease)
    run = current_run(db, lease)
    d["stale"] = bool(run and lease.inputs_changed_at and run.created_at and lease.inputs_changed_at > run.created_at)
    d["runs"] = [{"id": r.id, "run_no": r.run_no, "version_no": r.version_no, "status": r.status, "is_current": r.is_current,
                  "created_at": r.created_at, "approved_at": r.approved_at, "inputs_hash": r.inputs_hash[:12]}
                 for r in db.scalars(select(CalcRun).where(CalcRun.lease_id == lease.id).order_by(CalcRun.run_no.desc())).all()]
    d["approvals"] = [{"action": a.action, "from": a.from_status, "to": a.to_status, "user_id": a.user_id, "comment": a.comment,
                       "at": a.created_at} for a in db.scalars(select(Approval).where(Approval.object_type == "Lease",
                                                                                     Approval.object_id == lease.id)
                                                                   .order_by(Approval.created_at.desc())).all()]
    d["documents"] = [{"id": x.id, "doc_type": x.doc_type, "filename": x.filename, "size": x.size, "uploaded_at": x.uploaded_at,
                       "event_id": x.event_id, "pages": x.pages} for x in db.scalars(select(Document).where(Document.lease_id == lease.id)).all()]
    return to_jsonable(d)


@router.patch("/{lease_id}")
def update_lease(lease_id: int, payload: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(require("lease.write"))):
    lease = get_lease(lease_id, db, user)
    _editable(lease)
    reason = payload.pop("_reason", None)
    changes = {f: _coerce(f, v) for f, v in payload.items() if f in LEASE_FIELDS}
    n = audit.log_changes(db, user, lease, changes, "Lease", lease.lease_code, reason)
    if n:
        lease.updated_at = lease.inputs_changed_at = datetime.now()
    db.commit()
    return lease_dict(db, lease)


# ---------------------------------------------------------------- options
@router.put("/{lease_id}/options")
def put_options(lease_id: int, payload: list = Body(...), db: Session = Depends(get_db), user: User = Depends(require("lease.write"))):
    lease = get_lease(lease_id, db, user)
    _editable(lease)
    old = [(o.kind, o.exercise_date, o.reasonably_certain) for o in lease.options]
    lease.options = []
    for o in payload:
        rc = o.get("reasonably_certain")
        lease.options.append(LeaseOptionRow(kind=o["kind"], holder=o.get("holder") or "LESSEE", exercise_date=parse_date(o.get("exercise_date")),
                                            extension_end_date=parse_date(o.get("extension_end_date")),
                                            price=D(o["price"]) if o.get("price") not in (None, "") else None,
                                            reasonably_certain=None if rc in (None, "") else bool(rc), rationale=o.get("rationale"),
                                            description=o.get("description"),
                                            renewal_escalation_pct=D(o["renewal_escalation_pct"]) if o.get("renewal_escalation_pct") not in (None, "") else None,
                                            approval_date=parse_date(o.get("approval_date")),
                                            last_reassessment_date=parse_date(o.get("last_reassessment_date"))))
    lease.updated_at = lease.inputs_changed_at = datetime.now()
    audit.log(db, user, "UPDATE", "Lease", lease.id, lease.lease_code, "options", old,
              [(o.kind, o.exercise_date, o.reasonably_certain) for o in lease.options], payload and "Options / judgments updated")
    if lease.generator_config:
        try:
            regenerate_payments(db, lease, user)
        except ServiceError:
            pass
    db.commit()
    return lease_dict(db, lease)


# ---------------------------------------------------------------- payments
@router.put("/{lease_id}/payment-terms")
def put_terms(lease_id: int, payload: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(require("lease.write"))):
    lease = get_lease(lease_id, db, user)
    _editable(lease)
    audit.log(db, user, "UPDATE", "Lease", lease.id, lease.lease_code, "generator_config", lease.generator_config, payload)
    lease.generator_config = payload
    if payload.get("frequency_months"):
        lease.payment_frequency = {1: "MONTHLY", 3: "QUARTERLY", 6: "HALF_YEARLY", 12: "ANNUAL"}.get(int(payload["frequency_months"]), "MONTHLY")
    if payload.get("timing"):
        lease.payment_timing = payload["timing"]
    try:
        n = regenerate_payments(db, lease, user)
    except ServiceError as exc:
        _err(exc)
    lease.updated_at = lease.inputs_changed_at = datetime.now()
    db.commit()
    return {"generated": n, "lease": lease_dict(db, lease)}


@router.put("/{lease_id}/payments")
def put_payments(lease_id: int, payload: list = Body(...), db: Session = Depends(get_db), user: User = Depends(require("lease.write"))):
    """Replace the payment schedule (irregular / edited schedules). Overrides of inclusion require a reason."""
    lease = get_lease(lease_id, db, user)
    _editable(lease)
    for p in payload:
        if p.get("include_override") is not None and p.get("include_override") != "" and not p.get("override_reason"):
            raise HTTPException(400, f"Line {p.get('line_no')}: an inclusion override requires a reason.")
        if not p.get("date"):
            raise HTTPException(400, "Every payment requires a valid date.")
    before = len(lease.payments)
    lease.payments = []
    for i, p in enumerate(sorted(payload, key=lambda x: (str(x.get("date")), x.get("line_no") or 0)), start=1):
        io = p.get("include_override")
        lease.payments.append(PaymentScheduleRow(line_no=i, payment_date=parse_date(p["date"]), period_start=parse_date(p.get("period_start")),
                                                 period_end=parse_date(p.get("period_end")), lease_amount=D(p.get("lease_amount") or 0),
                                                 non_lease_amount=D(p.get("non_lease_amount") or 0), category=p.get("category") or "FIXED",
                                                 include_override=None if io in (None, "") else bool(io),
                                                 override_reason=p.get("override_reason"), description=p.get("description"),
                                                 source=p.get("source") or "MANUAL"))
    lease.updated_at = lease.inputs_changed_at = datetime.now()
    audit.log(db, user, "UPDATE", "Lease", lease.id, lease.lease_code, "payments", f"{before} lines", f"{len(payload)} lines",
              "Payment schedule edited")
    db.commit()
    return lease_dict(db, lease)


@router.put("/{lease_id}/costs")
def put_costs(lease_id: int, payload: list = Body(...), db: Session = Depends(get_db), user: User = Depends(require("lease.write"))):
    lease = get_lease(lease_id, db, user)
    _editable(lease)
    old = [(c.kind, str(c.amount)) for c in lease.costs]
    lease.costs = [LeaseCost(kind=c["kind"], cost_date=parse_date(c.get("date")) or lease.commencement_date, amount=D(c["amount"]),
                             description=c.get("description")) for c in payload if c.get("amount") not in (None, "")]
    lease.updated_at = lease.inputs_changed_at = datetime.now()
    audit.log(db, user, "UPDATE", "Lease", lease.id, lease.lease_code, "costs", old, [(c.kind, str(c.amount)) for c in lease.costs])
    db.commit()
    return lease_dict(db, lease)


@router.put("/{lease_id}/deposit")
def put_deposit(lease_id: int, payload: Optional[dict] = Body(None), db: Session = Depends(get_db),
                user: User = Depends(require("lease.write"))):
    lease = get_lease(lease_id, db, user)
    _editable(lease)
    old = lease.deposits[0].amount if lease.deposits else None
    lease.deposits = []
    if payload and payload.get("amount") not in (None, ""):
        lease.deposits.append(Deposit(amount=D(payload["amount"]), payment_date=parse_date(payload.get("payment_date")) or lease.commencement_date,
                                      refund_date=parse_date(payload.get("refund_date")), interest_bearing=bool(payload.get("interest_bearing")),
                                      contractual_rate_pct=D(payload["contractual_rate_pct"]) if payload.get("contractual_rate_pct") else None,
                                      market_rate_pct=D(payload["market_rate_pct"]) if payload.get("market_rate_pct") not in (None, "") else None,
                                      treat_difference_as_prepaid_rent=payload.get("treat_difference_as_prepaid_rent", True) is not False,
                                      notes=payload.get("notes")))
    lease.updated_at = lease.inputs_changed_at = datetime.now()
    audit.log(db, user, "UPDATE", "Lease", lease.id, lease.lease_code, "deposit", old, payload and payload.get("amount"))
    db.commit()
    return lease_dict(db, lease)


@router.put("/{lease_id}/restoration")
def put_restoration(lease_id: int, payload: Optional[dict] = Body(None), db: Session = Depends(get_db),
                    user: User = Depends(require("lease.write"))):
    lease = get_lease(lease_id, db, user)
    _editable(lease)
    old = lease.restorations[0].estimated_cost if lease.restorations else None
    lease.restorations = []
    if payload and payload.get("estimated_cost") not in (None, ""):
        lease.restorations.append(RestorationObligation(estimated_cost=D(payload["estimated_cost"]),
                                                        settlement_date=parse_date(payload.get("settlement_date")),
                                                        discount_rate_pct=D(payload.get("discount_rate_pct") or 0),
                                                        recognition_date=parse_date(payload.get("recognition_date")),
                                                        cost_is_current_price=bool(payload.get("cost_is_current_price")),
                                                        inflation_pct=D(payload.get("inflation_pct") or 0), notes=payload.get("notes")))
    lease.updated_at = lease.inputs_changed_at = datetime.now()
    audit.log(db, user, "UPDATE", "Lease", lease.id, lease.lease_code, "restoration", old, payload and payload.get("estimated_cost"))
    db.commit()
    return lease_dict(db, lease)


@router.put("/{lease_id}/assessment")
def put_assessment(lease_id: int, payload: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(require("lease.write"))):
    lease = get_lease(lease_id, db, user)
    _editable(lease)
    a = db.scalar(select(LeaseAssessment).where(LeaseAssessment.lease_id == lease.id))
    if a is None:
        a = LeaseAssessment(lease_id=lease.id)
        db.add(a)
    ch = {}
    for k in ("identified_asset", "substitution_rights", "economic_benefits", "directs_use", "contains_lease", "separate_components",
              "allocation_method", "exemption", "benefits_on_own", "not_highly_dependent", "conclusion", "notes"):
        if k in payload:
            ch[k] = payload[k]
    if "asset_value_when_new" in payload:
        ch["asset_value_when_new"] = D(payload["asset_value_when_new"]) if payload["asset_value_when_new"] not in (None, "") else None
    audit.log_changes(db, user, a, ch, "LeaseAssessment", lease.lease_code)
    a.assessed_by = user.id
    a.assessed_at = datetime.now()
    if payload.get("exemption") in ("SHORT_TERM", "LOW_VALUE"):
        lease.lease_type = payload["exemption"]
    elif payload.get("exemption") == "NONE" and lease.lease_type in ("SHORT_TERM", "LOW_VALUE"):
        lease.lease_type = "STANDARD"
    lease.updated_at = lease.inputs_changed_at = datetime.now()
    db.commit()
    return lease_dict(db, lease)


# ---------------------------------------------------------------- calculation
@router.post("/{lease_id}/calculate")
def calc(lease_id: int, db: Session = Depends(get_db), user: User = Depends(require("lease.calculate"))):
    lease = get_lease(lease_id, db, user)
    if lease.status not in ("Draft",):
        raise HTTPException(409, f"Lease is '{lease.status}' — recalculation happens through events or after reopening.")
    try:
        summary, run = calculate(db, lease, user)
    except ServiceError as exc:
        db.rollback()
        _err(exc)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(400, {"message": str(exc), "issues": []})
    db.commit()
    return {"run_id": run.id, "run_no": run.run_no, "status": run.status, "summary": summary}


@router.get("/{lease_id}/result")
def result(lease_id: int, run_id: Optional[int] = None, db: Session = Depends(get_db), user: User = Depends(require("lease.read"))):
    lease = get_lease(lease_id, db, user)
    run = db.get(CalcRun, run_id) if run_id else current_run(db, lease)
    if run is None or run.lease_id != lease.id:
        return {"run": None, "summary": None}
    return to_jsonable({"run": {"id": run.id, "run_no": run.run_no, "version_no": run.version_no, "status": run.status,
                                "engine_version": run.engine_version, "inputs_hash": run.inputs_hash, "created_at": run.created_at,
                                "approved_at": run.approved_at}, "summary": run.summary})


@router.get("/{lease_id}/lessor-position")
def lessor_position(lease_id: int, as_of: Optional[str] = None, db: Session = Depends(get_db),
                    user: User = Depends(require("lease.read"))):
    """Lessor position at a reporting date: balances, maturity analysis (Ind AS 116.94 / 97) and reconciliation (para 94)."""
    from ..engine.lessor import position_at
    lease = get_lease(lease_id, db, user)
    run = current_run(db, lease)
    if run is None or run.summary.get("kind") not in ("LESSOR", "SUBLEASE"):
        return {"available": False}
    if not is_current_lessor_run(run.summary):
        return {"available": False, "reason": "Calculated with the previous lessor engine — recalculate."}
    return to_jsonable({"available": True, **position_at(run.summary, parse_date(as_of) or date.today())})


@router.get("/{lease_id}/runs/{run_id}/inputs")
def run_inputs(lease_id: int, run_id: int, db: Session = Depends(get_db), user: User = Depends(require("audit.read"))):
    lease = get_lease(lease_id, db, user)
    run = db.get(CalcRun, run_id)
    if run is None or run.lease_id != lease.id:
        raise HTTPException(404)
    return {"inputs": run.inputs, "inputs_hash": run.inputs_hash}


@router.get("/{lease_id}/explain")
def explain(lease_id: int, period_end: str, db: Session = Depends(get_db), user: User = Depends(require("lease.read"))):
    lease = get_lease(lease_id, db, user)
    run = current_run(db, lease)
    if run is None:
        raise HTTPException(404, "No calculation")
    pb = db.scalar(select(PeriodBalance).where(PeriodBalance.calc_run_id == run.id, PeriodBalance.period_end == parse_date(period_end)))
    row = next((r for r in run.summary.get("periods", []) if r["period_end"] == period_end), None)
    return to_jsonable({"row": row, "detail": (pb.data if pb else {}), "initial": run.summary.get("initial"),
                        "daycount": (run.summary.get("initial") or {}).get("daycount")})


# ---------------------------------------------------------------- events
def _event_from_payload(lease: Lease, p: dict, ev: LeaseEventRow | None = None) -> LeaseEventRow:
    ev = ev or LeaseEventRow(lease_id=lease.id)
    ev.event_type = p["event_type"]
    ev.subtype = p.get("subtype")
    ev.effective_date = parse_date(p["effective_date"])
    ev.description = p.get("description")
    ev.details = p.get("details") or {}
    return ev


@router.post("/{lease_id}/events/preview")
def event_preview(lease_id: int, payload: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(require("event.write"))):
    lease = get_lease(lease_id, db, user)
    ev = _event_from_payload(lease, payload)
    ev.status = "Preview"
    try:
        return preview_event(db, lease, ev)
    except ServiceError as exc:
        _err(exc)
    except EngineInputError as exc:
        raise HTTPException(400, {"message": "Invalid event inputs", "issues": to_jsonable(exc.issues)})
    finally:
        db.rollback()


@router.post("/{lease_id}/events")
def event_create(lease_id: int, payload: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(require("event.write"))):
    lease = get_lease(lease_id, db, user)
    if lease.status not in ("Approved", "Posted", "Modified", "Draft"):
        raise HTTPException(409, f"Events can be recorded on approved leases (current status '{lease.status}').")
    ev = _event_from_payload(lease, payload)
    if lease.commencement_date and ev.effective_date < lease.commencement_date:
        raise HTTPException(400, "Event date cannot precede the commencement date.")
    if is_locked(db, lease.company_id, ev.effective_date):
        raise HTTPException(409, "The effective date falls in a locked accounting period — reopen the period first.")
    ev.status = "Draft"
    ev.prepared_by = user.id
    lease.events.append(ev)
    db.flush()
    if payload.get("document_id"):
        d = db.get(Document, int(payload["document_id"]))
        if d:
            d.lease_id, d.event_id = lease.id, ev.id
    audit.log(db, user, "CREATE", "LeaseEvent", ev.id, lease.lease_code, "event", None,
              f"{ev.event_type} {ev.subtype or ''} effective {ev.effective_date}: {ev.description or ''}")
    # an event re-opens the lease for recalculation and approval (history of the approved run is preserved)
    prev_status = lease.status
    if lease.status in ("Approved", "Posted", "Modified"):
        lease.status = "Draft"
        audit.log(db, user, "EVENT_REOPEN", "Lease", lease.id, lease.lease_code, "status", prev_status, "Draft",
                  f"{ev.event_type} recorded — new calculation required; approved run retained as history")
    try:
        summary, run = calculate(db, lease, user)
    except (ServiceError, EngineInputError) as exc:
        db.rollback()
        if isinstance(exc, ServiceError):
            _err(exc)
        raise HTTPException(400, {"message": "Invalid event inputs", "issues": to_jsonable(exc.issues)})
    db.commit()
    return {"event_id": ev.id, "run_id": run.id, "summary": summary}


@router.delete("/{lease_id}/events/{event_id}")
def event_delete(lease_id: int, event_id: int, db: Session = Depends(get_db), user: User = Depends(require("event.write"))):
    lease = get_lease(lease_id, db, user)
    ev = db.get(LeaseEventRow, event_id)
    if ev is None or ev.lease_id != lease.id:
        raise HTTPException(404)
    if ev.status == "Approved":
        raise HTTPException(409, "Approved events cannot be deleted — record a further event instead.")
    ev.status = "Rejected"
    lease.inputs_changed_at = datetime.now()
    audit.log(db, user, "REJECT", "LeaseEvent", ev.id, lease.lease_code, "status", "Draft", "Rejected", "Event withdrawn")
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- workflow
@router.post("/{lease_id}/workflow/{action}")
def workflow(lease_id: int, action: str, payload: dict = Body(default={}), db: Session = Depends(get_db),
             user: User = Depends(current_user)):
    lease = get_lease(lease_id, db, user)
    try:
        res = transition(db, lease, action, user, (payload or {}).get("comment"))
    except ServiceError as exc:
        db.rollback()
        _err(exc)
    db.commit()
    return res


# ---------------------------------------------------------------- journals, audit, documents, tax
@router.get("/{lease_id}/journals")
def journals(lease_id: int, db: Session = Depends(get_db), user: User = Depends(require("journal.read"))):
    lease = get_lease(lease_id, db, user)
    run = current_run(db, lease)
    return lease_journals(db, lease, run) if run else []


@router.get("/{lease_id}/audit")
def lease_audit(lease_id: int, db: Session = Depends(get_db), user: User = Depends(require("lease.read"))):
    lease = get_lease(lease_id, db, user)
    rows = db.scalars(select(AuditLog).where(or_(AuditLog.object_label == lease.lease_code,
                                                 (AuditLog.object_type == "Lease") & (AuditLog.object_id == str(lease.id))))
                      .order_by(AuditLog.at.desc()).limit(500)).all()
    return to_jsonable([{"at": a.at, "username": a.username, "action": a.action, "object_type": a.object_type, "field": a.field,
                         "old_value": a.old_value, "new_value": a.new_value, "reason": a.reason, "approval_status": a.approval_status}
                        for a in rows])


@router.post("/{lease_id}/documents")
async def upload_doc(lease_id: int, file: UploadFile = File(...), doc_type: str = Form("Lease agreement"),
                     event_id: Optional[int] = Form(None), notes: Optional[str] = Form(None), db: Session = Depends(get_db),
                     user: User = Depends(require("lease.write"))):
    lease = get_lease(lease_id, db, user)
    data = await file.read()
    doc = save_document(db, company_of(db), data, file.filename, user, lease.id, event_id, doc_type, notes)
    db.commit()
    return {"id": doc.id, "filename": doc.filename}


@router.get("/{lease_id}/tax")
def tax(lease_id: int, as_of: Optional[str] = None, db: Session = Depends(get_db), user: User = Depends(require("lease.read"))):
    lease = get_lease(lease_id, db, user)
    return tax_view(db, lease, parse_date(as_of) or date.today())


# ---------------------------------------------------------------- lease-level exports
@router.get("/{lease_id}/export/{kind}")
def export(lease_id: int, kind: str, client: str = "", period: str = "", prepared_by: str = "", reviewed_by: str = "", as_of: str = "",
           db: Session = Depends(get_db), user: User = Depends(require("export"))):
    lease = get_lease(lease_id, db, user)
    run = current_run(db, lease)
    if run is None:
        raise HTTPException(404, "Calculate the lease first")
    ld = lease_dict(db, lease)
    rd = {"run_no": run.run_no, "status": run.status, "summary": run.summary}
    comp = db.get(Company, lease.company_id)
    audit.log(db, user, "EXPORT", "Lease", lease.id, lease.lease_code, "export", None, kind)
    db.commit()
    fn = f"{lease.lease_code}"
    lessor = run.summary.get("kind") == "LESSOR"
    if run.summary.get("kind") in ("LESSOR", "SUBLEASE") and not is_current_lessor_run(run.summary):
        raise HTTPException(409, "This lease was calculated with the previous lessor engine. Recalculate it (reopen first if it is "
                                 "approved) to produce the lessor workpaper, memo and schedules.")
    at = parse_date(as_of) or date.today()
    if kind == "workpaper.xlsx":
        hdr = {"client": client or comp.name, "period": period, "prepared_by": prepared_by or user.full_name, "reviewed_by": reviewed_by}
        data = lessor_workpaper_xlsx(ld, rd, hdr, at) if lessor else lease_workpaper_xlsx(ld, rd, hdr)
        return Response(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": f'attachment; filename="{fn}_Ind_AS_116_{"lessor_" if lessor else ""}workpaper.xlsx"'})
    if kind == "memo.docx":
        data = lessor_memo_docx(ld, rd, comp.name, at) if lessor else lease_memo_docx(ld, rd, comp.name)
        return Response(data, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        headers={"Content-Disposition": f'attachment; filename="{fn}_accounting_memo.docx"'})
    cols = [{"key": "period_end", "label": "Period end", "type": "date"}, {"key": "liab_open", "label": "Opening liability", "type": "money"},
            {"key": "liab_additions", "label": "Additions", "type": "money"}, {"key": "interest", "label": "Interest", "type": "money"},
            {"key": "payments", "label": "Payments", "type": "money"},
            {"key": "liab_remeasurement", "label": "Remeasurement", "type": "money"},
            {"key": "liab_modification", "label": "Modification", "type": "money"},
            {"key": "liab_derecognised", "label": "Derecognised", "type": "money"},
            {"key": "liab_close", "label": "Closing liability", "type": "money"}, {"key": "rou_open", "label": "Opening ROU", "type": "money"},
            {"key": "rou_additions", "label": "ROU additions", "type": "money"}, {"key": "depreciation", "label": "Depreciation", "type": "money"},
            {"key": "impairment", "label": "Impairment", "type": "money"}, {"key": "rou_close", "label": "Closing ROU", "type": "money"}]
    rows = run.summary.get("periods", []) or run.summary.get("rows", [])
    if run.summary.get("kind") in ("LESSOR", "SUBLEASE"):
        cols = lessor_schedule_columns(rows)
    elif run.summary.get("kind") == "EXEMPT":
        keys = list(rows[0].keys()) if rows else []
        cols = [{"key": k, "label": k.replace("_", " ").title(), "type": "date" if "period" in k else "money"} for k in keys]
    title = f"Lease schedule — {lease.lease_code} {lease.description}"
    meta = {"Company": comp.name, "Calc run": f"{run.run_no} ({run.status})", "Generated": datetime.now().strftime("%d-%b-%Y %H:%M")}
    if kind == "schedule.xlsx":
        return Response(table_xlsx(title, cols, rows, meta), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": f'attachment; filename="{fn}_schedule.xlsx"'})
    if kind == "schedule.csv":
        return Response(table_csv(cols, rows), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{fn}_schedule.csv"'})
    if kind == "schedule.pdf":
        return Response(table_pdf(title, cols, rows, meta), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{fn}_schedule.pdf"'})
    raise HTTPException(404, "Unknown export")
