"""Attendance register: match staff by name, upsert daily marks, auto-add new names."""
from __future__ import annotations

import calendar
import difflib
import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.attendance import AttendanceMark, BankAdvance, Employee, SalaryAdvance
from app.models.branch import Branch

VALID_MARKS = ("P", "A", "WO", "L")
MAX_LEAVES_PER_MONTH = 2
_PRESENT_ALIASES = {"P", "PRESENT"}
_WEEKLY_OFF_ALIASES = {"WO", "O", "OFF", "WEEKLYOFF", "WOFF"}
_LEAVE_ALIASES = {"L", "LEAVE", "LEAVES", "CL", "PL"}


def normalize_employee_name(name: str) -> str:
    text = re.sub(r"[^A-Za-z0-9\s]", " ", str(name or ""))
    text = re.sub(r"\s+", " ", text).strip().upper()
    return text


def title_case_label(value: Optional[str]) -> Optional[str]:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return None
    return " ".join(
        (part[:1].upper() + part[1:].lower()) if part else ""
        for part in text.split(" ")
    )


def normalize_mark(value: Any) -> Optional[str]:
    if value is None:
        return None
    raw = str(value).strip().upper()
    if not raw:
        return None
    compact = re.sub(r"[^A-Z]", "", raw)
    if raw in _PRESENT_ALIASES or compact in _PRESENT_ALIASES:
        return "P"
    if raw in _WEEKLY_OFF_ALIASES or compact in _WEEKLY_OFF_ALIASES:
        return "WO"
    if raw in _LEAVE_ALIASES or compact in _LEAVE_ALIASES:
        return "L"
    return "A"


def count_month_leaves(
    db: Session,
    employee_id: int,
    year: int,
    month: int,
    exclude_date: Optional[date] = None,
    exclude_days: Optional[set] = None,
) -> int:
    last = calendar.monthrange(year, month)[1]
    start = date(year, month, 1)
    end = date(year, month, last)
    rows = (
        db.query(AttendanceMark)
        .filter(
            AttendanceMark.employee_id == employee_id,
            AttendanceMark.work_date >= start,
            AttendanceMark.work_date <= end,
            AttendanceMark.mark == "L",
        )
        .all()
    )
    total = 0
    for rec in rows:
        if exclude_date and rec.work_date == exclude_date:
            continue
        if exclude_days and rec.work_date.day in exclude_days:
            continue
        total += 1
    return total


def enforce_leave_quota(
    db: Session,
    employee: Employee,
    work_date: date,
    mark: Optional[str],
    *,
    reject_extra: bool = False,
) -> Tuple[Optional[str], Optional[str]]:
    mark = normalize_mark(mark)
    if mark != "L":
        return mark, None
    current = (
        db.query(AttendanceMark)
        .filter(
            AttendanceMark.employee_id == employee.id,
            AttendanceMark.work_date == work_date,
        )
        .first()
    )
    if current and normalize_mark(current.mark) == "L":
        return "L", None
    used = count_month_leaves(db, employee.id, work_date.year, work_date.month, exclude_date=work_date)
    if used >= MAX_LEAVES_PER_MONTH:
        if reject_extra:
            return None, f"Only {MAX_LEAVES_PER_MONTH} leaves are allowed in a month."
        return "A", None
    return "L", None


def cap_leave_marks(
    marks: Dict[str, Any],
    already_used: int,
) -> Dict[str, str]:
    allowed = max(0, MAX_LEAVES_PER_MONTH - int(already_used or 0))
    used = 0
    out: Dict[str, str] = {}
    for key in sorted(marks.keys(), key=lambda item: int(item) if str(item).isdigit() else 99):
        mark = normalize_mark(marks[key])
        if mark is None:
            continue
        if mark == "L":
            if used >= allowed:
                mark = "A"
            else:
                used += 1
        out[str(int(key))] = mark
    return out


def find_employee(
    db: Session, branch_id: int, name: str
) -> Optional[Employee]:
    key = normalize_employee_name(name)
    if not key:
        return None
    exact = (
        db.query(Employee)
        .filter(Employee.branch_id == branch_id, Employee.name_key == key)
        .first()
    )
    if exact:
        return exact
    roster = db.query(Employee).filter(Employee.branch_id == branch_id).all()
    best: Optional[Employee] = None
    best_ratio = 0.0
    for emp in roster:
        ratio = difflib.SequenceMatcher(None, key, emp.name_key or "").ratio()
        if ratio > best_ratio:
            best, best_ratio = emp, ratio
    if best and best_ratio >= 0.88:
        return best
    return None


def get_or_create_employee(
    db: Session,
    branch_id: int,
    name: str,
    rank: Optional[str] = None,
    team: Optional[str] = None,
    notes: Optional[str] = None,
    seen_on: Optional[date] = None,
    monthly_salary: Optional[float] = None,
) -> Tuple[Employee, bool]:
    display_name = title_case_label(name) or str(name or "").strip()
    display_rank = title_case_label(rank)
    display_team = title_case_label(team)
    emp = find_employee(db, branch_id, name)
    if emp:
        emp.name = display_name or emp.name
        if display_rank:
            emp.rank = display_rank
        if display_team:
            emp.team = display_team
        if notes:
            emp.notes = notes
        if monthly_salary is not None and emp.monthly_salary in (None, 0):
            emp.monthly_salary = float(monthly_salary)
        if seen_on:
            if emp.first_seen_date is None or seen_on < emp.first_seen_date:
                emp.first_seen_date = seen_on
            if emp.last_seen_date is None or seen_on > emp.last_seen_date:
                emp.last_seen_date = seen_on
            if emp.is_active is False and seen_on >= (emp.last_seen_date or seen_on):
                emp.is_active = True
        return emp, False

    emp = Employee(
        branch_id=branch_id,
        name=display_name,
        name_key=normalize_employee_name(name),
        rank=display_rank,
        team=display_team,
        notes=notes,
        monthly_salary=float(monthly_salary) if monthly_salary is not None else None,
        is_active=True,
        first_seen_date=seen_on,
        last_seen_date=seen_on,
    )
    db.add(emp)
    db.flush()
    return emp, True


def estimate_gross_salary(monthly_salary: Optional[float], payable_days: int, days_in_month: int) -> float:
    if not monthly_salary or days_in_month <= 0:
        return 0.0
    return round(float(monthly_salary) * payable_days / days_in_month, 2)


def month_bank_advance_totals(
    db: Session, branch_id: int, year: int, month: int
) -> Dict[int, float]:
    rows = (
        db.query(BankAdvance)
        .filter(
            BankAdvance.branch_id == branch_id,
            BankAdvance.year == year,
            BankAdvance.month == month,
        )
        .all()
    )
    return {rec.employee_id: float(rec.amount or 0) for rec in rows}


def upsert_bank_advance(
    db: Session,
    employee: Employee,
    year: int,
    month: int,
    amount: float,
) -> BankAdvance:
    rec = (
        db.query(BankAdvance)
        .filter(
            BankAdvance.employee_id == employee.id,
            BankAdvance.year == year,
            BankAdvance.month == month,
        )
        .first()
    )
    if not rec:
        rec = BankAdvance(
            employee_id=employee.id,
            branch_id=employee.branch_id,
            year=year,
            month=month,
        )
        db.add(rec)
    rec.amount = round(float(amount or 0), 2)
    rec.branch_id = employee.branch_id
    db.commit()
    db.refresh(rec)
    return rec


def month_advance_totals(
    db: Session, branch_id: int, year: int, month: int
) -> Dict[int, float]:
    last = calendar.monthrange(year, month)[1]
    start = date(year, month, 1)
    end = date(year, month, last)
    rows = (
        db.query(SalaryAdvance)
        .filter(
            SalaryAdvance.branch_id == branch_id,
            SalaryAdvance.advance_date >= start,
            SalaryAdvance.advance_date <= end,
        )
        .all()
    )
    totals: Dict[int, float] = {}
    for rec in rows:
        totals[rec.employee_id] = round(totals.get(rec.employee_id, 0.0) + float(rec.amount or 0), 2)
    return totals


def list_salary_advances_for_date(
    db: Session,
    branch_id: int,
    advance_date: date,
) -> List[Dict[str, Any]]:
    rows = (
        db.query(SalaryAdvance)
        .filter(
            SalaryAdvance.branch_id == branch_id,
            SalaryAdvance.advance_date == advance_date,
        )
        .all()
    )
    return [
        {
            "employee_id": rec.employee_id,
            "employee_name": rec.employee.name if rec.employee else "",
            "amount": float(rec.amount or 0),
        }
        for rec in rows
    ]


def salary_advances_grouped(
    db: Session,
    branch_ids: List[int],
    dates: List[date],
) -> Dict[tuple, List[Dict[str, Any]]]:
    if not branch_ids or not dates:
        return {}
    rows = (
        db.query(SalaryAdvance)
        .filter(
            SalaryAdvance.branch_id.in_(branch_ids),
            SalaryAdvance.advance_date.in_(dates),
        )
        .all()
    )
    grouped: Dict[tuple, List[Dict[str, Any]]] = {}
    for rec in rows:
        key = (rec.branch_id, rec.advance_date)
        grouped.setdefault(key, []).append({
            "employee_id": rec.employee_id,
            "employee_name": rec.employee.name if rec.employee else "",
            "amount": float(rec.amount or 0),
        })
    return grouped


def replace_salary_advances_for_date(
    db: Session,
    branch_id: int,
    advance_date: date,
    splits: List[Dict[str, Any]],
    source: str = "DAYBOOK",
) -> None:
    db.query(SalaryAdvance).filter(
        SalaryAdvance.branch_id == branch_id,
        SalaryAdvance.advance_date == advance_date,
    ).delete(synchronize_session=False)
    for row in splits or []:
        emp_id = int(row.get("employee_id") or 0)
        amount = round(float(row.get("amount") or 0), 2)
        if not emp_id or amount <= 0:
            continue
        emp = db.query(Employee).filter(Employee.id == emp_id).first()
        if not emp:
            continue
        db.add(SalaryAdvance(
            employee_id=emp.id,
            branch_id=branch_id,
            advance_date=advance_date,
            amount=amount,
            source=source or "DAYBOOK",
        ))
    db.commit()


def upsert_mark(
    db: Session,
    employee: Employee,
    work_date: date,
    mark: str,
    raw_mark: Optional[str] = None,
    notes: Optional[str] = None,
) -> AttendanceMark:
    mark = normalize_mark(mark) or "A"
    rec = (
        db.query(AttendanceMark)
        .filter(
            AttendanceMark.employee_id == employee.id,
            AttendanceMark.work_date == work_date,
        )
        .first()
    )
    if rec:
        rec.mark = mark
        rec.raw_mark = raw_mark
        if notes:
            rec.notes = notes
        return rec
    rec = AttendanceMark(
        employee_id=employee.id,
        branch_id=employee.branch_id,
        work_date=work_date,
        mark=mark,
        raw_mark=raw_mark,
        notes=notes,
    )
    db.add(rec)
    return rec


def upload_changes_saved_marks(
    db: Session,
    branch_id: int,
    year: int,
    month: int,
    employees: List[Dict[str, Any]],
) -> bool:
    """True when this upload would change a mark that is already saved."""
    for row in employees or []:
        name = str(row.get("name") or "").strip()
        emp = find_employee(db, branch_id, name)
        if not emp:
            continue
        for key, raw in (row.get("marks") or {}).items():
            try:
                work_date = date(year, month, int(key))
            except (TypeError, ValueError):
                continue
            mark = normalize_mark(raw)
            if not mark:
                continue
            rec = (
                db.query(AttendanceMark)
                .filter(
                    AttendanceMark.employee_id == emp.id,
                    AttendanceMark.work_date == work_date,
                )
                .first()
            )
            if rec and rec.mark != mark:
                return True
    return False


def apply_attendance_upload(
    db: Session,
    branch_id: int,
    year: int,
    month: int,
    employees: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Write only the days present on this sheet. Existing days not in the
    upload stay as they are, so daily/weekly/monthly photos can accumulate.
    New names are created automatically.
    """
    added: List[str] = []
    updated = 0
    marks_written = 0
    first_day = date(year, month, 1)

    for row in employees or []:
        name = str(row.get("name") or "").strip()
        if not name or not normalize_employee_name(name):
            continue
        marks = row.get("marks") or {}
        day_nums = []
        for key, raw in marks.items():
            try:
                day_nums.append(int(key))
            except (TypeError, ValueError):
                continue
        seen_on = first_day
        if day_nums:
            try:
                seen_on = date(year, month, min(max(min(day_nums), 1), 28))
            except ValueError:
                seen_on = first_day
        emp, created = get_or_create_employee(
            db,
            branch_id,
            name,
            rank=row.get("rank"),
            team=row.get("team"),
            notes=row.get("notes"),
            seen_on=seen_on,
        )
        if created:
            added.append(emp.name)
        else:
            updated += 1
        incoming_days = set()
        for key in marks.keys():
            try:
                incoming_days.add(int(key))
            except (TypeError, ValueError):
                continue
        already_used = count_month_leaves(db, emp.id, year, month, exclude_days=incoming_days)
        capped = cap_leave_marks(marks, already_used)
        last_day = None
        for key, mark in capped.items():
            try:
                work_date = date(year, month, int(key))
            except ValueError:
                continue
            upsert_mark(db, emp, work_date, mark, raw_mark=str(marks.get(key, mark)), notes=row.get("notes"))
            marks_written += 1
            last_day = work_date
        if last_day:
            if emp.last_seen_date is None or last_day > emp.last_seen_date:
                emp.last_seen_date = last_day

    db.commit()
    return {
        "added_employees": added,
        "updated_employees": updated,
        "marks_written": marks_written,
        "year": year,
        "month": month,
    }


def merge_attendance_sheets(sheets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Combine left/right register pages or day + week photos of the same month."""
    usable = [s for s in sheets if s and s.get("status") != "ERROR"]
    if not usable:
        return {"status": "ERROR", "error_detail": "No attendance figures could be read"}
    year = next((s.get("year") for s in usable if s.get("year")), None)
    month = next((s.get("month") for s in usable if s.get("month")), None)
    team = next((s.get("team") for s in usable if s.get("team")), None)
    by_key: Dict[str, Dict[str, Any]] = {}
    for sheet in usable:
        if not year and sheet.get("year"):
            year = sheet.get("year")
        if not month and sheet.get("month"):
            month = sheet.get("month")
        if not team and sheet.get("team"):
            team = sheet.get("team")
        for emp in sheet.get("employees") or []:
            key = normalize_employee_name(emp.get("name") or "")
            if not key:
                continue
            current = by_key.setdefault(key, {
                "name": title_case_label(emp.get("name")) or emp.get("name"),
                "rank": title_case_label(emp.get("rank")),
                "team": title_case_label(emp.get("team") or team),
                "notes": emp.get("notes"),
                "total_days": emp.get("total_days"),
                "marks": {},
            })
            if emp.get("rank") and not current.get("rank"):
                current["rank"] = emp.get("rank")
            if emp.get("notes"):
                current["notes"] = emp.get("notes")
            if emp.get("total_days") is not None:
                current["total_days"] = emp.get("total_days")
            for day, mark in (emp.get("marks") or {}).items():
                if normalize_mark(mark) is None:
                    continue
                current["marks"][str(int(day))] = normalize_mark(mark)
    return {
        "status": "SUCCESS",
        "year": year,
        "month": month,
        "team": team,
        "employees": list(by_key.values()),
    }


def get_attendance_matrix(
    db: Session,
    branch_id: int,
    year: int,
    month: int,
) -> Dict[str, Any]:
    last = calendar.monthrange(year, month)[1]
    start = date(year, month, 1)
    end = date(year, month, last)
    employees = (
        db.query(Employee)
        .filter(Employee.branch_id == branch_id)
        .order_by(Employee.team.asc(), Employee.name.asc())
        .all()
    )
    marks = (
        db.query(AttendanceMark)
        .filter(
            AttendanceMark.branch_id == branch_id,
            AttendanceMark.work_date >= start,
            AttendanceMark.work_date <= end,
        )
        .all()
    )
    by_emp: Dict[int, Dict[int, str]] = {}
    for rec in marks:
        by_emp.setdefault(rec.employee_id, {})[rec.work_date.day] = normalize_mark(rec.mark) or "A"

    advances = month_advance_totals(db, branch_id, year, month)
    bank_advances = month_bank_advance_totals(db, branch_id, year, month)
    rows = []
    present = absent = weekly_off = leave = 0
    new_this_month = 0
    for emp in employees:
        day_map = by_emp.get(emp.id) or {}
        if not day_map and emp.is_active is False:
            continue
        counts = {k: 0 for k in VALID_MARKS}
        for mark in day_map.values():
            if mark in counts:
                counts[mark] += 1
        present += counts["P"]
        absent += counts["A"]
        weekly_off += counts["WO"]
        leave += counts["L"]
        is_new = bool(emp.first_seen_date and start <= emp.first_seen_date <= end)
        if is_new:
            new_this_month += 1
        payable_leave = min(counts["L"], MAX_LEAVES_PER_MONTH)
        payable = counts["P"] + counts["WO"] + payable_leave
        monthly = float(emp.monthly_salary or 0)
        gross = estimate_gross_salary(monthly, payable, last)
        cash_advance = float(advances.get(emp.id) or 0)
        bank_advance = float(bank_advances.get(emp.id) or 0)
        rows.append({
            "id": emp.id,
            "name": title_case_label(emp.name) or emp.name,
            "rank": title_case_label(emp.rank),
            "team": title_case_label(emp.team),
            "notes": emp.notes,
            "is_new": is_new,
            "is_active": bool(emp.is_active),
            "marks": {str(d): day_map.get(d) for d in range(1, last + 1)},
            "present": counts["P"],
            "absent": counts["A"],
            "weekly_off": counts["WO"],
            "leave": counts["L"],
            "leave_allowed": MAX_LEAVES_PER_MONTH,
            "off": counts["WO"],
            "holiday": 0,
            "left": 0,
            "payable_days": payable,
            "monthly_salary": monthly,
            "gross_salary": gross,
            "advance": cash_advance,
            "cash_advance": cash_advance,
            "bank_advance": bank_advance,
            "net_salary": round(gross - cash_advance - bank_advance, 2),
        })

    return {
        "year": year,
        "month": month,
        "days": last,
        "employees": rows,
        "summary": {
            "staff": len(rows),
            "new_staff": new_this_month,
            "present": present,
            "absent": absent,
            "weekly_off": weekly_off,
            "leave": leave,
            "leave_allowed": MAX_LEAVES_PER_MONTH,
            "off": weekly_off,
            "holiday": 0,
        },
    }


def list_staff(db: Session, branch_id: Optional[int] = None) -> List[Dict[str, Any]]:
    query = db.query(Employee)
    if branch_id:
        query = query.filter(Employee.branch_id == branch_id)
    rows = query.order_by(Employee.team.asc(), Employee.name.asc()).all()
    branches = {b.id: b.name for b in db.query(Branch).all()}
    return [{
        "id": emp.id,
        "branch_id": emp.branch_id,
        "branch_name": branches.get(emp.branch_id, ""),
        "name": title_case_label(emp.name) or emp.name,
        "rank": title_case_label(emp.rank),
        "team": title_case_label(emp.team),
        "notes": emp.notes,
        "monthly_salary": float(emp.monthly_salary or 0),
        "is_active": bool(emp.is_active),
        "first_seen_date": emp.first_seen_date.isoformat() if emp.first_seen_date else None,
        "last_seen_date": emp.last_seen_date.isoformat() if emp.last_seen_date else None,
    } for emp in rows]


def update_staff(
    db: Session,
    employee_id: int,
    data: Dict[str, Any],
) -> Optional[Employee]:
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        return None
    if data.get("name"):
        emp.name = title_case_label(data.get("name")) or emp.name
        emp.name_key = normalize_employee_name(data.get("name"))
    if "rank" in data:
        emp.rank = title_case_label(data.get("rank"))
    if "team" in data:
        emp.team = title_case_label(data.get("team"))
    if "notes" in data:
        emp.notes = data.get("notes") or None
    if "is_active" in data:
        emp.is_active = bool(data.get("is_active"))
    if data.get("branch_id"):
        emp.branch_id = int(data["branch_id"])
    if "monthly_salary" in data:
        raw = data.get("monthly_salary")
        emp.monthly_salary = float(raw) if raw not in (None, "") else None
    db.commit()
    db.refresh(emp)
    return emp
