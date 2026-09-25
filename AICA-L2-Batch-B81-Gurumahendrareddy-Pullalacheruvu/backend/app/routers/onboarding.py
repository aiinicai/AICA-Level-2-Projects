"""First run, and everything that follows from it.

The first question this application asks is which data to load: the
demonstration company, or your own. That is a deliberate choice rather than a
default, because the two audiences are different — someone evaluating the tool
wants numbers on screen in five seconds, and someone deploying it wants their
own.

After that, set-up is staged. Not because staging is tidy, but because a
forty-field form asking for everything up front does not get finished. Stage 1
is whatever produces a defensible runway number, and nothing more.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from fastapi import (
    APIRouter, Body, Depends, File, Form, HTTPException, Response, UploadFile,
)
from pydantic import BaseModel, Field
from sqlalchemy import func

from app.core.security import get_current_user, require_approver, require_write
from app.database import get_db
from app.models import (
    BankAccount, Bill, Commitment, Customer, Entity, ImportBatch, Invoice,
    LedgerEntry, OnboardingState, Role, StatutoryDue, User, Vendor,
)
from app.routers.deps import get_ctx, log
from app.services import setupimport
from app.services.common import Ctx

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Where am I
# ---------------------------------------------------------------------------
@router.get("/status")
def status(db=Depends(get_db), user: User = Depends(get_current_user)):
    """Answers the only question the router needs: show the app, or the door."""
    entities = db.query(Entity).order_by(Entity.sort_order, Entity.id).all()
    if not entities:
        return {
            "first_run": True,
            "entities": [],
            "can_set_up": user.role in Role.APPROVERS,
            "message": ("Nothing is set up yet. Load the demonstration company to "
                        "look around, or set up your own."),
        }

    states = {s.entity_id: s for s in db.query(OnboardingState).all()}
    out = []
    for e in entities:
        s = states.get(e.id)
        out.append({
            "id": e.id, "name": e.name, "code": e.code,
            "mode": s.mode if s else "own",
            "stage1": bool(s and s.stage1_done), "stage2": bool(s and s.stage2_done),
            "stage3": bool(s and s.stage3_done),
            "dismissed": bool(s and s.dismissed),
        })
    return {"first_run": False, "entities": out,
            "can_set_up": user.role in Role.APPROVERS}


@router.get("/readiness")
def readiness(ctx: Ctx = Depends(get_ctx), user: User = Depends(get_current_user)):
    """What each screen still needs, so a tab can say so instead of showing zero.

    A confident zero is the worst thing a cash tool can display. "₹ 0 receivable"
    and "no invoices entered yet" look identical on a card and mean opposite
    things, so the screens are told which one they are looking at.
    """
    eids = ctx.entity_ids

    def n(model, *filters):
        q = ctx.db.query(func.count(model.id)).filter(model.entity_id.in_(eids))
        for f in filters:
            q = q.filter(f)
        return q.scalar() or 0

    banks = n(BankAccount)
    movement = n(LedgerEntry)
    invoices = n(Invoice, Invoice.outstanding > 0)
    bills = n(Bill, Bill.outstanding > 0)
    statutory = n(StatutoryDue)
    commitments = n(Commitment)

    checks = {
        "bank_accounts": {"have": banks, "needed_for": ["Today", "Liquidity", "Cash Calendar"],
                          "prompt": "Add your bank balances — Setup › Import, or the "
                                    "Bank accounts register."},
        "movement": {"have": movement, "needed_for": ["Runway & Burn", "Today", "Plan vs Actual"],
                     "prompt": "Add three months of receipts and payments — burn cannot "
                               "be computed without them."},
        "invoices": {"have": invoices, "needed_for": ["Money Coming In", "Cash Calendar"],
                     "prompt": "Add your open invoices to turn on ageing, DSO and "
                               "concentration."},
        "bills": {"have": bills, "needed_for": ["Money Going Out", "Cash Calendar"],
                  "prompt": "Add your open bills."},
        "statutory": {"have": statutory, "needed_for": ["Money Going Out"],
                      "prompt": "Add statutory dues — they are first charge on cash."},
        "commitments": {"have": commitments, "needed_for": ["Money Going Out"],
                        "prompt": "Add committed-but-unbilled spend."},
    }

    stage1 = banks > 0 and movement > 0
    stage2 = stage1 and (invoices > 0 or bills > 0) and statutory > 0
    stage3 = stage2 and commitments > 0

    # Keep the stored state in step, so the wizard knows where it left off.
    st = (ctx.db.query(OnboardingState)
          .filter(OnboardingState.entity_id == ctx.entity.id).first())
    if st:
        st.stage1_done, st.stage2_done, st.stage3_done = stage1, stage2, stage3
        if stage3 and not st.completed_at:
            st.completed_at = _now()
        ctx.db.commit()

    blocked = {}
    for key, c in checks.items():
        if not c["have"]:
            for tab in c["needed_for"]:
                blocked.setdefault(tab, []).append(c["prompt"])

    return {
        "checks": checks,
        "stage1": stage1, "stage2": stage2, "stage3": stage3,
        "runway_computable": stage1,
        "tabs_needing_data": blocked,
        "headline": ("Everything the screens need is in place." if stage3 else
                     "Runway is computable. Add open items to turn on the calendar "
                     "and ageing." if stage1 else
                     "Not enough data for a runway figure yet — bank balances and "
                     "three months of movement are what it takes."),
    }


# ---------------------------------------------------------------------------
# Door 1 — the demonstration company
# ---------------------------------------------------------------------------
@router.post("/demo")
def load_demo(confirm: bool = Body(False, embed=True),
              db=Depends(get_db), user: User = Depends(require_approver)):
    """Load Northwind Robotics. Replaces everything — hence the confirmation."""
    if db.query(Entity).count() and not confirm:
        raise HTTPException(409, "There is already data here. Loading the demonstration "
                                 "company replaces all of it. Send confirm=true if that "
                                 "is what you want.")
    from app.seed import seed_all

    # seed_all drops and recreates every table. Anything this session is still
    # holding (the signed-in user, for one) refers to rows that no longer
    # exist, and SQLAlchemy warns about the collision on the next flush. Let go
    # of them first.
    db.expunge_all()
    stats = seed_all(db, wipe=True)
    for e in db.query(Entity).all():
        db.add(OnboardingState(entity_id=e.id, mode="demo", stage1_done=True,
                               stage2_done=True, stage3_done=True,
                               completed_at=_now(), created_by=user.name))
    db.commit()
    return {"loaded": True, "stats": stats,
            "message": ("Northwind Robotics loaded — 18 months of ledger, as at "
                        "31-Aug-2026. Sign-in accounts are unchanged.")}


# ---------------------------------------------------------------------------
# Door 2 — your own company
# ---------------------------------------------------------------------------
class EntityIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    code: str = Field(..., min_length=1, max_length=16)
    currency: str = "INR"
    fx_to_inr: float = 1.0
    min_cash_floor: float = Field(0.0, ge=0)
    books_closed_upto: date | None = None
    tally_company: str | None = None


@router.post("/entity")
def create_entity(body: EntityIn, db=Depends(get_db),
                  user: User = Depends(require_approver)):
    if db.query(Entity).filter(func.lower(Entity.name) == body.name.lower()).first():
        raise HTTPException(409, f"There is already an entity called '{body.name}'.")
    if db.query(Entity).filter(func.lower(Entity.code) == body.code.lower()).first():
        raise HTTPException(409, f"The code '{body.code}' is already in use.")

    e = Entity(name=body.name, code=body.code.upper(), currency=body.currency,
               fx_to_inr=body.fx_to_inr, is_consolidated=False,
               min_cash_floor=body.min_cash_floor,
               books_closed_upto=body.books_closed_upto or date.today(),
               tally_company=body.tally_company,
               sort_order=(db.query(func.count(Entity.id)).scalar() or 0) + 1)
    db.add(e)
    db.flush()
    db.add(OnboardingState(entity_id=e.id, mode="own", created_by=user.name))

    # Definitions are the glossary every argument about a number ends at, so a
    # new entity gets them rather than an empty Setup screen.
    from app.models import Definition
    if not db.query(Definition).count():
        from app.seed import reference as ref
        for d in ref.DEFINITIONS:
            db.add(Definition(term=d["term"], plain_english=d["plain_english"],
                              formula=d.get("formula"), basis_note=d.get("basis_help"),
                              category=d.get("category", "General"),
                              updated_by=user.name))
    db.commit()
    return {"id": e.id, "name": e.name, "code": e.code,
            "message": f"{e.name} created. Next: bring in your figures."}


# ---------------------------------------------------------------------------
# The workbook
# ---------------------------------------------------------------------------
def _xlsx(data: bytes, filename: str) -> Response:
    return Response(content=data,
                    media_type="application/vnd.openxmlformats-officedocument."
                               "spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/template")
def blank_template(user: User = Depends(get_current_user)):
    return _xlsx(setupimport.build_template(), "Cash_Runway_Setup_Template.xlsx")


@router.get("/example")
def worked_example(user: User = Depends(get_current_user)):
    """The same template, filled in with the demonstration company's figures."""
    from app.seed.exampledata import example_rows
    return _xlsx(setupimport.build_template(example_rows()),
                 "Cash_Runway_Setup_EXAMPLE_Northwind.xlsx")


@router.get("/schema")
def schema(user: User = Depends(get_current_user)):
    """What the workbook expects — also what the in-app forms are built from."""
    return {"stages": setupimport.STAGE_LABELS,
            "sheets": [{
                "name": s.name, "stage": s.stage, "title": s.title, "why": s.why,
                "columns": [{"header": c.header, "key": c.key, "kind": c.kind,
                             "required": c.required, "choices": c.choices,
                             "help": c.help} for c in s.cols],
            } for s in setupimport.SHEETS]}


def _encode(parsed: dict) -> str:
    def enc(o):
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        raise TypeError(str(type(o)))
    return json.dumps(parsed, default=enc)


def _decode(raw: str) -> dict:
    out: dict[str, list[dict]] = {}
    for sheet_name, rows in json.loads(raw).items():
        sheet = setupimport.SHEETS_BY_NAME.get(sheet_name)
        date_keys = {c.key for c in sheet.cols if c.kind == "date"} if sheet else set()
        fixed = []
        for r in rows:
            r = dict(r)
            for k in date_keys:
                if isinstance(r.get(k), str):
                    r[k] = date.fromisoformat(r[k])
            fixed.append(r)
        out[sheet_name] = fixed
    return out


@router.post("/validate")
async def validate_upload(file: UploadFile = File(...),
                          ctx: Ctx = Depends(get_ctx),
                          user: User = Depends(require_write)):
    """Read and check the file. Writes the report, not the data."""
    content = await file.read()
    try:
        report = setupimport.validate(content)
    except ValueError as e:
        raise HTTPException(400, str(e))

    parsed = report.pop("parsed")
    batch = ImportBatch(
        entity_id=ctx.entity.id, filename=file.filename or "setup.xlsx",
        sheets=_encode(parsed), rows_accepted=report["accepted"],
        rows_rejected=report["rejected"],
        errors=json.dumps(report["errors"]), committed=False,
        uploaded_by=user.name)
    ctx.db.add(batch)
    ctx.db.commit()

    report["batch_id"] = batch.id
    report["nothing_saved_yet"] = True
    return report


@router.post("/commit/{batch_id}")
def commit_upload(batch_id: int, replace: bool = Body(False, embed=True),
                  ctx: Ctx = Depends(get_ctx), user: User = Depends(require_write)):
    batch = ctx.db.get(ImportBatch, batch_id)
    if not batch or batch.entity_id != ctx.entity.id:
        raise HTTPException(404, "That upload is not on file. Upload the workbook again.")
    if batch.committed:
        raise HTTPException(409, "That upload has already been imported.")

    parsed = _decode(batch.sheets or "{}")
    if replace:
        _clear_entity_data(ctx.db, ctx.entity.id)

    counts = setupimport.commit(ctx.db, ctx.entity, parsed, user.name)
    batch.committed = True

    log(ctx, user, "uploaded", "SetupWorkbook",
        f"Imported {batch.filename} — "
        + ", ".join(f"{v} {k.replace('_', ' ')}" for k, v in counts.items() if v),
        object_id=str(batch.id))
    ctx.db.commit()
    return {"imported": counts,
            "message": "Imported. Every figure carries your name and today's date "
                       "as its source, and shows in the manual entries register."}


class ManualRow(BaseModel):
    sheet: str
    rows: list[dict]


@router.post("/manual")
def manual_entry(body: ManualRow, ctx: Ctx = Depends(get_ctx),
                 user: User = Depends(require_write)):
    """The typed-in path, validated by exactly the same rules as the workbook.

    Two ways in, one set of rules — otherwise the form quietly accepts what the
    upload would have rejected.
    """
    sheet = setupimport.SHEETS_BY_NAME.get(body.sheet)
    if not sheet:
        raise HTTPException(400, f"There is no '{body.sheet}' sheet.")

    accepted, errors = [], []
    for i, raw in enumerate(body.rows, start=1):
        rec, problems = {}, []
        for col in sheet.cols:
            v = raw.get(col.key)
            if col.kind == "date":
                d = setupimport._as_date(v)
                if v not in (None, "") and d is None:
                    problems.append(f"'{col.header}' is not a date")
                rec[col.key] = d
            elif col.kind == "number":
                nv = setupimport._as_number(v)
                if v not in (None, "") and nv is None:
                    problems.append(f"'{col.header}' is not a number")
                rec[col.key] = nv
            elif col.kind == "bool":
                rec[col.key] = bool(setupimport._as_bool(v))
            elif col.kind == "choice":
                s = str(v).strip() if v not in (None, "") else None
                if s and col.choices and s not in col.choices:
                    problems.append(f"'{col.header}' must be one of: {', '.join(col.choices)}")
                rec[col.key] = s
            else:
                rec[col.key] = str(v).strip() if v not in (None, "") else None
            if col.required and rec.get(col.key) in (None, ""):
                problems.append(f"'{col.header}' is required")
        problems.extend(setupimport._row_rules(sheet, rec))
        if problems:
            errors.append({"row": i, "message": "; ".join(problems)})
        else:
            accepted.append(rec)

    if errors:
        raise HTTPException(422, {"detail": "Some rows could not be saved.",
                                  "errors": errors})

    counts = setupimport.commit(ctx.db, ctx.entity, {sheet.name: accepted}, user.name)
    log(ctx, user, "created", sheet.name,
        f"Added {len(accepted)} row(s) to {sheet.name} by hand.")
    ctx.db.commit()
    return {"saved": len(accepted), "counts": counts}


# ---------------------------------------------------------------------------
def _clear_entity_data(db, entity_id: int) -> None:
    """Transactional data only. Users, definitions and settings stay."""
    for model in (LedgerEntry, Invoice, Bill, StatutoryDue, Commitment,
                  BankAccount, Customer, Vendor):
        db.query(model).filter(model.entity_id == entity_id).delete(
            synchronize_session=False)
    db.flush()


@router.post("/reset")
def reset_everything(confirm: str = Body(..., embed=True),
                     db=Depends(get_db), user: User = Depends(require_approver)):
    """Clear all data and go back to the first-run screen.

    Sign-in accounts, definitions and alert rules are kept — this returns the
    application to the state a fresh install is in, not to an unusable one.
    Typing the phrase is the guard: a destructive action reached by one click
    will eventually be reached by an accidental one.
    """
    if confirm.strip().lower() != "start again":
        raise HTTPException(400, "To confirm, type: start again")

    entities = db.query(Entity).all()
    for e in entities:
        _clear_entity_data(db, e.id)
    for model in (OnboardingState, ImportBatch):
        db.query(model).delete(synchronize_session=False)

    # Everything hanging off an entity goes with it.
    from app.models import (
        ActivityLog, Alert, BankStatementImport, BoardPack, Commitment,
        LedgerMapping, Plan, Pseudonym, Scenario, SyncRun, SyncSchedule,
    )
    for model in (ActivityLog, Alert, BoardPack, Plan, Scenario, SyncRun,
                  SyncSchedule, LedgerMapping, Pseudonym, BankStatementImport):
        db.query(model).delete(synchronize_session=False)
    db.query(Entity).delete(synchronize_session=False)
    db.commit()

    return {"reset": True,
            "message": ("Cleared. Sign-in accounts and definitions are unchanged. "
                        "Reload the page and you will be asked what to load.")}


@router.post("/dismiss")
def dismiss(ctx: Ctx = Depends(get_ctx), user: User = Depends(require_write)):
    st = (ctx.db.query(OnboardingState)
          .filter(OnboardingState.entity_id == ctx.entity.id).first())
    if st is None:
        st = OnboardingState(entity_id=ctx.entity.id, mode="own", created_by=user.name)
        ctx.db.add(st)
    st.dismissed = True
    ctx.db.commit()
    return {"dismissed": True}
