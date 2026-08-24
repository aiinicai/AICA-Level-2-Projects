import io
from datetime import date

import openpyxl
from app.seed import seed_database
from app.models.branch import Branch
from app.models.cash_rec import CashReconciliation
from app.models.card_qr_rec import CardQrReconciliation
from app.services.import_service import process_daily_sales_import


def test_daybook_import_posts_cash_and_card_qr(db_session):
    seed_database(db=db_session)
    branch = db_session.query(Branch).filter(Branch.code == "NOIDA01").first()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Date", "Cash Sale", "Credit Card", "Zomato"])
    ws.append([date(2026, 5, 1), 12000, 40870, 5500])
    buf = io.BytesIO()
    wb.save(buf)

    process_daily_sales_import(db_session, buf.getvalue(), "daybook.xlsx", branch.id)

    cash = db_session.query(CashReconciliation).filter(
        CashReconciliation.branch_id == branch.id,
        CashReconciliation.rec_date == date(2026, 5, 1),
    ).first()
    assert cash is not None
    assert cash.cash_sale == 12000

    card = db_session.query(CardQrReconciliation).filter(
        CardQrReconciliation.branch_id == branch.id,
        CardQrReconciliation.sale_date == date(2026, 5, 1),
    ).first()
    assert card is not None
    assert card.card_qr_sales_amount == 40870


def test_manual_daybook_and_card_qr_entry(db_session):
    seed_database(db=db_session)
    branch = db_session.query(Branch).filter(Branch.code == "NOIDA01").first()
    from app.services.daybook_service import save_manual_daybook_entry
    from app.services.card_qr_service import save_manual_card_qr_entry

    row = save_manual_daybook_entry(
        db_session, branch.id, date(2026, 8, 1),
        cash=1000, card_qr=2500, zomato=0, swiggy=0, dineout=0,
    )
    assert row["cash"] == 1000
    assert row["card_qr"] == 2500
    rec = save_manual_card_qr_entry(db_session, branch.id, date(2026, 8, 1), 2500, 2400)
    assert rec.received_amount == 2400
    assert rec.difference == 100
    assert rec.status == "DIFFERENCE"


def test_daybook_date_change_removes_old_row(db_session):
    seed_database(db=db_session)
    branch = db_session.query(Branch).filter(Branch.code == "NOIDA01").first()
    from app.services.daybook_service import save_manual_daybook_entry, get_consolidated_daybook
    from app.models.daily_sales import DailySale

    save_manual_daybook_entry(
        db_session, branch.id, date(2026, 8, 23),
        cash=1500, card_qr=0, zomato=0, swiggy=0, dineout=0,
    )
    save_manual_daybook_entry(
        db_session, branch.id, date(2026, 8, 22),
        cash=1500, card_qr=0, zomato=0, swiggy=0, dineout=0,
        original_branch_id=branch.id,
        original_sale_date=date(2026, 8, 23),
    )
    old = db_session.query(DailySale).filter(
        DailySale.branch_id == branch.id,
        DailySale.sale_date == date(2026, 8, 23),
    ).all()
    new_rows = get_consolidated_daybook(db_session, branch.id, date(2026, 8, 22), date(2026, 8, 22))
    assert old == []
    assert new_rows
    assert new_rows[0]["cash"] == 1500
    cash_old = db_session.query(CashReconciliation).filter(
        CashReconciliation.branch_id == branch.id,
        CashReconciliation.rec_date == date(2026, 8, 23),
    ).first()
    assert cash_old is None


def test_all_branch_daybook_sums_openings(db_session):
    seed_database(db=db_session)
    noida = db_session.query(Branch).filter(Branch.code == "NOIDA01").first()
    rdc = db_session.query(Branch).filter(Branch.code == "RDC01").first()
    from app.services.daybook_service import save_manual_daybook_entry, get_consolidated_daybook
    from app.services.cash_service import create_or_update_cash_reconciliation

    save_manual_daybook_entry(db_session, noida.id, date(2026, 4, 1), cash=1000)
    save_manual_daybook_entry(db_session, rdc.id, date(2026, 4, 1), cash=2500)
    create_or_update_cash_reconciliation(
        db_session, noida.id, date(2026, 4, 1),
        {"opening_balance": 1661.0, "actual_closing_balance": 500.0},
    )
    create_or_update_cash_reconciliation(
        db_session, rdc.id, date(2026, 4, 1),
        {"opening_balance": 1200.0, "actual_closing_balance": 800.0},
    )
    all_rows = get_consolidated_daybook(db_session, None, date(2026, 4, 1), date(2026, 4, 1))
    assert len(all_rows) == 1
    assert all_rows[0]["branch_name"] == "All Branches"
    assert all_rows[0]["is_aggregate"] is True
    assert all_rows[0]["cash"] == 3500
    assert all_rows[0]["cash_balance"] == 2861.0
    one = get_consolidated_daybook(db_session, noida.id, date(2026, 4, 1), date(2026, 4, 1))
    assert len(one) == 1
    assert one[0]["branch_name"] == noida.name
    assert one[0]["cash"] == 1000
