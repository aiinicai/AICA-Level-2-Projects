"""Lease service: master data, payment generation, mapping to the engine, calculation runs.

The accounting logic lives in app.engine; this module only translates stored data into
engine inputs, runs the engine and persists immutable calculation runs.
"""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db.models import (AssetClass, CalcRun, Company, Counterparty, Deposit, DiscountRate, Entity, FxRate, Lease,
                         LeaseAssessment, LeaseCost, LeaseEventRow, LeaseOptionRow, LiabilitySchedule, PaymentScheduleRow,
                         PeriodBalance, RestorationObligation, RouSchedule)
from ..engine.calendar_utils import add_months, months_between_frac, next_day, parse_date, prev_day
from ..engine.decimal_utils import D, ZERO, q, to_jsonable
from ..engine.exemptions import ExemptionInput, exempt_expense_schedule
from ..engine.lessee import ENGINE_VERSION, EngineInputError, calculate_lessee
from ..engine.lease_term import determine_lease_term
from ..engine.lessor import LessorDepositInput, LessorEvent, LessorInputError, LessorLeaseInput, calculate_lessor
from ..engine.models import (CostItem, DepositInput, EventType, FxInput, ImpairmentInput, LeaseEvent, LeaseOption,
                             LeaseTermInput, LesseeLeaseInput, ModificationInput, OpeningBalance, OptionHolder, OptionKind,
                             PaymentCategory, PaymentLine, ReassessmentInput, ReassessmentKind, RestorationInput,
                             RestorationRevisionInput, RouDerecognitionInput, Severity, TerminationInput, Timing)
from ..engine.payments import EscalationRule, PaymentTerms, RentFree, RentStep, generate_payments
from ..engine.sale_leaseback import SaleLeasebackInput, calculate_sale_leaseback
from ..engine.sublease import SubleaseInput, calculate_sublease
from . import audit
from .settings_service import build_policy, get_settings

EDITABLE_STATUSES = ("Draft",)
FREQ_MONTHS = {"MONTHLY": 1, "QUARTERLY": 3, "HALF_YEARLY": 6, "ANNUAL": 12}


class ServiceError(Exception):
    def __init__(self, message: str, issues: list | None = None, status: int = 400):
        super().__init__(message)
        self.message = message
        self.issues = issues or []
        self.status = status


# --------------------------------------------------------------------------- helpers
def dec(v, default=None):
    if v is None or v == "":
        return default
    return D(v)


def next_lease_code(db: Session) -> str:
    n = db.scalar(select(func.count(Lease.id))) or 0
    while True:
        n += 1
        code = f"L-{n:04d}"
        if not db.scalar(select(Lease.id).where(Lease.lease_code == code)):
            return code


def company_of(db: Session) -> Company:
    c = db.scalar(select(Company).order_by(Company.id))
    if c is None:
        raise ServiceError("Company not configured", status=500)
    return c


def expedient_for(lease: Lease) -> bool:
    if lease.non_lease_expedient is not None:
        return bool(lease.non_lease_expedient)
    return bool(lease.asset_class.non_lease_expedient) if lease.asset_class else False


# --------------------------------------------------------------------------- payment generation
def terms_from_config(cfg: dict, fy_start_month: int = 4) -> PaymentTerms:
    esc = [EscalationRule(value=D(e["value"]), every_months=int(e.get("every_months") or 12), kind=e.get("kind", "PERCENT"),
                          first_date=parse_date(e.get("first_date")), compounding=bool(e.get("compounding", True)),
                          applies_to=e.get("applies_to", "LEASE")) for e in cfg.get("escalations", []) if e.get("value") not in (None, "")]
    steps = [RentStep(parse_date(s["start"]), D(s["amount"]), dec(s.get("non_lease_amount"))) for s in cfg.get("steps", [])
             if s.get("start") and s.get("amount") not in (None, "")]
    rf = [RentFree(parse_date(r["start"]), parse_date(r["end"]), r.get("applies_to", "LEASE")) for r in cfg.get("rent_free", [])
          if r.get("start") and r.get("end")]
    return PaymentTerms(amount=D(cfg.get("amount") or 0), start_date=parse_date(cfg["start_date"]), end_date=parse_date(cfg["end_date"]),
                        frequency_months=int(cfg.get("frequency_months") or 1), timing=Timing(cfg.get("timing") or "ADVANCE"),
                        alignment=cfg.get("alignment") or "ANNIVERSARY", due_day=int(cfg["due_day"]) if cfg.get("due_day") else None,
                        due_offset_days=int(cfg.get("due_offset_days") or 0), escalations=esc,
                        escalation_anchor=parse_date(cfg.get("escalation_anchor")), steps=steps, rent_free=rf,
                        non_lease_amount=D(cfg.get("non_lease_amount") or 0), prorate_partial=bool(cfg.get("prorate_partial", True)),
                        category=PaymentCategory(cfg.get("category") or "FIXED"), description=cfg.get("description") or "Rent",
                        fy_start_month=fy_start_month)


def generate_lines(lease: Lease, fy_start_month: int = 4) -> list[PaymentLine]:
    """Base-term lines from the generator config plus lines for optional extension periods."""
    cfg = lease.generator_config
    if not cfg or not cfg.get("start_date") or not cfg.get("end_date") or cfg.get("amount") in (None, ""):
        raise ServiceError("Payment terms are incomplete (amount, start and end dates are required).")
    t = terms_from_config(cfg, fy_start_month)
    lines = generate_payments(t)
    last_amount = lines[-1].lease_amount if lines else D(cfg.get("amount"))
    last_nl = lines[-1].non_lease_amount if lines else ZERO
    no = len(lines) + 1
    prev_end = t.end_date
    for opt in sorted([o for o in lease.options if o.kind == "EXTENSION" and o.extension_end_date],
                      key=lambda o: o.extension_end_date):
        start = next_day(prev_end)
        if opt.extension_end_date <= prev_end:
            continue
        uplift = (Decimal(1) + D(opt.renewal_escalation_pct or 0) / 100)
        ocfg = copy.deepcopy(cfg)
        ocfg.update({"amount": str(q(last_amount * uplift)), "start_date": start.isoformat(),
                     "end_date": opt.extension_end_date.isoformat(), "rent_free": [], "steps": [],
                     "non_lease_amount": str(last_nl), "escalation_anchor": start.isoformat(),
                     "description": f"Rent — optional extension period ({opt.description or 'extension option'})"})
        for e in ocfg.get("escalations", []):
            e["first_date"] = None
        olines = generate_payments(terms_from_config(ocfg, fy_start_month), start_line_no=no)
        for l in olines:
            l.source = "OPTION"
        lines += olines
        no += len(olines)
        if olines:
            last_amount, last_nl = olines[-1].lease_amount, olines[-1].non_lease_amount
        prev_end = opt.extension_end_date
    return lines


def regenerate_payments(db: Session, lease: Lease, user) -> int:
    comp = db.get(Company, lease.company_id)
    lines = generate_lines(lease, comp.fy_start_month or 4)
    manual = [p for p in lease.payments if p.source == "MANUAL"]
    lease.payments = [p for p in manual]
    no = 1
    for l in lines:
        lease.payments.append(PaymentScheduleRow(line_no=no, payment_date=l.date, period_start=l.period_start,
                                                 period_end=l.period_end, lease_amount=l.lease_amount,
                                                 non_lease_amount=l.non_lease_amount, category=l.category.value
                                                 if hasattr(l.category, "value") else l.category,
                                                 description=l.description, source=l.source or "GENERATED"))
        no += 1
    for m in manual:
        m.line_no = no
        no += 1
    audit.log(db, user, "GENERATE_PAYMENTS", "Lease", lease.id, lease.lease_code, "payments", None, f"{len(lines)} lines generated")
    return len(lines)


def lines_from_rows(rows: list[PaymentScheduleRow]) -> list[PaymentLine]:
    return [PaymentLine(date=r.payment_date, lease_amount=D(r.lease_amount or 0), non_lease_amount=D(r.non_lease_amount or 0),
                        category=PaymentCategory(r.category or "FIXED"), period_start=r.period_start, period_end=r.period_end,
                        description=r.description or "", line_no=r.line_no, include_override=r.include_override,
                        override_reason=r.override_reason or "", source=r.source or "") for r in rows]


def lines_from_json(items: list[dict]) -> list[PaymentLine]:
    out = []
    for i, x in enumerate(items or [], start=1):
        out.append(PaymentLine(date=parse_date(x["date"]), lease_amount=D(x.get("lease_amount", x.get("amount", 0))),
                               non_lease_amount=D(x.get("non_lease_amount") or 0), category=PaymentCategory(x.get("category") or "FIXED"),
                               period_start=parse_date(x.get("period_start")), period_end=parse_date(x.get("period_end")),
                               description=x.get("description", ""), line_no=i, source="EVENT"))
    return out


# --------------------------------------------------------------------------- mapping to the engine
def _options(lease: Lease) -> list[LeaseOption]:
    out = []
    for o in lease.options:
        out.append(LeaseOption(kind=OptionKind(o.kind), holder=OptionHolder(o.holder or "LESSEE"), exercise_date=o.exercise_date,
                               extension_end_date=o.extension_end_date, price=D(o.price or 0),
                               reasonably_certain=bool(o.reasonably_certain), rationale=o.rationale or "",
                               description=o.description or ""))
    return out


def _event_payments(db: Session, lease: Lease, det: dict, e: date, new_term_end: Optional[date], base_lines: list[PaymentLine],
                    fy: int, scope_decrease: Decimal = ZERO) -> list[PaymentLine]:
    mode = det.get("payments_mode") or ("MANUAL" if det.get("new_payments") else "GENERATE" if det.get("new_payment_terms") else "KEEP")
    if mode == "MANUAL":
        return lines_from_json(det.get("new_payments"))
    if mode == "GENERATE":
        cfg = copy.deepcopy(det["new_payment_terms"])
        cfg.setdefault("start_date", e.isoformat())
        if new_term_end and not cfg.get("end_date"):
            cfg["end_date"] = new_term_end.isoformat()
        lines = generate_payments(terms_from_config(cfg, fy))
        for l in lines:
            l.source = "EVENT"
        return lines
    end = new_term_end
    out = []
    for l in base_lines:
        if l.date < e:
            continue
        if end and (l.period_start or l.date) > end:
            continue
        nl = copy.copy(l)
        if mode == "SCALE" and scope_decrease:
            nl.lease_amount = q(D(l.lease_amount) * (1 - scope_decrease))
            nl.non_lease_amount = q(D(l.non_lease_amount) * (1 - scope_decrease))
        if mode in ("KEEP", "KEEP_PLUS_OPTION", "SCALE"):
            nl.include_override = None
        out.append(nl)
    return out


def build_events(db: Session, lease: Lease, base_lines: list[PaymentLine], fy: int, statuses=("Draft", "Submitted", "Approved"),
                 extra: LeaseEventRow | None = None) -> list[LeaseEvent]:
    rows = [e for e in lease.events if e.status in statuses]
    if extra is not None and extra not in rows:
        rows.append(extra)
    out = []
    for ev in sorted(rows, key=lambda x: (x.effective_date, x.id or 0)):
        det = ev.details or {}
        e = ev.effective_date
        t = ev.event_type
        ref = f"EV-{ev.id}" if ev.id else "EV-preview"
        after = bool(det.get("apply_after_payments"))
        if t == "MODIFICATION":
            nte = parse_date(det.get("new_term_end"))
            sd = D(det.get("scope_decrease_fraction") or 0)
            pays = _event_payments(db, lease, det, e, nte, base_lines, fy, sd)
            out.append(LeaseEvent(EventType.MODIFICATION, e, ref, after, modification=ModificationInput(
                e, ev.description or "", pays, dec(det.get("revised_rate_pct")), nte, sd, bool(det.get("additional_rou")),
                bool(det.get("commensurate_standalone_price")), parse_date(det.get("new_useful_life_end")),
                det.get("purchase_option_rc"))))
        elif t == "REASSESSMENT":
            nte = parse_date(det.get("new_term_end"))
            pays = _event_payments(db, lease, det, e, nte, base_lines, fy)
            out.append(LeaseEvent(EventType.REASSESSMENT, e, ref, after, reassessment=ReassessmentInput(
                e, ReassessmentKind(ev.subtype or det.get("kind") or "LEASE_TERM"), ev.description or "", pays,
                dec(det.get("revised_rate_pct")), nte, det.get("purchase_option_rc"), parse_date(det.get("new_useful_life_end")))))
        elif t == "TERMINATION":
            out.append(LeaseEvent(EventType.TERMINATION, e, ref, after, termination=TerminationInput(e, D(det.get("penalty") or 0),
                                                                                                     ev.description or "")))
        elif t == "IMPAIRMENT":
            out.append(LeaseEvent(EventType.IMPAIRMENT, e, ref, after, impairment=ImpairmentInput(
                e, dec(det.get("impairment_amount")), dec(det.get("recoverable_amount")), det.get("cgu") or "",
                det.get("rationale") or ev.description or "")))
        elif t == "RESTORATION_REVISION":
            out.append(LeaseEvent(EventType.RESTORATION_REVISION, e, ref, after, restoration_revision=RestorationRevisionInput(
                e, dec(det.get("new_estimated_cost")), dec(det.get("new_discount_rate_pct")), parse_date(det.get("new_settlement_date")),
                ev.description or "")))
        elif t == "ROU_DERECOGNITION":
            out.append(LeaseEvent(EventType.ROU_DERECOGNITION, e, ref, after, rou_derecognition=RouDerecognitionInput(
                e, D(det.get("fraction") or 0), ev.description or "")))
    return out


def fx_input(db: Session, lease: Lease, functional: str) -> Optional[FxInput]:
    if (lease.currency or functional) == functional:
        return None
    rows = db.scalars(select(FxRate).where(FxRate.from_ccy == lease.currency, FxRate.to_ccy == functional)
                      .order_by(FxRate.rate_date)).all()
    rates = {r.rate_date: D(r.rate) for r in rows if r.rate_type in ("SPOT", "CLOSING")}
    avgs = {r.rate_date: D(r.rate) for r in rows if r.rate_type == "AVERAGE"}
    return FxInput(functional, rates, avgs)


def build_engine_input(db: Session, lease: Lease, extra_event: LeaseEventRow | None = None,
                       event_statuses=("Draft", "Submitted", "Approved")) -> LesseeLeaseInput:
    comp = db.get(Company, lease.company_id)
    fy = comp.fy_start_month or 4
    if lease.commencement_date is None or lease.contract_end is None:
        raise ServiceError("Commencement date and contract end date are required.")
    if lease.discount_rate_pct in (None, ""):
        raise ServiceError("Discount rate is missing — a capitalised lease cannot be measured without it (Ind AS 116.26).")
    pending = [o for o in lease.options if o.reasonably_certain is None]
    if pending:
        raise ServiceError("Accounting judgment required: the 'reasonably certain' assessment is missing for "
                           + ", ".join(f"{o.kind.lower()} option ({o.description or o.exercise_date})" for o in pending) + ".")
    if not lease.payments:
        if lease.generator_config:
            regenerate_payments(db, lease, None)
        else:
            raise ServiceError("No lease payments entered.")
    base_lines = lines_from_rows(lease.payments)
    term = LeaseTermInput(lease.commencement_date, lease.contract_end, _options(lease), lease.enforceable_end,
                          lease.enforceable_rationale or "")
    costs = lease.costs
    idc = [CostItem(c.cost_date, D(c.amount), c.description or "") for c in costs if c.kind == "IDC"]
    inc = [CostItem(c.cost_date, D(c.amount), c.description or "") for c in costs if c.kind == "INCENTIVE"]
    pre = [CostItem(c.cost_date, D(c.amount), c.description or "") for c in costs if c.kind == "PREPAID"]
    oth = [CostItem(c.cost_date, D(c.amount), c.description or "") for c in costs if c.kind == "OTHER"]
    dep = None
    if lease.deposits:
        d = lease.deposits[0]
        dep = DepositInput(D(d.amount), d.payment_date, d.refund_date, bool(d.interest_bearing), D(d.contractual_rate_pct or 0),
                           dec(d.market_rate_pct), bool(d.treat_difference_as_prepaid_rent))
    rest = None
    if lease.restorations:
        r = lease.restorations[0]
        rest = RestorationInput(D(r.estimated_cost), r.settlement_date, D(r.discount_rate_pct), r.recognition_date,
                                bool(r.cost_is_current_price), D(r.inflation_pct or 0))
    opening = None
    if lease.opening_balance and lease.opening_balance.get("cutover_date"):
        ob = lease.opening_balance
        opening = OpeningBalance(parse_date(ob["cutover_date"]), D(ob["liability"]), D(ob["rou_cost"]), D(ob.get("rou_acc_dep") or 0),
                                 D(ob.get("rou_acc_imp") or 0), bool(ob.get("use_implied_rate", True)))
    events = build_events(db, lease, base_lines, fy, event_statuses, extra_event)
    policy = build_policy(comp, lease.policy_overrides)
    return LesseeLeaseInput(
        lease_id=lease.lease_code, commencement=lease.commencement_date, term=term, payments=base_lines,
        discount_rate_pct=D(lease.discount_rate_pct), currency=lease.currency or comp.functional_currency, rate_basis=lease.rate_basis,
        policy=policy, asset_class=lease.asset_class.name if lease.asset_class else "Other", description=lease.description or "",
        idc=idc, incentives_received=inc, prepaid_before_commencement=pre, other_rou_adjustments=oth, deposit=dep,
        restoration=rest, useful_life_end=lease.useful_life_end, ownership_transfers=bool(lease.ownership_transfers),
        non_lease_expedient=expedient_for(lease), events=events, fx=fx_input(db, lease, comp.functional_currency),
        opening=opening)


# --------------------------------------------------------------------------- serialisation
def serialize_lessee(res) -> dict:
    out = to_jsonable({
        "lease_id": res.lease_id, "currency": res.currency, "engine_version": res.engine_version,
        "term": res.term, "initial": res.initial, "payment_rows": res.payment_rows, "events": res.events,
        "payments": res.payments, "flags": res.flags, "issues": res.issues, "deposit": res.deposit,
        "restoration": res.restoration, "fx_periods": res.fx_periods, "totals": res.totals,
        "postings": [{"date": p.date, "event": p.event, "narration": p.narration, "period_end": p.period_end, "ref": p.ref,
                      "lines": [{"role": l[0], "debit": l[1], "credit": l[2]} for l in p.lines]} for p in res.postings],
    })
    rows = []
    for r in res.periods:
        d = to_jsonable(r)
        d.pop("detail", None)
        rows.append(d)
    out["periods"] = rows
    out["kind"] = "LESSEE"
    return out


def inputs_snapshot(inp) -> dict:
    return to_jsonable(inp)


# --------------------------------------------------------------------------- calculation
def calculate(db: Session, lease: Lease, user, persist: bool = True) -> tuple[dict, Optional[CalcRun]]:
    comp = db.get(Company, lease.company_id)
    lt = lease.lease_type or "STANDARD"
    detail_rows = None
    if lease.role == "LESSOR" and lt != "SUBLEASE":
        summary, snap = _calc_lessor(db, lease, comp)
    elif lt == "SUBLEASE":
        summary, snap = _calc_sublease(db, lease, comp)
    elif lt in ("SHORT_TERM", "LOW_VALUE"):
        summary, snap = _calc_exempt(db, lease, comp)
    else:
        try:
            inp = build_engine_input(db, lease)
            if lt == "SALE_LEASEBACK":
                summary, snap, detail_rows = _calc_slb(db, lease, comp, inp)
            else:
                res = calculate_lessee(inp)
                summary = serialize_lessee(res)
                snap = inputs_snapshot(inp)
                detail_rows = [(r.period_end, to_jsonable({"detail": r.detail, "maturity": r.maturity})) for r in res.periods]
        except EngineInputError as exc:
            raise ServiceError("Calculation blocked by input validation.", [to_jsonable(i) for i in exc.issues])
    summary["lease_type"] = lt
    summary["calculated_at"] = datetime.now().isoformat(timespec="seconds")
    summary = to_jsonable(summary)
    snap = to_jsonable(snap)
    if not persist:
        return summary, None
    h = hashlib.sha256(json.dumps(snap, sort_keys=True, default=str).encode()).hexdigest()
    n = (db.scalar(select(func.max(CalcRun.run_no)).where(CalcRun.lease_id == lease.id)) or 0) + 1
    for old in db.scalars(select(CalcRun).where(CalcRun.lease_id == lease.id, CalcRun.status.in_(["Draft", "Prepared", "Under Review"]))):
        old.status = "Superseded"
        old.is_current = False
    for old in db.scalars(select(CalcRun).where(CalcRun.lease_id == lease.id, CalcRun.is_current == True)):  # noqa: E712
        old.is_current = False
    run = CalcRun(lease_id=lease.id, run_no=n, status="Draft", is_current=True, engine_version=ENGINE_VERSION, inputs=snap,
                  inputs_hash=h, summary=summary, created_by=getattr(user, "id", None))
    db.add(run)
    db.flush()
    for r in summary.get("periods", []):
        db.add(LiabilitySchedule(calc_run_id=run.id, period_start=parse_date(r["period_start"]), period_end=parse_date(r["period_end"]),
                                 opening=r["liab_open"], additions=r["liab_additions"], interest=r["interest"], payments=r["payments"],
                                 remeasurement=r["liab_remeasurement"], modification=r["liab_modification"],
                                 derecognised=r["liab_derecognised"], closing=r["liab_close"], current=r["liab_current"],
                                 non_current=r["liab_noncurrent"]))
        db.add(RouSchedule(calc_run_id=run.id, period_end=parse_date(r["period_end"]), opening=r["rou_open"], additions=r["rou_additions"],
                           depreciation=r["depreciation"], impairment=r["impairment"], remeasurement=r["rou_remeasurement"],
                           modification=r["rou_modification"], derecognised=r["rou_derecognised"], closing=r["rou_close"],
                           cost_close=r["rou_cost_close"], accdep_close=r["rou_accdep_close"], accimp_close=r["rou_accimp_close"]))
    for pe, data in (detail_rows or []):
        db.add(PeriodBalance(calc_run_id=run.id, period_end=pe, data=data))
    if summary.get("kind") in ("LESSOR", "SUBLEASE"):
        msg = (f"Run {n}: {str(summary.get('classification') or '').title()} lease; net investment {summary.get('net_investment')}"
               if summary.get("classification") == "FINANCE" else f"Run {n}: {str(summary.get('classification') or '').title()} lease")
    else:
        msg = f"Run {n}: liability {summary.get('initial', {}).get('liability')} ROU {summary.get('initial', {}).get('rou')}"
    audit.log(db, user, "CALCULATE", "Lease", lease.id, lease.lease_code, "calc_run", None, msg)
    return summary, run


def _calc_exempt(db: Session, lease: Lease, comp: Company):
    s = get_settings(comp)
    a = db.scalar(select(LeaseAssessment).where(LeaseAssessment.lease_id == lease.id))
    lines = lines_from_rows(lease.payments) if lease.payments else generate_lines(lease, comp.fy_start_month or 4)
    thr = s["policies"].get("low_value_threshold")
    inp = ExemptionInput(lease.lease_code, lease.lease_type, LeaseTermInput(lease.commencement_date, lease.contract_end, _options(lease),
                                                                         lease.enforceable_end, lease.enforceable_rationale or ""),
                         lines, lease.asset_class.name if lease.asset_class else "",
                         class_election_short_term=bool(lease.asset_class.short_term_election) if lease.asset_class else False,
                         asset_value_when_new=dec(a.asset_value_when_new) if a else None, low_value_threshold=dec(thr),
                         benefits_on_own=(a.benefits_on_own is not False) if a else True,
                         not_highly_dependent=(a.not_highly_dependent is not False) if a else True)
    res = exempt_expense_schedule(inp)
    summary = to_jsonable({"kind": "EXEMPT", "exemption": lease.lease_type, "valid": res.valid, "reasons": res.reasons,
                           "issues": res.issues, "term_months": res.term_months, "reference": res.reference,
                           "rows": res.rows, "total_expense": res.total_expense, "periods": []})
    summary["postings"] = [{"date": r["period_end"], "event": "EXEMPT_EXPENSE", "period_end": r["period_end"], "ref": "",
                            "narration": f"{'Short-term' if lease.lease_type == 'SHORT_TERM' else 'Low-value'} lease expense — straight-line (Ind AS 116.6)",
                            "lines": [{"role": "SHORT_TERM_LEASE_EXPENSE" if lease.lease_type == "SHORT_TERM" else "LOW_VALUE_LEASE_EXPENSE",
                                       "debit": r["expense"], "credit": "0"},
                                      {"role": "ACCRUED_RENT", "debit": "0", "credit": r["expense"]}]}
                           for r in summary["rows"] if D(r["expense"]) != 0]
    summary["postings"] += [{"date": r["period_end"], "event": "PAYMENT", "period_end": r["period_end"], "ref": "",
                             "narration": "Rent paid — exempt lease", "lines": [{"role": "ACCRUED_RENT", "debit": r["cash_paid"], "credit": "0"},
                                                                                 {"role": "LESSOR_PAYABLE", "debit": "0", "credit": r["cash_paid"]}]}
                            for r in summary["rows"] if D(r["cash_paid"]) != 0]
    if not res.valid:
        summary["issues"] = summary.get("issues", [])
    return summary, to_jsonable(inp)


LESSOR_EVENT_TYPES = ("MODIFICATION", "TERMINATION", "UGR_REVISION", "ECL")


def build_lessor_events(db: Session, lease: Lease, base_lines: list[PaymentLine], fy: int, statuses=("Draft", "Submitted", "Approved"),
                        extra: LeaseEventRow | None = None) -> list[LessorEvent]:
    rows = [e for e in lease.events if e.status in statuses]
    if extra is not None and extra not in rows:
        rows.append(extra)
    out = []
    for ev in sorted(rows, key=lambda x: (x.effective_date, x.id or 0)):
        det = ev.details or {}
        e = ev.effective_date
        t = ev.event_type
        ref_ = f"EV-{ev.id}" if ev.id else "EV-preview"
        if t not in LESSOR_EVENT_TYPES:
            raise ServiceError(f"'{t.replace('_', ' ').title()}' does not apply to a lessor lease. Lessor events: modification "
                               "(paras 79–80, 87), early termination, reduction of the unguaranteed residual value (para 77) and "
                               "expected credit losses (Ind AS 109).")
        le = LessorEvent(t, e, ref_, ev.description or "", nature=ev.subtype or det.get("nature") or "",
                         new_term_end=parse_date(det.get("new_term_end")), new_unguaranteed_residual=dec(det.get("new_unguaranteed_residual")),
                         penalty=D(det.get("penalty") or 0), asset_value_returned=dec(det.get("asset_value_returned")),
                         loss_allowance=dec(det.get("loss_allowance")))
        if t == "MODIFICATION" and le.nature != "SEPARATE_LEASE":
            le.new_payments = _event_payments(db, lease, det, e, le.new_term_end, base_lines, fy)
        out.append(le)
    return out


def build_lessor_input(db: Session, lease: Lease, comp: Company, extra_event: LeaseEventRow | None = None,
                       event_statuses=("Draft", "Submitted", "Approved")) -> LessorLeaseInput:
    det = lease.lessor_details or {}
    fy = comp.fy_start_month or 4
    if lease.commencement_date is None or lease.contract_end is None:
        raise ServiceError("Commencement date and contract end date are required.")
    pending = [o for o in lease.options if o.reasonably_certain is None]
    if pending:
        raise ServiceError("Accounting judgment required: the 'reasonably certain' assessment is missing for "
                           + ", ".join(f"{o.kind.lower()} option ({o.description or o.exercise_date})" for o in pending) + ".")
    if not lease.payments:
        if lease.generator_config:
            regenerate_payments(db, lease, None)
        else:
            raise ServiceError("No lease payments entered.")
    base_lines = lines_from_rows(lease.payments)
    term = determine_lease_term(LeaseTermInput(lease.commencement_date, lease.contract_end, _options(lease), lease.enforceable_end,
                                               lease.enforceable_rationale or ""))
    policy = build_policy(comp, lease.policy_overrides)
    if det.get("income_method"):
        policy.lessor_income_method = det["income_method"]
    dep = None
    if lease.deposits:
        d = lease.deposits[0]
        dep = LessorDepositInput(D(d.amount), d.payment_date or lease.commencement_date, d.refund_date or next_day(term.term_end),
                                 bool(d.interest_bearing), D(d.contractual_rate_pct or 0), dec(d.market_rate_pct),
                                 d.treat_difference_as_prepaid_rent is not False)
    events = build_lessor_events(db, lease, base_lines, fy, event_statuses, extra_event)
    return LessorLeaseInput(
        lease_id=lease.lease_code, commencement=lease.commencement_date, term_end=term.term_end, payments=base_lines,
        fair_value=D(det.get("fair_value") or 0), carrying_amount=D(det.get("carrying_amount") or 0),
        economic_life_months=int(D(det["economic_life_months"])) if det.get("economic_life_months") not in (None, "") else None,
        unguaranteed_residual=D(det.get("unguaranteed_residual") or 0), residual_date=parse_date(det.get("residual_date")),
        lessor_idc=D(det.get("lessor_idc") or 0), implicit_rate_pct=dec(det.get("implicit_rate_pct")),
        transfers_ownership=bool(det.get("transfers_ownership")), bargain_purchase_option=bool(det.get("bargain_purchase_option")),
        specialised_asset=bool(det.get("specialised_asset")), lessee_bears_cancellation_losses=bool(det.get("lessee_bears_cancellation_losses")),
        residual_fv_gains_to_lessee=bool(det.get("residual_fv_gains_to_lessee")), bargain_renewal=bool(det.get("bargain_renewal")),
        manufacturer_dealer=bool(det.get("manufacturer_dealer")), substantially_all_pct=D(det.get("substantially_all_pct") or 90),
        major_part_pct=D(det.get("major_part_pct") or 75), classification_override=det.get("classification_override") or None,
        override_rationale=det.get("override_rationale") or "", policy=policy, market_rate_pct=dec(det.get("market_rate_pct")),
        deposit=dep, events=events, term=term, currency=lease.currency or comp.functional_currency, description=lease.description or "")


def serialize_lessor(res, kind: str = "LESSOR") -> dict:
    summary = to_jsonable({
        "kind": kind, "engine_version": res.engine_version, "classification": res.classification,
        "classification_final": res.classification_final, "suggested_classification": res.suggested_classification,
        "indicators": res.indicators, "implicit_rate_pct": res.implicit_rate_pct, "rate_source": res.rate_source,
        "pv_ratio_pct": res.pv_ratio_pct, "undiscounted_ratio_pct": res.undiscounted_ratio_pct, "term_ratio_pct": res.term_ratio_pct,
        "net_investment": res.net_investment, "gross_investment": res.gross_investment, "unearned_finance_income": res.unearned_finance_income,
        "selling_profit": res.selling_profit, "derecognition_gain": res.derecognition_gain, "revenue": res.revenue,
        "cost_of_sale": res.cost_of_sale,
        "pv_unguaranteed_residual": res.pv_unguaranteed_residual, "receivable_at_commencement": res.receivable_at_commencement,
        "rows": res.rows, "maturity": res.maturity, "flags": res.flags, "issues": res.issues, "explanation": res.explanation,
        "payments": res.payments, "pv_lines": res.pv_lines, "events": res.events, "segments": res.segments, "deposit": res.deposit,
        "idc": res.idc, "totals": res.totals, "term": res.term, "rate_basis": res.rate_basis, "income_method": res.income_method,
        "periods": []})
    summary["postings"] = [{"date": p.date.isoformat(), "event": p.event, "narration": p.narration,
                            "period_end": p.period_end.isoformat() if p.period_end else None, "ref": p.ref,
                            "lines": [{"role": l[0], "debit": str(l[1]), "credit": str(l[2])} for l in p.lines]} for p in res.postings]
    return summary


def _lessor_error(exc: LessorInputError) -> ServiceError:
    errs = [i for i in exc.issues if i.severity == Severity.ERROR]
    return ServiceError("Calculation blocked by input validation." if len(errs) != 1 else errs[0].message, [to_jsonable(i) for i in errs])


def _calc_lessor(db: Session, lease: Lease, comp: Company):
    inp = build_lessor_input(db, lease, comp)
    try:
        res = calculate_lessor(inp)
    except LessorInputError as exc:
        raise _lessor_error(exc)
    except ValueError as exc:
        raise ServiceError(str(exc))
    return serialize_lessor(res), to_jsonable(inp)


def rou_nbv_at(db: Session, head: Lease, at: date) -> Decimal:
    run = current_run(db, head)
    if not run:
        raise ServiceError("Head lease has no calculation — calculate the head lease first.")
    rows = run.summary.get("periods", [])
    prev = [r for r in rows if parse_date(r["period_end"]) < at]
    if not prev:
        return D(run.summary["initial"]["rou"])
    last = prev[-1]
    cur = [r for r in rows if parse_date(r["period_start"]) <= at <= parse_date(r["period_end"])]
    nbv = D(last["rou_close"])
    if cur:
        r = cur[0]
        ps, pe = parse_date(r["period_start"]), parse_date(r["period_end"])
        days = (pe - ps).days + 1
        nbv -= D(r["depreciation"]) * Decimal((at - ps).days) / Decimal(days)
    return q(nbv)


def _calc_sublease(db: Session, lease: Lease, comp: Company):
    det = lease.sublease_details or {}
    head = db.get(Lease, lease.head_lease_id) if lease.head_lease_id else None
    if head is None:
        raise ServiceError("Link the sublease to its head lease.")
    lines = lines_from_rows(lease.payments) if lease.payments else generate_lines(lease, comp.fy_start_month or 4)
    head_run = current_run(db, head)
    head_rate = D(head.discount_rate_pct or 0)
    nbv = rou_nbv_at(db, head, lease.commencement_date)
    head_term_end = parse_date(head_run.summary["term"]["term_end"]) if head_run else head.contract_end
    inp = SubleaseInput(lease.lease_code, head.lease_code, lease.commencement_date, lease.contract_end, lines, nbv, head_term_end,
                        head_rate, D(det.get("portion_subleased") or 1), head.lease_type == "SHORT_TERM",
                        dec(det.get("implicit_rate_pct")), det.get("classification_override"), det.get("override_rationale") or "",
                        policy=build_policy(comp, lease.policy_overrides))
    try:
        res = calculate_sublease(inp)
    except LessorInputError as exc:
        raise _lessor_error(exc)
    lr = res.lessor
    summary = to_jsonable({"kind": "SUBLEASE", "classification": res.classification, "classification_final": lr.classification_final,
                           "explanation": res.explanation, "rate_pct": res.rate_pct, "implicit_rate_pct": res.rate_pct,
                           "net_investment": res.net_investment, "rou_derecognised": res.rou_derecognised,
                           "gain_loss": res.gain_loss, "rows": res.rows, "flags": res.flags, "term_ratio_pct": res.term_ratio_pct,
                           "pv_ratio_pct": res.pv_ratio_pct, "head_lease": head.lease_code, "head_rou_nbv": nbv, "periods": [],
                           "segments": lr.segments, "rate_basis": lr.rate_basis, "payments": lr.payments, "totals": lr.totals,
                           "income_method": lr.income_method, "receivable_at_commencement": lr.receivable_at_commencement,
                           "unearned_finance_income": lr.unearned_finance_income, "gross_investment": lr.gross_investment})
    postings = []
    for p in res.postings:
        lines_ = [{"role": ("SUBLEASE_CLEARING" if l[0] == "ROU_ASSET_SUBLEASED" else l[0]), "debit": str(l[1]), "credit": str(l[2])}
                  for l in p.lines]
        postings.append({"date": p.date, "event": p.event, "narration": p.narration, "period_end": p.period_end, "ref": p.ref,
                         "lines": lines_})
    summary["postings"] = postings
    return summary, to_jsonable(inp)


def _calc_slb(db: Session, lease: Lease, comp: Company, inp: LesseeLeaseInput):
    det = lease.slb_details or {}
    if det.get("is_sale") is None:
        raise ServiceError("Record the Ind AS 115 sale assessment conclusion for the sale and leaseback (para 99).")
    probe = calculate_lessee(inp)
    leaseback = [PaymentLine(date=pv.date, lease_amount=pv.amount, description="Leaseback payment") for pv in probe.initial.pv_lines]
    slb = calculate_sale_leaseback(SaleLeasebackInput(
        lease.lease_code, lease.commencement_date, det.get("asset_description") or lease.asset_description or "",
        D(det.get("carrying_amount") or 0), D(det.get("sale_consideration") or 0), D(det.get("fair_value") or 0),
        leaseback, inp.discount_rate_pct, bool(det.get("is_sale")), det.get("assessment_notes") or "", policy=inp.policy))
    if slb.is_sale:
        adj = slb.rou_asset - probe.initial.rou
        inp.other_rou_adjustments = list(inp.other_rou_adjustments) + [
            CostItem(inp.commencement, adj, "Sale and leaseback: ROU measured at retained proportion of carrying amount (para 100(a))")]
        res = calculate_lessee(inp)
        summary = serialize_lessee(res)
        keep = [p for p in summary["postings"] if p["event"] not in ("COMMENCEMENT", "ROU_ADJUSTMENT")]
        slb_post = [{"date": p.date, "event": p.event, "narration": p.narration, "period_end": p.period_end, "ref": p.ref,
                     "lines": [{"role": l[0], "debit": str(l[1]), "credit": str(l[2])} for l in p.lines]} for p in slb.postings]
        summary["postings"] = slb_post + keep
        detail_rows = [(r.period_end, to_jsonable({"detail": r.detail, "maturity": r.maturity})) for r in res.periods]
    else:
        summary = {"kind": "SLB_FAILED", "periods": [], "postings": [{"date": p.date, "event": p.event, "narration": p.narration,
                                                                         "period_end": p.period_end, "ref": p.ref,
                                                                         "lines": [{"role": l[0], "debit": str(l[1]), "credit": str(l[2])}
                                                                                   for l in p.lines]} for p in slb.postings]}
        detail_rows = []
    summary["slb"] = to_jsonable({"is_sale": slb.is_sale, "steps": slb.steps, "rou_asset": slb.rou_asset,
                                  "financial_liability_total": slb.financial_liability_total,
                                  "lease_liability_portion": slb.lease_liability_portion, "additional_financing": slb.additional_financing,
                                  "prepayment": slb.prepayment, "gain_total": slb.gain_total,
                                  "gain_rights_transferred": slb.gain_rights_transferred,
                                  "gain_rights_retained_not_recognised": slb.gain_rights_retained_not_recognised, "flags": slb.flags,
                                  "buyer_lessor": slb.buyer_lessor})
    return summary, inputs_snapshot(inp), detail_rows


def is_lessor(lease: Lease) -> bool:
    return lease.role == "LESSOR" and (lease.lease_type or "STANDARD") != "SUBLEASE"


def preview_event(db: Session, lease: Lease, ev: LeaseEventRow) -> dict:
    """Compute the impact of an event without saving (pre vs post)."""
    if is_lessor(lease):
        comp = db.get(Company, lease.company_id)
        try:
            base = calculate_lessor(build_lessor_input(db, lease, comp, event_statuses=("Approved", "Submitted", "Draft")))
            res = calculate_lessor(build_lessor_input(db, lease, comp, extra_event=ev))
        except LessorInputError as exc:
            raise _lessor_error(exc)
        refs = ("EV-preview", f"EV-{ev.id}")
        new_events = [e for e in res.events if e["ref"] in refs]
        return {"lessor": True, "event": to_jsonable(new_events[0]) if new_events else None, "issues": to_jsonable(res.issues),
                "before": {"totals": to_jsonable(base.totals)}, "after": {"totals": to_jsonable(res.totals)},
                "postings": [to_jsonable({"date": p.date, "event": p.event, "narration": p.narration,
                                          "lines": [{"role": l[0], "debit": l[1], "credit": l[2]} for l in p.lines]})
                             for p in res.postings if p.ref in refs],
                "periods_after": to_jsonable([r for r in res.rows if r["period_end"] >= prev_day(ev.effective_date)][:24])}
    base = calculate_lessee(build_engine_input(db, lease, event_statuses=("Approved", "Submitted", "Draft")))
    inp = build_engine_input(db, lease, extra_event=ev)
    res = calculate_lessee(inp)
    new_events = [e for e in res.events if e.ref in ("EV-preview", f"EV-{ev.id}")]
    return {"event": to_jsonable(new_events[0]) if new_events else None,
            "issues": to_jsonable(res.issues), "before": {"totals": to_jsonable(base.totals)}, "after": {"totals": to_jsonable(res.totals)},
            "postings": [to_jsonable({"date": p.date, "event": p.event, "narration": p.narration,
                                      "lines": [{"role": l[0], "debit": l[1], "credit": l[2]} for l in p.lines]})
                         for p in res.postings if p.ref in ("EV-preview", f"EV-{ev.id}")],
            "periods_after": [to_jsonable({k: v for k, v in r.__dict__.items() if k != "detail"}) for r in res.periods
                              if r.period_end >= prev_day(ev.effective_date)][:24]}


# --------------------------------------------------------------------------- queries
def current_run(db: Session, lease: Lease, approved_only: bool = False) -> Optional[CalcRun]:
    stmt = select(CalcRun).where(CalcRun.lease_id == lease.id)
    if approved_only:
        stmt = stmt.where(CalcRun.status.in_(["Approved", "Posted"]))
        return db.scalar(stmt.order_by(CalcRun.run_no.desc()))
    run = db.scalar(stmt.where(CalcRun.is_current == True).order_by(CalcRun.run_no.desc()))  # noqa: E712
    return run or db.scalar(stmt.order_by(CalcRun.run_no.desc()))


def reporting_run(db: Session, lease: Lease) -> Optional[CalcRun]:
    """Run used for reporting: latest approved, else latest draft (flagged as unapproved)."""
    return current_run(db, lease, approved_only=True) or current_run(db, lease)


def lease_dict(db: Session, lease: Lease, full: bool = True) -> dict:
    run = reporting_run(db, lease)
    s = run.summary if run else {}
    init = s.get("initial") or {}
    periods = s.get("periods") or []
    today = date.today()
    cur = [p for p in periods if parse_date(p["period_end"]) <= today]
    last = cur[-1] if cur else (periods[0] if periods and parse_date(periods[0]["period_start"]) <= today else None)
    d = {
        "id": lease.id, "lease_code": lease.lease_code, "status": lease.status, "role": lease.role, "lease_type": lease.lease_type,
        "description": lease.description, "entity_id": lease.entity_id, "entity": lease.entity.name if lease.entity else "",
        "entity_code": lease.entity.code if lease.entity else "",
        "asset_class_id": lease.asset_class_id, "asset_class": lease.asset_class.name if lease.asset_class else "",
        "asset_description": lease.asset_description, "location": lease.location, "business_unit": lease.business_unit,
        "cost_centre": lease.cost_centre, "department": lease.department, "project": lease.project,
        "counterparty_id": lease.counterparty_id, "lessor": lease.counterparty.name if lease.counterparty else "",
        "related_party": bool(lease.counterparty.related_party) if lease.counterparty else False,
        "vendor_id": lease.counterparty.vendor_id if lease.counterparty else "",
        "contract_number": lease.contract_number, "contract_date": lease.contract_date, "commencement_date": lease.commencement_date,
        "availability_date": lease.availability_date, "contract_end": lease.contract_end, "enforceable_end": lease.enforceable_end,
        "enforceable_rationale": lease.enforceable_rationale, "currency": lease.currency,
        "payment_frequency": lease.payment_frequency, "payment_timing": lease.payment_timing,
        "discount_rate_pct": lease.discount_rate_pct, "rate_basis": lease.rate_basis, "rate_source": lease.rate_source,
        "discount_rate_id": lease.discount_rate_id, "useful_life_end": lease.useful_life_end,
        "ownership_transfers": lease.ownership_transfers, "non_lease_expedient": lease.non_lease_expedient,
        "head_lease_id": lease.head_lease_id, "notes": lease.notes, "created_at": lease.created_at, "updated_at": lease.updated_at,
        "calc_status": run.status if run else None, "calc_run_no": run.run_no if run else None,
        "initial_liability": init.get("liability"), "initial_rou": init.get("rou"),
        "liability_now": last.get("liab_close") if last else None, "rou_now": last.get("rou_close") if last else None,
        "term_end": (s.get("term") or {}).get("term_end"), "term_months": (s.get("term") or {}).get("term_months"),
        "flags_count": len(s.get("flags") or []), "issues_count": len(s.get("issues") or []),
        "source_extraction_id": lease.source_extraction_id,
    }
    if s.get("kind") in ("LESSOR", "SUBLEASE"):
        lrows = s.get("rows") or []
        cur_l = [r for r in lrows if parse_date(r["period_end"]) <= today]
        lr = cur_l[-1] if cur_l else None
        d.update({"classification": s.get("classification_final") or s.get("classification"),
                  "classification_initial": s.get("classification"),
                  "net_investment_now": lr.get("ni_close") if lr else None, "accrued_income_now": lr.get("accrued_close") if lr else None,
                  "initial_net_investment": s.get("net_investment") if s.get("classification") == "FINANCE" else None})
    if full:
        a = db.scalar(select(LeaseAssessment).where(LeaseAssessment.lease_id == lease.id))
        d.update({
            "generator_config": lease.generator_config, "policy_overrides": lease.policy_overrides,
            "opening_balance": lease.opening_balance, "lessor_details": lease.lessor_details, "slb_details": lease.slb_details,
            "sublease_details": lease.sublease_details, "tax_settings": lease.tax_settings,
            "options": [{"id": o.id, "kind": o.kind, "holder": o.holder, "exercise_date": o.exercise_date,
                         "extension_end_date": o.extension_end_date, "price": o.price, "reasonably_certain": o.reasonably_certain,
                         "rationale": o.rationale, "description": o.description, "renewal_escalation_pct": o.renewal_escalation_pct,
                         "approval_date": o.approval_date, "last_reassessment_date": o.last_reassessment_date} for o in lease.options],
            "payments": [{"id": p.id, "line_no": p.line_no, "date": p.payment_date, "period_start": p.period_start,
                          "period_end": p.period_end, "lease_amount": p.lease_amount, "non_lease_amount": p.non_lease_amount,
                          "category": p.category, "include_override": p.include_override, "override_reason": p.override_reason,
                          "description": p.description, "source": p.source} for p in lease.payments],
            "costs": [{"id": c.id, "kind": c.kind, "date": c.cost_date, "amount": c.amount, "description": c.description} for c in lease.costs],
            "deposit": ({"id": lease.deposits[0].id, "amount": lease.deposits[0].amount, "payment_date": lease.deposits[0].payment_date,
                         "refund_date": lease.deposits[0].refund_date, "interest_bearing": lease.deposits[0].interest_bearing,
                         "contractual_rate_pct": lease.deposits[0].contractual_rate_pct, "market_rate_pct": lease.deposits[0].market_rate_pct,
                         "treat_difference_as_prepaid_rent": lease.deposits[0].treat_difference_as_prepaid_rent,
                         "notes": lease.deposits[0].notes} if lease.deposits else None),
            "restoration": ({"id": lease.restorations[0].id, "estimated_cost": lease.restorations[0].estimated_cost,
                             "settlement_date": lease.restorations[0].settlement_date,
                             "discount_rate_pct": lease.restorations[0].discount_rate_pct,
                             "recognition_date": lease.restorations[0].recognition_date,
                             "cost_is_current_price": lease.restorations[0].cost_is_current_price,
                             "inflation_pct": lease.restorations[0].inflation_pct, "notes": lease.restorations[0].notes}
                            if lease.restorations else None),
            "assessment": ({k: getattr(a, k) for k in ("identified_asset", "substitution_rights", "economic_benefits", "directs_use",
                                                        "contains_lease", "separate_components", "allocation_method", "exemption",
                                                        "asset_value_when_new", "benefits_on_own", "not_highly_dependent",
                                                        "conclusion", "notes", "assessed_at")} if a else None),
            "events": [{"id": e.id, "event_type": e.event_type, "subtype": e.subtype, "effective_date": e.effective_date,
                        "description": e.description, "details": e.details, "status": e.status, "result": e.result,
                        "approved_at": e.approved_at, "created_at": e.created_at} for e in lease.events],
        })
    return to_jsonable(d)
