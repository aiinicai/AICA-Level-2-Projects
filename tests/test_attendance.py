from datetime import date

from app.models.branch import Branch
from app.services.attendance_ocr import normalize_attendance_json
from app.services.attendance_service import (
    apply_attendance_upload,
    estimate_gross_salary,
    find_employee,
    get_attendance_matrix,
    list_staff,
    merge_attendance_sheets,
    normalize_employee_name,
    normalize_mark,
    replace_salary_advances_for_date,
    title_case_label,
    update_staff,
    upsert_bank_advance,
)


def test_normalize_employee_name():
    assert normalize_employee_name("Raj Veer") == "RAJ VEER"
    assert normalize_employee_name("  RajVeer! ") == "RAJVEER"
    assert normalize_employee_name("SHUBH Bahadur") == "SHUBH BAHADUR"


def test_title_case_label():
    assert title_case_label("SURESH chef") == "Suresh Chef"
    assert title_case_label("chinese") == "Chinese"
    assert title_case_label("Kitchen") == "Kitchen"
    assert title_case_label("  NEERAJ  ") == "Neeraj"


def test_normalize_mark():
    assert normalize_mark("p") == "P"
    assert normalize_mark("Present") == "P"
    assert normalize_mark("weekly off") == "WO"
    assert normalize_mark("O") == "WO"
    assert normalize_mark("WO") == "WO"
    assert normalize_mark("L") == "L"
    assert normalize_mark("Leave") == "L"
    assert normalize_mark("H") == "A"
    assert normalize_mark("-") == "A"
    assert normalize_mark("") is None


def test_merge_left_and_right_register_pages():
    merged = merge_attendance_sheets([
        {
            "status": "SUCCESS",
            "year": 2026,
            "month": 6,
            "team": "Kitchen Team",
            "employees": [{
                "name": "SURESH",
                "rank": "chef chinese",
                "marks": {"1": "P", "2": "A"},
            }],
        },
        {
            "status": "SUCCESS",
            "year": 2026,
            "month": 6,
            "employees": [{
                "name": "Suresh",
                "marks": {"21": "P", "22": "O"},
                "notes": "2 pending off",
            }, {
                "name": "RajVeer",
                "rank": "Indian",
                "marks": {"26": "P", "27": "P"},
                "total_days": 6,
            }],
        },
    ])
    by_name = {e["name"].upper(): e for e in merged["employees"]}
    assert merged["year"] == 2026 and merged["month"] == 6
    assert by_name["SURESH"]["marks"]["1"] == "P"
    assert by_name["SURESH"]["marks"]["21"] == "P"
    assert by_name["SURESH"]["notes"] == "2 pending off"
    assert "RAJVEER" in by_name
    assert by_name["RAJVEER"]["marks"]["26"] == "P"


def test_apply_adds_missing_staff_and_keeps_earlier_days(db_session):
    branch = Branch(code="ATT1", name="Attendance Test")
    db_session.add(branch)
    db_session.commit()

    first = apply_attendance_upload(db_session, branch.id, 2026, 6, [{
        "name": "SURESH",
        "rank": "chef",
        "team": "Kitchen",
        "marks": {"1": "P", "2": "A"},
    }])
    assert first["added_employees"] == ["Suresh"]
    assert first["marks_written"] == 2

    second = apply_attendance_upload(db_session, branch.id, 2026, 6, [{
        "name": "SURESH",
        "marks": {"8": "P", "9": "O"},
    }, {
        "name": "RajVeer",
        "rank": "Indian",
        "team": "Kitchen",
        "marks": {"26": "P", "27": "P"},
    }])
    assert second["added_employees"] == ["Rajveer"]
    assert find_employee(db_session, branch.id, "suresh") is not None
    assert find_employee(db_session, branch.id, "rajveer") is not None

    matrix = get_attendance_matrix(db_session, branch.id, 2026, 6)
    names = {row["name"]: row for row in matrix["employees"]}
    assert names["Suresh"]["marks"]["1"] == "P"
    assert names["Suresh"]["marks"]["2"] == "A"
    assert names["Suresh"]["marks"]["8"] == "P"
    assert names["Suresh"]["marks"]["9"] == "WO"
    assert names["Rajveer"]["is_new"] is True
    assert names["Rajveer"]["marks"]["26"] == "P"
    assert matrix["summary"]["new_staff"] == 2
    roster = list_staff(db_session, branch.id)
    assert {row["name"] for row in roster} == {"Suresh", "Rajveer"}


def test_fuzzy_name_match(db_session):
    branch = Branch(code="ATT2", name="Attendance Fuzzy")
    db_session.add(branch)
    db_session.commit()
    apply_attendance_upload(db_session, branch.id, 2026, 6, [{
        "name": "SHUBH Bahadur",
        "team": "UT",
        "marks": {"1": "P"},
    }])
    emp = find_employee(db_session, branch.id, "Shubh Bahadur")
    assert emp is not None
    assert emp.name_key == "SHUBH BAHADUR"


def test_normalize_attendance_json_period():
    out = normalize_attendance_json({
        "period": "June 2026",
        "employees": [{
            "name": "RAMU",
            "rank": "UT",
            "marks": {"1": "P", "2": "-", "3": "A"},
        }],
    })
    assert out["year"] == 2026
    assert out["month"] == 6
    assert out["employees"][0]["name"] == "Ramu"
    assert out["employees"][0]["rank"] == "Ut"
    assert out["employees"][0]["marks"] == {"1": "P", "2": "A", "3": "A"}


def test_estimate_gross_salary_from_attendance():
    assert estimate_gross_salary(30000, 20, 30) == 20000.0
    assert estimate_gross_salary(0, 20, 30) == 0.0
    assert estimate_gross_salary(31000, 0, 31) == 0.0


def test_attendance_salary_and_advance(db_session):
    branch = Branch(code="SAL1", name="Salary Test")
    db_session.add(branch)
    db_session.commit()
    apply_attendance_upload(db_session, branch.id, 2026, 6, [{
        "name": "Ankit Chef",
        "rank": "Chinese",
        "team": "Kitchen",
        "marks": {str(d): "P" for d in range(1, 21)} | {"21": "O", "22": "A"},
    }])
    emp = find_employee(db_session, branch.id, "Ankit Chef")
    update_staff(db_session, emp.id, {"monthly_salary": 30000})
    replace_salary_advances_for_date(db_session, branch.id, date(2026, 6, 4), [
        {"employee_id": emp.id, "amount": 2000},
    ])
    matrix = get_attendance_matrix(db_session, branch.id, 2026, 6)
    row = matrix["employees"][0]
    assert row["payable_days"] == 21
    assert row["gross_salary"] == 21000.0
    assert row["advance"] == 2000.0
    assert row["cash_advance"] == 2000.0
    assert row["bank_advance"] == 0.0
    assert row["net_salary"] == 19000.0
    upsert_bank_advance(db_session, emp, 2026, 6, 1500)
    matrix = get_attendance_matrix(db_session, branch.id, 2026, 6)
    row = matrix["employees"][0]
    assert row["cash_advance"] == 2000.0
    assert row["bank_advance"] == 1500.0
    assert row["net_salary"] == 17500.0
    roster = list_staff(db_session, branch.id)
    assert roster[0]["monthly_salary"] == 30000.0


def test_two_leaves_per_month_cap(db_session):
    branch = Branch(code="LEV1", name="Leave Cap")
    db_session.add(branch)
    db_session.commit()
    apply_attendance_upload(db_session, branch.id, 2026, 8, [{
        "name": "Ravi Cook",
        "marks": {"1": "L", "2": "L", "3": "L", "4": "P"},
    }])
    matrix = get_attendance_matrix(db_session, branch.id, 2026, 8)
    row = matrix["employees"][0]
    assert row["marks"]["1"] == "L"
    assert row["marks"]["2"] == "L"
    assert row["marks"]["3"] == "A"
    assert row["leave"] == 2
    assert row["leave_allowed"] == 2
