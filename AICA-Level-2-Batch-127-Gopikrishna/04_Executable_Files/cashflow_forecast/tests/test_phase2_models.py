from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError

from app.models import (AuditLog, BankAccount, BankBalance, BatchStatus, Category, Direction, ImportBatch,
                        LineItem, Override, OverrideAction, Role, Scenario, Snapshot, SourceType, User)
from app.services.init_db import init_db
from app.services.settings_service import active_roles, get_business_settings, update_business_settings

EXPECTED_TABLES = {
    "user", "app_setting", "bank_account", "bank_balance", "bank_facility", "category", "category_alias",
    "source_default_category", "import_batch", "line_item", "mapping_exception", "collection_history",
    "override", "scenario", "snapshot", "export_log", "audit_log",
}


def _batch(db, src=SourceType.VENDOR_PDC, sha="a" * 64):
    b = ImportBatch(source_type=src, original_filename="pdc.xlsx", stored_filename="x.xlsx", sha256=sha,
                    size_bytes=100, status=BatchStatus.ACCEPTED)
    db.add(b); db.flush()
    return b


def _item(db, batch, key, amount="1000.000", d=date(2026, 12, 5)):
    li = LineItem(batch_id=batch.id, source_type=batch.source_type, source_key=key, row_number=2,
                  direction=Direction.OUTFLOW, counterparty="Vendor 01", reference="CHQ-1",
                  planned_date=d, amount=Decimal(amount), raw={"Voucher No": key, "Amount": amount})
    db.add(li); db.flush()
    return li


def test_all_tables_created(engine):
    assert EXPECTED_TABLES <= set(inspect(engine).get_table_names())


def test_init_db_is_idempotent(engine, db):
    init_db(engine); init_db(engine)
    assert db.scalar(select(func.count()).select_from(Scenario)) == 2
    assert db.scalar(select(Scenario).where(Scenario.is_default)).name == "Base"
    assert db.scalar(select(func.count()).select_from(Category)) == 0  # categories are never seeded


def test_business_settings_seeded_and_validated(db):
    b = get_business_settings(db)
    assert (b.lot_scheme, b.lot_length_days, b.horizon_months, b.base_currency) == ("month_thirds", 10, 3, "OMR")
    assert b.show_month_totals is True
    update_business_settings(db, {"horizon_months": 2})
    assert get_business_settings(db).horizon_months == 2
    with pytest.raises(ValidationError):
        update_business_settings(db, {"horizon_months": 13})
    with pytest.raises(ValidationError):
        update_business_settings(db, {"lot_length_days": 0})
    with pytest.raises(KeyError):
        update_business_settings(db, {"no_such_key": 1})
    assert get_business_settings(db).lot_length_days == 10  # unchanged after the failed update


def test_approver_role_switched_off_by_default(db):
    assert Role.APPROVER not in active_roles(db)
    update_business_settings(db, {"approver_enabled": True})
    assert Role.APPROVER in active_roles(db)


def test_money_stored_as_exact_baisa(db):
    acct = BankAccount(bank_name="Bank A", account_name="Current", currency="OMR")
    usd = BankAccount(bank_name="Bank D", account_name="USD", currency="USD")
    db.add_all([acct, usd]); db.flush()
    db.add_all([
        BankBalance(account_id=acct.id, as_of_date=date(2026, 11, 23), balance=Decimal("182450.250")),
        BankBalance(account_id=usd.id, as_of_date=date(2026, 11, 23), balance=Decimal("40000"),
                    fx_rate_to_base=Decimal("0.3845")),
    ])
    db.commit()
    raw = db.execute(text("SELECT balance, fx_rate_to_base FROM bank_balance ORDER BY id")).all()
    assert raw[0] == (182450250, "1")
    assert raw[1] == (40000000, "0.3845")
    usd_bal = db.scalar(select(BankBalance).where(BankBalance.account_id == usd.id))
    assert usd_bal.balance * usd_bal.fx_rate_to_base == Decimal("15380.000")
    # 0.1 + 0.2 style drift cannot happen: sums are integer sums
    b = _batch(db)
    for i in range(1000):
        _item(db, b, f"PV-{i}", "0.001")
    assert db.scalar(select(func.sum(LineItem.amount))) is not None
    assert db.execute(text("SELECT SUM(amount) FROM line_item")).scalar() == 1000


def test_one_active_override_per_key_and_action(db):
    db.add(Override(source_type=SourceType.VENDOR_PDC, source_key="PV-1", action=OverrideAction.HOLD))
    db.commit()
    db.add(Override(source_type=SourceType.VENDOR_PDC, source_key="PV-1", action=OverrideAction.HOLD))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    first = db.scalar(select(Override))
    first.is_active = False  # revoke -> history kept, a new hold is allowed
    db.add(Override(source_type=SourceType.VENDOR_PDC, source_key="PV-1", action=OverrideAction.HOLD))
    db.commit()
    assert db.scalar(select(func.count()).select_from(Override)) == 2


def test_hold_with_honouring_date_partial_and_extension_history(db):
    # partial hold of 4,000 out of the cheque, re-presented on 15 Dec
    h1 = Override(source_type=SourceType.VENDOR_PDC, source_key="PV-9", action=OverrideAction.HOLD,
                  new_date=date(2026, 12, 15), new_amount=Decimal("4000"), reason="Await delivery")
    db.add(h1); db.commit()
    # extension: old hold revoked (kept), new hold with a later date
    h1.is_active = False
    db.add(Override(source_type=SourceType.VENDOR_PDC, source_key="PV-9", action=OverrideAction.HOLD,
                    new_date=date(2027, 1, 5), new_amount=Decimal("4000"), reason="Extended"))
    # open-ended hold on another cheque: no date
    db.add(Override(source_type=SourceType.VENDOR_PDC, source_key="PV-10", action=OverrideAction.HOLD))
    db.commit()
    hist = db.scalars(select(Override).where(Override.source_key == "PV-9").order_by(Override.id)).all()
    assert [(o.is_active, o.new_date) for o in hist] == [(False, date(2026, 12, 15)), (True, date(2027, 1, 5))]
    db.add(Override(source_type=SourceType.VENDOR_PDC, source_key="PV-11", action=OverrideAction.HOLD,
                    new_amount=Decimal("0")))
    with pytest.raises(IntegrityError):
        db.commit()


@pytest.mark.parametrize("action", [OverrideAction.DEFER, OverrideAction.REDATE, OverrideAction.REDUCE,
                                    OverrideAction.RECATEGORISE])
def test_override_requires_its_fields(db, action):
    db.add(Override(source_type=SourceType.VENDOR_PDC, source_key="PV-2", action=action))
    with pytest.raises(IntegrityError):
        db.commit()


def test_reupload_keeps_overrides(db):
    b1 = _batch(db, sha="1" * 64)
    _item(db, b1, "PV-100", "5000.000")
    db.add(Override(source_type=SourceType.VENDOR_PDC, source_key="PV-100", action=OverrideAction.DEFER,
                    target_lot_start=date(2026, 12, 11), reason="Vendor agreed"))
    db.commit()

    # next day: same file uploaded again -> new batch, old one superseded and even deleted
    b2 = _batch(db, sha="1" * 64)
    _item(db, b2, "PV-100", "5000.000")
    b1.status = BatchStatus.SUPERSEDED
    db.delete(b1)
    db.commit()

    joined = db.execute(
        select(LineItem.source_key, Override.action, Override.target_lot_start)
        .join(Override, (Override.source_type == LineItem.source_type) & (Override.source_key == LineItem.source_key))
        .where(LineItem.batch_id == b2.id, Override.is_active)
    ).all()
    assert joined == [("PV-100", OverrideAction.DEFER, date(2026, 12, 11))]


def test_line_item_keeps_raw_row(db):
    b = _batch(db)
    li = _item(db, b, "PV-7")
    db.commit()
    assert db.get(LineItem, li.id).raw == {"Voucher No": "PV-7", "Amount": "1000.000"}


def test_audit_survives_user_deletion(db):
    u = User(username="preparer1", password_hash="x", role=Role.PREPARER)
    db.add(u); db.flush()
    db.add(AuditLog(user_id=u.id, username=u.username, action="override.create", entity="override",
                    entity_key="vendor_pdc:PV-1", after={"action": "hold"}))
    db.commit()
    db.delete(u); db.commit()
    row = db.scalar(select(AuditLog))
    assert (row.user_id, row.username) == (None, "preparer1")


def test_one_snapshot_per_day_and_scenario(db):
    sc = db.scalar(select(Scenario).where(Scenario.is_default))
    kw = dict(snapshot_date=date(2026, 11, 23), as_of_date=date(2026, 11, 23), scenario_id=sc.id,
              grid={"lots": []}, content_sha256="0" * 64)
    db.add(Snapshot(**kw)); db.commit()
    db.add(Snapshot(**kw))
    with pytest.raises(IntegrityError):
        db.commit()


def test_healthz_reads_settings_from_db():
    from fastapi.testclient import TestClient

    from app.main import create_app

    body = TestClient(create_app()).get("/healthz").json()
    assert body["business_defaults"]["grid_start"] == "current_lot"
