"""Write endpoints — the manual registers, classifications and annotations.

These are what make the tool honest about its own data: everything that is not
in Tally is entered here by a named person at a recorded time, and shows up in
Setup › Manual Entries Register and in the Activity Log.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.security import require_write
from app.models import (
    BankAccount, Bill, Commitment, CommitmentType, Covenant, Criticality,
    Customer, EmployeeLiability, ExpectedInflow, Facility, FundingRound,
    HiringPlanItem, Invoice, LedgerEntry, NextRaise, StatutoryDue,
    UnbilledWork, User, Vendor,
)
from app.routers.deps import get_ctx, log
from app.services.common import Ctx, fmt_inr

router = APIRouter(prefix="/api", tags=["registers"])


def _apply(obj: Any, payload: BaseModel, user: User) -> list[str]:
    changes = []
    for field, value in payload.model_dump(exclude_unset=True).items():
        if not hasattr(obj, field):
            continue
        before = getattr(obj, field)
        if before != value:
            changes.append(f"{field}: {before} → {value}")
            setattr(obj, field, value)
    if changes and hasattr(obj, "updated_by"):
        obj.updated_by = user.name
    return changes


# ---------------------------------------------------------------------------
# TAB 2B — reclassify a ledger entry as recurring or one-off
# ---------------------------------------------------------------------------
class ReclassifyIn(BaseModel):
    is_one_off: bool
    note: str | None = None


@router.post("/ledger/{entry_id}/reclassify")
def reclassify(entry_id: int, payload: ReclassifyIn, ctx: Ctx = Depends(get_ctx),
               user: User = Depends(require_write)):
    e = ctx.db.get(LedgerEntry, entry_id)
    if not e:
        raise HTTPException(404, "Entry not found")
    before = "one-off" if e.is_one_off else "recurring"
    e.is_one_off = payload.is_one_off
    e.one_off_note = payload.note if payload.is_one_off else None
    e.classified_by = user.name if payload.is_one_off else None
    after = "one-off" if e.is_one_off else "recurring"
    log(ctx, user, "reclassified", "LedgerEntry",
        f"Reclassified '{e.narration or e.voucher_no}' {fmt_inr(abs(e.cash_amount))} "
        f"from {before} to {after}.", str(e.id), before, after)
    ctx.db.commit()
    return {"ok": True, "is_one_off": e.is_one_off, "classified_by": e.classified_by}


# ---------------------------------------------------------------------------
# TAB 4 — receivables annotations
# ---------------------------------------------------------------------------
class InvoiceIn(BaseModel):
    collection_probability: float | None = Field(None, ge=0, le=1)
    promised_date: date | None = None
    promised_amount: float | None = None
    is_disputed: bool | None = None
    dispute_reason: str | None = None
    dispute_raised_on: date | None = None
    dispute_owner: str | None = None
    expected_resolution: date | None = None


@router.patch("/invoices/{invoice_id}")
def update_invoice(invoice_id: int, payload: InvoiceIn, ctx: Ctx = Depends(get_ctx),
                   user: User = Depends(require_write)):
    inv = ctx.db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(404, "Invoice not found")
    changes = _apply(inv, payload, user)
    if payload.is_disputed is True:
        inv.status = "disputed"
        if not inv.dispute_raised_on:
            inv.dispute_raised_on = ctx.today
        if not inv.dispute_owner:
            inv.dispute_owner = user.name
    elif payload.is_disputed is False and inv.status == "disputed":
        inv.status = "open"
    if changes:
        log(ctx, user, "updated", "Invoice",
            f"Updated invoice {inv.invoice_no} — {'; '.join(changes)}.", str(inv.id))
    ctx.db.commit()
    return {"ok": True, "changes": changes}


class CustomerIn(BaseModel):
    credit_terms_days: int | None = None
    owner: str | None = None
    last_contact: date | None = None
    contact_person: str | None = None
    notes: str | None = None


@router.patch("/customers/{customer_id}")
def update_customer(customer_id: int, payload: CustomerIn, ctx: Ctx = Depends(get_ctx),
                    user: User = Depends(require_write)):
    c = ctx.db.get(Customer, customer_id)
    if not c:
        raise HTTPException(404, "Customer not found")
    changes = _apply(c, payload, user)
    if changes:
        log(ctx, user, "updated", "Customer", f"Updated {c.name} — {'; '.join(changes)}.", str(c.id))
    ctx.db.commit()
    return {"ok": True, "changes": changes}


class UnbilledIn(BaseModel):
    customer_id: int
    description: str
    amount: float
    delivered_on: date
    expected_invoice_date: date | None = None
    blocker: str | None = None
    owner: str | None = None


@router.post("/unbilled")
def create_unbilled(payload: UnbilledIn, ctx: Ctx = Depends(get_ctx),
                    user: User = Depends(require_write)):
    u = UnbilledWork(entity_id=ctx.entity.id, **payload.model_dump(),
                     source="manual", created_by=user.name)
    ctx.db.add(u)
    ctx.db.flush()
    log(ctx, user, "created", "UnbilledWork",
        f"Recorded {fmt_inr(payload.amount)} of delivered but uninvoiced work.", str(u.id))
    ctx.db.commit()
    return {"id": u.id}


@router.delete("/unbilled/{item_id}")
def delete_unbilled(item_id: int, ctx: Ctx = Depends(get_ctx),
                    user: User = Depends(require_write)):
    u = ctx.db.get(UnbilledWork, item_id)
    if not u:
        raise HTTPException(404, "Not found")
    ctx.db.delete(u)
    log(ctx, user, "deleted", "UnbilledWork", f"Removed '{u.description}'.", str(item_id))
    ctx.db.commit()
    return {"deleted": True}


class ExpectedInflowIn(BaseModel):
    description: str
    inflow_type: str = "Other"
    expected_on: date
    amount: float
    probability: float = Field(0.5, ge=0, le=1)
    counterparty: str | None = None
    notes: str | None = None
    is_received: bool | None = None


@router.post("/expected-inflows")
def create_inflow(payload: ExpectedInflowIn, ctx: Ctx = Depends(get_ctx),
                  user: User = Depends(require_write)):
    e = ExpectedInflow(entity_id=ctx.entity.id, **payload.model_dump(exclude_none=True),
                       source="manual", created_by=user.name)
    ctx.db.add(e)
    ctx.db.flush()
    log(ctx, user, "created", "ExpectedInflow",
        f"Recorded expected inflow of {fmt_inr(payload.amount)} — {payload.description}.", str(e.id))
    ctx.db.commit()
    return {"id": e.id}


@router.patch("/expected-inflows/{item_id}")
def update_inflow(item_id: int, payload: ExpectedInflowIn, ctx: Ctx = Depends(get_ctx),
                  user: User = Depends(require_write)):
    e = ctx.db.get(ExpectedInflow, item_id)
    if not e:
        raise HTTPException(404, "Not found")
    changes = _apply(e, payload, user)
    if changes:
        log(ctx, user, "updated", "ExpectedInflow", f"Updated '{e.description}'.", str(e.id))
    ctx.db.commit()
    return {"ok": True, "changes": changes}


# ---------------------------------------------------------------------------
# TAB 5 — payables, statutory earmarking, commitments, vendors
# ---------------------------------------------------------------------------
class StatutoryIn(BaseModel):
    earmarked_amount: float | None = None
    funded: bool | None = None
    amount: float | None = None
    due_date: date | None = None
    notes: str | None = None
    status: str | None = None


@router.patch("/statutory/{due_id}")
def update_statutory(due_id: int, payload: StatutoryIn, ctx: Ctx = Depends(get_ctx),
                     user: User = Depends(require_write)):
    s = ctx.db.get(StatutoryDue, due_id)
    if not s:
        raise HTTPException(404, "Statutory due not found")
    before = s.earmarked_amount
    changes = _apply(s, payload, user)
    if payload.earmarked_amount is not None:
        s.funded = s.earmarked_amount >= s.amount
        s.status = "funded" if s.funded else ("overdue" if s.due_date < ctx.today else "pending")
        log(ctx, user, "updated", "StatutoryDue",
            f"Earmarked {fmt_inr(s.earmarked_amount)} against {s.head} {s.period} "
            f"({fmt_inr(s.amount)} due {s.due_date:%d-%b-%y}).", str(s.id),
            fmt_inr(before), fmt_inr(s.earmarked_amount))
    elif changes:
        log(ctx, user, "updated", "StatutoryDue",
            f"Updated {s.head} {s.period} — {'; '.join(changes)}.", str(s.id))
    ctx.db.commit()
    return {"ok": True, "funded": s.funded, "gap": max(s.amount - s.earmarked_amount, 0.0)}


class BillIn(BaseModel):
    deferrable: bool | None = None
    deferral_cost: float | None = None
    penalty_note: str | None = None
    approver: str | None = None
    status: str | None = None
    burn_category: str | None = None


@router.patch("/bills/{bill_id}")
def update_bill(bill_id: int, payload: BillIn, ctx: Ctx = Depends(get_ctx),
                user: User = Depends(require_write)):
    b = ctx.db.get(Bill, bill_id)
    if not b:
        raise HTTPException(404, "Bill not found")
    changes = _apply(b, payload, user)
    if changes:
        log(ctx, user, "updated", "Bill", f"Updated bill {b.bill_no} — {'; '.join(changes)}.", str(b.id))
    ctx.db.commit()
    return {"ok": True, "changes": changes}


class VendorIn(BaseModel):
    criticality: str | None = None
    on_hold: bool | None = None
    hold_reason: str | None = None
    credit_terms_days: int | None = None
    notes: str | None = None


@router.patch("/vendors/{vendor_id}")
def update_vendor(vendor_id: int, payload: VendorIn, ctx: Ctx = Depends(get_ctx),
                  user: User = Depends(require_write)):
    v = ctx.db.get(Vendor, vendor_id)
    if not v:
        raise HTTPException(404, "Vendor not found")
    if payload.criticality and payload.criticality not in Criticality.ALL:
        raise HTTPException(400, f"Criticality must be one of {Criticality.ALL}")
    changes = _apply(v, payload, user)
    if changes:
        log(ctx, user, "updated", "Vendor", f"Updated {v.name} — {'; '.join(changes)}.", str(v.id))
    ctx.db.commit()
    return {"ok": True, "changes": changes}


class CommitmentIn(BaseModel):
    commitment_type: str
    counterparty: str
    description: str | None = None
    total_value: float
    consumed_to_date: float = 0.0
    cancellable: bool = False
    notice_period_days: int = 0
    exit_cost: float = 0.0
    starts_on: date | None = None
    ends_on: date | None = None
    monthly_runrate: float = 0.0
    burn_category: str | None = None
    owner: str | None = None


@router.post("/commitments")
def create_commitment(payload: CommitmentIn, ctx: Ctx = Depends(get_ctx),
                      user: User = Depends(require_write)):
    if payload.commitment_type not in CommitmentType.ALL:
        raise HTTPException(400, f"Type must be one of {CommitmentType.ALL}")
    c = Commitment(entity_id=ctx.entity.id, **payload.model_dump(),
                   source="manual", created_by=user.name)
    ctx.db.add(c)
    ctx.db.flush()
    log(ctx, user, "created", "Commitment",
        f"Recorded {payload.commitment_type} with {payload.counterparty}, "
        f"{fmt_inr(payload.total_value)}.", str(c.id))
    ctx.db.commit()
    return {"id": c.id}


@router.patch("/commitments/{item_id}")
def update_commitment(item_id: int, payload: CommitmentIn, ctx: Ctx = Depends(get_ctx),
                      user: User = Depends(require_write)):
    c = ctx.db.get(Commitment, item_id)
    if not c:
        raise HTTPException(404, "Not found")
    changes = _apply(c, payload, user)
    if changes:
        log(ctx, user, "updated", "Commitment",
            f"Updated commitment with {c.counterparty} — {'; '.join(changes)}.", str(c.id))
    ctx.db.commit()
    return {"ok": True, "changes": changes}


@router.delete("/commitments/{item_id}")
def delete_commitment(item_id: int, ctx: Ctx = Depends(get_ctx),
                      user: User = Depends(require_write)):
    c = ctx.db.get(Commitment, item_id)
    if not c:
        raise HTTPException(404, "Not found")
    ctx.db.delete(c)
    log(ctx, user, "deleted", "Commitment", f"Removed commitment with {c.counterparty}.", str(item_id))
    ctx.db.commit()
    return {"deleted": True}


# ---------------------------------------------------------------------------
# TAB 3A — bank accounts (restriction flags are a judgement, so they are manual)
# ---------------------------------------------------------------------------
class BankAccountIn(BaseModel):
    institution: str | None = None
    account_name: str | None = None
    account_masked: str | None = None
    purpose: str | None = None
    balance: float | None = None
    books_balance: float | None = None
    is_restricted: bool | None = None
    restriction_reason: str | None = None
    maturity_date: date | None = None
    signatory: str | None = None
    approval_limit: float | None = None
    as_on: date | None = None


@router.post("/bank-accounts")
def create_bank_account(payload: BankAccountIn, ctx: Ctx = Depends(get_ctx),
                        user: User = Depends(require_write)):
    if not payload.institution or not payload.account_name:
        raise HTTPException(400, "Institution and account name are required.")
    b = BankAccount(entity_id=ctx.entity.id, **payload.model_dump(exclude_none=True),
                    source="manual", created_by=user.name)
    ctx.db.add(b)
    ctx.db.flush()
    log(ctx, user, "created", "BankAccount",
        f"Added {payload.institution} — {payload.account_name}.", str(b.id))
    ctx.db.commit()
    return {"id": b.id}


@router.patch("/bank-accounts/{account_id}")
def update_bank_account(account_id: int, payload: BankAccountIn,
                        ctx: Ctx = Depends(get_ctx), user: User = Depends(require_write)):
    b = ctx.db.get(BankAccount, account_id)
    if not b:
        raise HTTPException(404, "Account not found")
    if payload.is_restricted and not (payload.restriction_reason or b.restriction_reason):
        raise HTTPException(400, "A restricted balance must carry a reason — otherwise it is "
                                 "treated as available.")
    changes = _apply(b, payload, user)
    if changes:
        log(ctx, user, "updated", "BankAccount",
            f"Updated {b.institution} {b.account_name} — {'; '.join(changes)}.", str(b.id))
    ctx.db.commit()
    return {"ok": True, "changes": changes}


# ---------------------------------------------------------------------------
# TAB 9 — capital registers
# ---------------------------------------------------------------------------
class FacilityIn(BaseModel):
    lender: str | None = None
    facility_type: str | None = None
    sanctioned: float | None = None
    drawn: float | None = None
    interest_rate: float | None = None
    tenure_months: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    next_repayment_date: date | None = None
    next_repayment_amount: float | None = None
    security_given: str | None = None
    is_active: bool | None = None


@router.post("/facilities")
def create_facility(payload: FacilityIn, ctx: Ctx = Depends(get_ctx),
                    user: User = Depends(require_write)):
    if not payload.lender or payload.sanctioned is None:
        raise HTTPException(400, "Lender and sanctioned amount are required.")
    f = Facility(entity_id=ctx.entity.id, **payload.model_dump(exclude_none=True),
                 source="manual", created_by=user.name)
    ctx.db.add(f)
    ctx.db.flush()
    log(ctx, user, "created", "Facility",
        f"Added {payload.lender} {payload.facility_type or 'facility'} of "
        f"{fmt_inr(payload.sanctioned)}.", str(f.id))
    ctx.db.commit()
    return {"id": f.id}


@router.patch("/facilities/{facility_id}")
def update_facility(facility_id: int, payload: FacilityIn, ctx: Ctx = Depends(get_ctx),
                    user: User = Depends(require_write)):
    f = ctx.db.get(Facility, facility_id)
    if not f:
        raise HTTPException(404, "Facility not found")
    changes = _apply(f, payload, user)
    if changes:
        log(ctx, user, "updated", "Facility", f"Updated {f.lender} — {'; '.join(changes)}.", str(f.id))
    ctx.db.commit()
    return {"ok": True, "changes": changes}


class CovenantIn(BaseModel):
    name: str | None = None
    metric_key: str | None = None
    operator: str | None = None
    required_value: float | None = None
    amber_buffer_pct: float | None = None
    test_date: date | None = None
    test_frequency: str | None = None
    facility_id: int | None = None
    notes: str | None = None


@router.post("/covenants")
def create_covenant(payload: CovenantIn, ctx: Ctx = Depends(get_ctx),
                    user: User = Depends(require_write)):
    if not payload.name or not payload.metric_key or payload.required_value is None:
        raise HTTPException(400, "Name, metric and required value are required.")
    c = Covenant(entity_id=ctx.entity.id, **payload.model_dump(exclude_none=True),
                 source="manual", created_by=user.name)
    ctx.db.add(c)
    ctx.db.flush()
    log(ctx, user, "created", "Covenant", f"Added covenant '{payload.name}'.", str(c.id))
    ctx.db.commit()
    return {"id": c.id}


@router.patch("/covenants/{covenant_id}")
def update_covenant(covenant_id: int, payload: CovenantIn, ctx: Ctx = Depends(get_ctx),
                    user: User = Depends(require_write)):
    c = ctx.db.get(Covenant, covenant_id)
    if not c:
        raise HTTPException(404, "Covenant not found")
    changes = _apply(c, payload, user)
    if changes:
        log(ctx, user, "updated", "Covenant", f"Updated '{c.name}' — {'; '.join(changes)}.", str(c.id))
    ctx.db.commit()
    return {"ok": True, "changes": changes}


class NextRaiseIn(BaseModel):
    target_amount: float | None = None
    target_close_date: date | None = None
    lead_time_months: int | None = None
    instrument: str | None = None
    status: str | None = None
    notes: str | None = None


@router.patch("/next-raise")
def update_next_raise(payload: NextRaiseIn, ctx: Ctx = Depends(get_ctx),
                      user: User = Depends(require_write)):
    r = (ctx.db.query(NextRaise)
         .filter(NextRaise.entity_id == ctx.entity.id, NextRaise.is_active.is_(True)).first())
    if not r:
        r = NextRaise(entity_id=ctx.entity.id, target_amount=payload.target_amount or 0,
                      target_close_date=payload.target_close_date or ctx.today,
                      source="manual", created_by=user.name)
        ctx.db.add(r)
    changes = _apply(r, payload, user)
    log(ctx, user, "updated", "NextRaise",
        f"Updated the next raise — {'; '.join(changes) if changes else 'no change'}.")
    ctx.db.commit()
    return {"ok": True, "changes": changes}


class FundingRoundIn(BaseModel):
    round_name: str
    closed_on: date
    amount: float
    instrument: str = "Equity"
    investor: str | None = None
    post_money_valuation: float | None = None
    cash_remaining: float = 0.0
    notes: str | None = None


@router.post("/funding-rounds")
def create_round(payload: FundingRoundIn, ctx: Ctx = Depends(get_ctx),
                 user: User = Depends(require_write)):
    f = FundingRound(entity_id=ctx.entity.id, **payload.model_dump(),
                     source="manual", created_by=user.name)
    ctx.db.add(f)
    ctx.db.flush()
    log(ctx, user, "created", "FundingRound",
        f"Recorded {payload.round_name} of {fmt_inr(payload.amount)}.", str(f.id))
    ctx.db.commit()
    return {"id": f.id}


# ---------------------------------------------------------------------------
# TAB 2C — hiring plan and employee liabilities
# ---------------------------------------------------------------------------
class HiringIn(BaseModel):
    role: str
    function: str
    positions: int = 1
    planned_start: date
    monthly_cost_each: float
    one_time_cost: float = 0.0
    status: str = "planned"
    approved_by: str | None = None
    notes: str | None = None


@router.post("/hiring-plan")
def create_hire(payload: HiringIn, ctx: Ctx = Depends(get_ctx),
                user: User = Depends(require_write)):
    h = HiringPlanItem(entity_id=ctx.entity.id, **payload.model_dump(),
                       source="manual", created_by=user.name)
    ctx.db.add(h)
    ctx.db.flush()
    log(ctx, user, "created", "HiringPlanItem",
        f"Added {payload.positions} × {payload.role} from {payload.planned_start:%b-%y}.", str(h.id))
    ctx.db.commit()
    return {"id": h.id}


@router.patch("/hiring-plan/{item_id}")
def update_hire(item_id: int, payload: HiringIn, ctx: Ctx = Depends(get_ctx),
                user: User = Depends(require_write)):
    h = ctx.db.get(HiringPlanItem, item_id)
    if not h:
        raise HTTPException(404, "Not found")
    changes = _apply(h, payload, user)
    if changes:
        log(ctx, user, "updated", "HiringPlanItem", f"Updated {h.role} — {'; '.join(changes)}.", str(h.id))
    ctx.db.commit()
    return {"ok": True, "changes": changes}


@router.delete("/hiring-plan/{item_id}")
def delete_hire(item_id: int, ctx: Ctx = Depends(get_ctx),
                user: User = Depends(require_write)):
    h = ctx.db.get(HiringPlanItem, item_id)
    if not h:
        raise HTTPException(404, "Not found")
    h.status = "cancelled"
    log(ctx, user, "deleted", "HiringPlanItem", f"Cancelled the {h.role} role.", str(item_id))
    ctx.db.commit()
    return {"cancelled": True}


# ---------------------------------------------------------------------------
# TAB 7 — variance notes
# ---------------------------------------------------------------------------
class VarianceNoteIn(BaseModel):
    plan_id: int
    month: date
    variance_type: str
    driver: str
    owner: str | None = None
    comment: str | None = None
    status: str = "open"
    category: str | None = None
    note_id: int | None = None


@router.post("/variance-notes")
def upsert_note(payload: VarianceNoteIn, ctx: Ctx = Depends(get_ctx),
                user: User = Depends(require_write)):
    from app.services.variance import upsert_variance_note
    try:
        n = upsert_variance_note(
            ctx, plan_id=payload.plan_id, month=payload.month,
            variance_type=payload.variance_type, driver=payload.driver,
            owner=payload.owner, comment=payload.comment, status=payload.status,
            user_name=user.name, category=payload.category, note_id=payload.note_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    log(ctx, user, "updated" if payload.note_id else "created", "VarianceNote",
        f"Explained {payload.month:%b-%y} variance as {payload.variance_type}: "
        f"{payload.driver[:120]}", str(n.id))
    ctx.db.commit()
    return {"id": n.id}


# ---------------------------------------------------------------------------
# Setup › Manual Entries Register (SPEC 12A) — everything not in the books
# ---------------------------------------------------------------------------
@router.get("/manual-entries")
def manual_entries(ctx: Ctx = Depends(get_ctx), user: User = Depends(require_write)):
    """One view of every row a person typed rather than the accounting system
    supplying — with who added it and when."""
    out: list[dict] = []

    def add(kind: str, rows, label, amount, when):
        for r in rows:
            out.append({
                "kind": kind, "id": r.id, "label": label(r), "amount": amount(r),
                "effective_date": when(r).isoformat() if when(r) else None,
                "source": getattr(r, "source", "manual"),
                "created_by": getattr(r, "created_by", None),
                "created_at": (r.created_at.isoformat()
                               if getattr(r, "created_at", None) else None),
                "updated_by": getattr(r, "updated_by", None),
                "updated_at": (r.updated_at.isoformat()
                               if getattr(r, "updated_at", None) else None),
            })

    ids = ctx.entity_ids
    q = ctx.db.query
    add("Commitment", q(Commitment).filter(Commitment.entity_id.in_(ids),
                                           Commitment.source == "manual").all(),
        lambda r: f"{r.commitment_type} — {r.counterparty}",
        lambda r: r.remaining, lambda r: r.ends_on)
    add("Expected inflow", q(ExpectedInflow).filter(ExpectedInflow.entity_id.in_(ids)).all(),
        lambda r: r.description, lambda r: r.amount, lambda r: r.expected_on)
    add("Unbilled work", q(UnbilledWork).filter(UnbilledWork.entity_id.in_(ids)).all(),
        lambda r: r.description, lambda r: r.amount, lambda r: r.delivered_on)
    add("Dispute", q(Invoice).filter(Invoice.entity_id.in_(ids),
                                     Invoice.is_disputed.is_(True)).all(),
        lambda r: f"Disputed invoice {r.invoice_no}", lambda r: r.outstanding,
        lambda r: r.dispute_raised_on)
    add("Bank account", q(BankAccount).filter(BankAccount.entity_id.in_(ids)).all(),
        lambda r: f"{r.institution} — {r.account_name}", lambda r: r.balance, lambda r: r.as_on)
    add("Facility", q(Facility).filter(Facility.entity_id.in_(ids)).all(),
        lambda r: f"{r.lender} — {r.facility_type}", lambda r: r.sanctioned, lambda r: r.end_date)
    add("Covenant", q(Covenant).filter(Covenant.entity_id.in_(ids)).all(),
        lambda r: r.name, lambda r: r.required_value, lambda r: r.test_date)
    add("Funding round", q(FundingRound).filter(FundingRound.entity_id.in_(ids)).all(),
        lambda r: r.round_name, lambda r: r.amount, lambda r: r.closed_on)
    add("Hiring plan", q(HiringPlanItem).filter(HiringPlanItem.entity_id.in_(ids)).all(),
        lambda r: f"{r.positions} × {r.role}",
        lambda r: r.monthly_cost_each * r.positions, lambda r: r.planned_start)
    add("Employee liability", q(EmployeeLiability).filter(
        EmployeeLiability.entity_id.in_(ids)).all(),
        lambda r: "Gratuity, leave and bonus accrual",
        lambda r: r.gratuity_accrued + r.leave_encashment_accrued + r.bonus_accrued,
        lambda r: r.as_on)

    out.sort(key=lambda r: r["updated_at"] or r["created_at"] or "", reverse=True)
    return {
        "rows": out,
        "count": len(out),
        "basis": "Everything on this list was entered by a person, not supplied by the "
                 "accounting system. These are the figures that depend on someone keeping "
                 "them current.",
    }
