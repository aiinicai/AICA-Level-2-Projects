import pytest
from datetime import date
from app.seed import seed_database
from app.models.branch import Branch
from app.services.cash_service import (
    get_salary_advance_bucket,
    calculate_cash_reconciliation_equation,
    create_or_update_cash_reconciliation
)
from app.models.cash_rec import CashReconciliation
from app.models.attendance import Employee, SalaryAdvance
from app.services.attendance_service import replace_salary_advances_for_date

def test_salary_advance_bucket_dates():
    assert get_salary_advance_bucket(date(2026, 4, 3)) == "SALARY_ADV_1_5"
    assert get_salary_advance_bucket(date(2026, 4, 10)) == "SALARY_ADV_6_15"
    assert get_salary_advance_bucket(date(2026, 4, 25)) == "SALARY_ADV_16_31"

def test_cash_reconciliation_equation():
    rec = CashReconciliation(
        opening_balance=10000.0,
        cash_sale=20000.0,
        site_expenses_inv_rec=2000.0,
        site_expenses_inv_not_rec=500.0,
        advance_salary_1_5=3000.0,
        transfer_base_kitchen=5000.0,
        service_charge=200.0,
        actual_closing_balance=19700.0
    )
    # Expected = 10000 + 20000 - 2000 - 500 - 3000 - 5000 + 200 = 19700
    res = calculate_cash_reconciliation_equation(rec)
    assert res["expected_closing_balance"] == 19700.0
    assert res["difference"] == 0.0

def test_image_ocr_date_recognition():
    from app.services.image_ocr_service import parse_image_to_dict
    
    dict1 = parse_image_to_dict(b"", "Register_02_04_2026.png")
    assert dict1["date"] == "2026-04-02"
    
    dict2 = parse_image_to_dict(b"", "Register_15_04_26.jpg")
    assert dict2["date"] == "2026-04-15"

def test_ocr_audit_log_and_structured_rows():
    from app.services.image_ocr_service import parse_image_to_dict
    res = parse_image_to_dict(b"", "Test_Register_Photo.png")
    
    assert "fields" in res
    assert "parsed_rows" in res
    assert "raw_ocr_response" in res
    assert "calculated_total" in res
    assert "total_difference" in res
    
    fields = res["fields"]
    assert "cash" in fields
    assert "status" in fields["cash"]


def test_cash_rec_staff_advance_mapping(db_session):
    seed_database(db=db_session)
    branch = db_session.query(Branch).filter(Branch.code == "NOIDA01").first()
    emp = Employee(branch_id=branch.id, name="Ravi Cook", name_key="RAVI COOK", rank="Cook")
    db_session.add(emp)
    db_session.commit()

    create_or_update_cash_reconciliation(
        db_session,
        branch_id=branch.id,
        rec_date=date(2026, 5, 6),
        data={
            "opening_balance": 2382.0,
            "advance_salary_6_15": 2000.0,
            "actual_closing_balance": 0.0,
        },
    )
    replace_salary_advances_for_date(
        db_session,
        branch.id,
        date(2026, 5, 6),
        [{"employee_id": emp.id, "amount": 2000}],
        source="CASH_REC",
    )
    rows = db_session.query(SalaryAdvance).filter(
        SalaryAdvance.branch_id == branch.id,
        SalaryAdvance.advance_date == date(2026, 5, 6),
    ).all()
    assert len(rows) == 1
    assert rows[0].employee_id == emp.id
    assert rows[0].amount == 2000
    assert rows[0].source == "CASH_REC"


def test_cash_rec_date_change_removes_old_row(db_session):
    seed_database(db=db_session)
    branch = db_session.query(Branch).filter(Branch.code == "NOIDA01").first()
    create_or_update_cash_reconciliation(
        db_session,
        branch_id=branch.id,
        rec_date=date(2026, 8, 23),
        data={"opening_balance": 500.0, "actual_closing_balance": 400.0, "remarks": "move me"},
    )
    from app.services.cash_service import delete_cash_reconciliation
    delete_cash_reconciliation(db_session, branch.id, date(2026, 8, 23))
    create_or_update_cash_reconciliation(
        db_session,
        branch_id=branch.id,
        rec_date=date(2026, 8, 22),
        data={"opening_balance": 500.0, "actual_closing_balance": 400.0, "remarks": "moved"},
    )
    old = db_session.query(CashReconciliation).filter(
        CashReconciliation.branch_id == branch.id,
        CashReconciliation.rec_date == date(2026, 8, 23),
    ).first()
    new = db_session.query(CashReconciliation).filter(
        CashReconciliation.branch_id == branch.id,
        CashReconciliation.rec_date == date(2026, 8, 22),
    ).first()
    assert old is None
    assert new is not None
    assert new.remarks == "moved"

