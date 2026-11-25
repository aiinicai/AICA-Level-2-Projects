"""Read the current data from the database into engine ``Inputs`` and run the forecast."""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import BusinessDefaults
from app.engine.forecast import (BalanceIn, CategoryIn, FacilityIn, Forecast, Inputs, ItemIn, OverrideIn,
                                 compute)
from app.engine.lots import ACTUAL, build_lots
from app.importers.specs import FORECAST_SOURCES
from app.models import (ApprovalStatus, BankAccount, BankBalance, BankFacility, BatchStatus, Category, ImportBatch, LineItem,
                        Override, OverrideAction, Scenario, Snapshot, SourceType, User)
from app.services.settings_service import get_business_settings


def resolve_as_of(db: Session) -> date:
    """Default as-of date: the latest bank balance date (else today)."""
    return db.scalar(select(func.max(BankBalance.as_of_date))) or date.today()


def get_scenario(db: Session, scenario: str | int | Scenario | None = None) -> Scenario:
    if isinstance(scenario, Scenario):
        return scenario
    if isinstance(scenario, int):
        sc = db.get(Scenario, scenario)
    elif scenario:
        sc = db.scalar(select(Scenario).where(func.lower(Scenario.name) == scenario.lower()))
    else:
        sc = db.scalar(select(Scenario).where(Scenario.is_default)) or db.scalar(select(Scenario).limit(1))
    if sc is None:
        raise LookupError(f"scenario {scenario!r} not found")
    return sc


def current_items(db: Session) -> list[ItemIn]:
    rows = db.scalars(
        select(LineItem).join(ImportBatch, ImportBatch.id == LineItem.batch_id)
        .where(ImportBatch.status == BatchStatus.ACCEPTED,
               LineItem.source_type.in_([SourceType(s) for s in FORECAST_SOURCES]),
               LineItem.category_id.is_not(None))
        .order_by(LineItem.planned_date, LineItem.source_type, LineItem.source_key))
    return [ItemIn(li.id, li.source_type.value, li.source_key, li.category_id, li.direction.value,
                   li.planned_date, li.amount, li.counterparty, li.reference, li.project, li.bank_name,
                   (li.currency or "OMR").upper(), li.is_paid, li.risk_flag_imported, li.bill_discounted_imported,
                   li.note) for li in rows]


def active_overrides(db: Session) -> list[OverrideIn]:
    names = dict(db.execute(select(User.id, User.username)).all())
    ext: dict[tuple[str, str], int] = {}     # earlier (revoked) holds = times extended / changed
    for st, key, n in db.execute(
            select(Override.source_type, Override.source_key, func.count())
            .where(Override.action == OverrideAction.HOLD, Override.is_active.is_(False),
                   Override.revoked_at.isnot(None), Override.approval_status != ApprovalStatus.PENDING)
            .group_by(Override.source_type, Override.source_key)):
        ext[(st.value, key)] = n
    out = []
    # active overrides, plus changes waiting for approval (the engine only flags those)
    waiting = (Override.approval_status == ApprovalStatus.PENDING) & Override.revoked_at.is_(None)
    for o in db.scalars(select(Override).where(Override.is_active | waiting).order_by(Override.id)):
        out.append(OverrideIn(o.id, o.source_type.value, o.source_key, o.action.value, o.new_date,
                              o.target_lot_start, o.new_amount, o.new_category_id, o.reason or "",
                              o.approval_status.value, names.get(o.created_by_id, ""), o.created_at,
                              ext.get((o.source_type.value, o.source_key), 0)))
    return out


def load_balances(db: Session, as_of: date, warnings: list[str]) -> list[BalanceIn]:
    out = []
    for acct in db.scalars(select(BankAccount).where(BankAccount.is_active)
                           .order_by(BankAccount.display_order, BankAccount.id)):
        bal = db.scalar(select(BankBalance).where(BankBalance.account_id == acct.id,
                                                  BankBalance.as_of_date <= as_of)
                        .order_by(BankBalance.as_of_date.desc()).limit(1))
        if bal is None:
            warnings.append(f"No balance for {acct.bank_name} {acct.account_name} on or before {as_of:%d-%b-%Y}.")
            continue
        if bal.as_of_date != as_of:
            warnings.append(f"{acct.bank_name} {acct.account_name}: latest balance is from "
                            f"{bal.as_of_date:%d-%b-%Y}, not the as-of date.")
        out.append(BalanceIn(acct.bank_name, acct.account_name, acct.currency, bal.as_of_date, bal.balance,
                             bal.fx_rate_to_base))
    if not out:
        warnings.append("No bank balances entered: the opening balance is zero.")
    return out


def load_facilities(db: Session, as_of: date) -> list[FacilityIn]:
    latest = (select(BankFacility.bank_name, BankFacility.facility_type,
                     func.max(BankFacility.as_of_date).label("d"))
              .where(BankFacility.as_of_date <= as_of)
              .group_by(BankFacility.bank_name, BankFacility.facility_type).subquery())
    rows = db.scalars(select(BankFacility).join(
        latest, (BankFacility.bank_name == latest.c.bank_name)
        & (BankFacility.facility_type == latest.c.facility_type) & (BankFacility.as_of_date == latest.c.d))
        .order_by(BankFacility.bank_name))
    return [FacilityIn(f.bank_name, f.facility_type, f.as_of_date, f.available_amount, f.limit_amount,
                       f.utilised_amount) for f in rows]


def load_inputs(db: Session, *, as_of: date | None = None, scenario: str | int | Scenario | None = None,
                exclude_risk: bool | None = None, use_delay_model: bool | None = None,
                settings: BusinessDefaults | None = None) -> Inputs:
    s = settings or get_business_settings(db)
    as_of = as_of or resolve_as_of(db)
    sc = get_scenario(db, scenario)
    exclude_risk = sc.exclude_risk_adjusted if exclude_risk is None else exclude_risk
    use_delay_model = sc.use_delay_model if use_delay_model is None else use_delay_model
    warnings: list[str] = []
    items = current_items(db)
    cats = [CategoryIn(c.id, c.name, c.direction.value, c.summary_group, c.display_order, c.default_treatment.value,
                       c.is_active) for c in db.scalars(select(Category))]
    hints = {}
    if use_delay_model:
        from app.advisory.delay_model import predict_collection_dates
        hints = predict_collection_dates(db, [i for i in items if i.source == "collections"], as_of)
    locked = {}
    for lt in build_lots(as_of, s):
        if lt.status != ACTUAL:
            continue
        snap = db.scalar(select(Snapshot).where(Snapshot.scenario_id == sc.id,
                                                Snapshot.as_of_date.between(lt.start, lt.end))
                         .order_by(Snapshot.as_of_date.desc()).limit(1))
        col = next((c for c in (snap.grid.get("lots", []) if snap else []) if c["start"] == lt.start.isoformat()),
                   None)
        if col:
            locked[lt.start] = {**col, "snapshot_as_of": snap.as_of_date.isoformat()}
    prev = db.scalar(select(Snapshot).where(Snapshot.scenario_id == sc.id, Snapshot.as_of_date < as_of)
                     .order_by(Snapshot.as_of_date.desc(), Snapshot.id.desc()).limit(1))
    previous = ({"as_of": prev.grid["as_of"], "opening": prev.grid["erp_opening"],
                 "daily_net": prev.grid.get("daily_net", {})} if prev else None)
    return Inputs(as_of=as_of, settings=s, items=items, categories=cats, overrides=active_overrides(db),
                  balances=load_balances(db, as_of, warnings), facilities=load_facilities(db, as_of),
                  scenario=sc.name, scenario_id=sc.id, exclude_risk=exclude_risk, date_hints=hints,
                  locked=locked, previous=previous, warnings=warnings)


def run_forecast(db: Session, **kw) -> Forecast:
    return compute(load_inputs(db, **kw))
