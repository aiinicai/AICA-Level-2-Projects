"""Creates the demo organisation described in the project plan (Section 6):
19 users across Executive, Finance, IT, HR, Sales, Operations, matching the
4-level hierarchy, including one ON_NOTICE example. Runs once, automatically,
the first time the app starts against an empty database.
"""
import datetime as dt
import random
from sqlalchemy.orm import Session
from . import models
from .auth import hash_password

DEFAULT_PASSWORD = "Welcome@123"

DEPARTMENTS = ["Executive", "Finance", "IT", "HR", "Sales", "Operations"]

# (code, name, role, dept, designation, doj, manager_code, extra)
PEOPLE = [
    ("EMP-0001", "You (Founder/CEO)", models.ROLE_CEO, "Executive", "Chief Executive Officer", "2018-01-01", None, {}),
    ("EMP-0002", "Aditi Sharma", models.ROLE_DEPT_ADMIN, "Finance", "Finance Head", "2019-03-10", "EMP-0001", {}),
    ("EMP-0003", "Rohan Mehta", models.ROLE_DEPT_ADMIN, "IT", "IT Head", "2019-06-15", "EMP-0001", {}),
    ("EMP-0004", "Priya Nair", models.ROLE_DEPT_ADMIN, "HR", "HR Head", "2019-01-20", "EMP-0001", {}),
    ("EMP-0005", "Karan Verma", models.ROLE_DEPT_ADMIN, "Sales", "Sales Head", "2020-02-01", "EMP-0001", {}),
    ("EMP-0006", "Sneha Kulkarni", models.ROLE_DEPT_ADMIN, "Operations", "Operations Head", "2020-05-11", "EMP-0001", {}),
    ("EMP-0007", "Vikram Rao", models.ROLE_MANAGER, "Finance", "Finance Manager", "2020-07-01", "EMP-0002", {}),
    ("EMP-0008", "Neha Joshi", models.ROLE_MANAGER, "IT", "IT Manager", "2020-08-14", "EMP-0003", {}),
    ("EMP-0009", "Arjun Malhotra", models.ROLE_MANAGER, "HR", "HR Manager", "2021-01-05", "EMP-0004", {}),
    ("EMP-0010", "Divya Iyer", models.ROLE_MANAGER, "Sales", "Sales Manager", "2021-03-19", "EMP-0005", {}),
    ("EMP-0011", "Rahul Singh", models.ROLE_EMPLOYEE, "Finance", "Finance Executive", "2022-01-10", "EMP-0007", {}),
    ("EMP-0012", "Simran Kaur", models.ROLE_EMPLOYEE, "Finance", "Accounts Executive", "2022-06-20", "EMP-0007", {}),
    ("EMP-0013", "Amit Patel", models.ROLE_EMPLOYEE, "IT", "Software Engineer", "2021-11-01", "EMP-0008", {}),
    ("EMP-0014", "Sana Khan", models.ROLE_EMPLOYEE, "IT", "QA Engineer", "2022-09-12", "EMP-0008",
        {"employment_status": "ON_NOTICE", "resignation_date": "2026-08-15", "notice_period_days": 30,
         "last_working_day": "2026-09-14", "resignation_reason": "Relocating to another city"}),
    ("EMP-0015", "Ishaan Kapoor", models.ROLE_EMPLOYEE, "HR", "HR Executive", "2022-04-18", "EMP-0009", {}),
    ("EMP-0016", "Meera Pillai", models.ROLE_EMPLOYEE, "HR", "Talent Acquisition Executive", "2023-02-02", "EMP-0009", {}),
    ("EMP-0017", "Aryan Chawla", models.ROLE_EMPLOYEE, "Sales", "Sales Executive", "2022-07-25", "EMP-0010", {}),
    ("EMP-0018", "Riya Bhatt", models.ROLE_EMPLOYEE, "Sales", "Business Development Executive", "2023-05-09", "EMP-0010", {}),
    ("EMP-0019", "Yash Deshmukh", models.ROLE_EMPLOYEE, "Operations", "Operations Executive", "2022-10-03", "EMP-0006", {}),
]

LEAVE_TYPES = [
    ("Casual Leave", 12), ("Sick Leave", 8), ("Privilege/Earned Leave", 15), ("Unpaid Leave", 0),
]


def _d(s):
    return dt.datetime.strptime(s, "%Y-%m-%d").date() if s else None


def run_seed(db: Session):
    dept_map = {}
    for name in DEPARTMENTS:
        dep = models.Department(name=name)
        db.add(dep)
        db.flush()
        dept_map[name] = dep.id

    for lt_name, days in LEAVE_TYPES:
        db.add(models.LeaveType(name=lt_name, default_annual_days=days))
    db.flush()

    code_to_id = {}
    # pass 1: create users without manager link
    for code, name, role, dept, designation, doj, mgr_code, extra in PEOPLE:
        u = models.User(
            employee_code=code,
            name=name,
            email=f"{code.lower()}@company.local",
            password_hash=hash_password(DEFAULT_PASSWORD),
            must_change_password=True,
            role=role,
            department_id=dept_map[dept],
            designation=designation,
            date_of_joining=_d(doj),
            employment_status=extra.get("employment_status", "ACTIVE"),
            resignation_date=_d(extra.get("resignation_date")),
            notice_period_days=extra.get("notice_period_days"),
            last_working_day=_d(extra.get("last_working_day")),
            resignation_reason=extra.get("resignation_reason"),
        )
        db.add(u)
        db.flush()
        code_to_id[code] = u.id

    # pass 2: wire up manager_id
    for code, name, role, dept, designation, doj, mgr_code, extra in PEOPLE:
        if mgr_code:
            u = db.query(models.User).filter_by(employee_code=code).first()
            u.manager_id = code_to_id[mgr_code]

    db.commit()

    _seed_activity(db)


# ---------------------------------------------------------------------------
# Rich demo activity for the last 20 days: attendance, leave, tasks (self and
# assigned, with query/comment threads), meetings and pending actions -
# covering every status/type combination so the app is fully explorable
# right after first launch.
# ---------------------------------------------------------------------------

TASK_TITLES = [
    "Prepare monthly report", "Follow up with vendor", "Update client presentation",
    "Review budget numbers", "Fix onboarding checklist", "Draft policy update",
    "Reconcile expense claims", "Prepare interview questions", "Update asset register",
    "Clean up shared drive", "Test new process", "Prepare training material",
    "Review pull request", "Update project tracker", "Prepare invoice", "Draft email to stakeholders",
]
PENDING_TITLES = [
    "Get sign-off from CEO", "Chase pending invoice", "Collect feedback from team",
    "Confirm meeting room booking", "Await IT approval", "Follow up on offer letter",
    "Waiting on legal review", "Chase signed contract copy",
]
MEETING_TITLES = [
    "Weekly sync", "Budget planning meeting", "1:1 catch-up",
    "Sprint planning", "Quarterly review", "Cross-team alignment", "Team standup",
]
CLIENT_MEETING_TITLES = [
    "Client review call - Acme Corp", "Client onboarding - Globex Ltd",
    "Client review call - Initech", "Renewal discussion - Umbrella Inc",
    "Client QBR - Stark Industries", "Client escalation call - Wayne Enterprises",
    "New client kickoff - Wonka Industries",
]
QUERY_MESSAGES = [
    "Could you clarify the expected format for this?",
    "Do you want this shared with the whole team or just leadership?",
    "What's the deadline flexibility on this one?",
    "Should this include last quarter's numbers too?",
]
REPLY_MESSAGES = [
    "Please keep it in the standard template, thanks.",
    "Just leadership for now, I'll circulate after review.",
    "End of week is fine if needed, but try Friday morning.",
    "Yes, include the last quarter for comparison.",
]


def _seed_activity(db: Session, days_back: int = 20, days_fwd: int = 14):
    rng = random.Random(42)
    today = dt.date.today()
    users = db.query(models.User).order_by(models.User.id).all()
    leave_types = db.query(models.LeaveType).all()

    for u in users:
        # ---- Attendance: last `days_back` days through today, weekends = HOLIDAY.
        # Today itself is always marked (only a rare "not marked" elsewhere in the window). ----
        leave_block_start = rng.randint(2, days_back - 3)
        leave_block_len = rng.choice([1, 1, 2, 3])
        for offset in range(days_back, -1, -1):
            day = today - dt.timedelta(days=offset)
            if day.weekday() >= 5:
                status = "HOLIDAY"
            elif leave_block_start <= offset < leave_block_start + leave_block_len:
                status = "LEAVE"
            else:
                roll = rng.random()
                if roll < 0.55:
                    status = "WFO"
                elif roll < 0.85:
                    status = "WFH"
                elif roll < 0.93:
                    status = "HALF_DAY"
                elif offset == 0:
                    status = "WFO"  # today is always marked, for a live-looking demo
                else:
                    continue  # not marked, to exercise the "Not marked" rule
            db.add(models.Attendance(user_id=u.id, date=day, status=status, raw_prompt_text="[demo seed data]"))

        # ---- Leave requests: past approved block, a rejected one, and 1-2 upcoming (pending/approved) ----
        if leave_types:
            lt = rng.choice(leave_types)
            block_start_date = today - dt.timedelta(days=leave_block_start)
            block_end_date = block_start_date + dt.timedelta(days=leave_block_len - 1)
            db.add(models.LeaveRequest(
                user_id=u.id, leave_type_id=lt.id, start_date=block_start_date, end_date=block_end_date,
                reason="Personal work", status="APPROVED", approver_id=u.manager_id or u.id,
                raw_prompt_text="[demo seed data]",
            ))

            for _ in range(rng.choice([1, 1, 2])):
                future_start = today + dt.timedelta(days=rng.randint(2, days_fwd))
                db.add(models.LeaveRequest(
                    user_id=u.id, leave_type_id=rng.choice(leave_types).id,
                    start_date=future_start, end_date=future_start + dt.timedelta(days=rng.choice([0, 1, 2])),
                    reason="Planned leave", status=rng.choice(["PENDING", "PENDING", "APPROVED"]),
                    raw_prompt_text="[demo seed data]",
                    approver_id=(u.manager_id or u.id) if rng.random() < 0.4 else None,
                ))

            if rng.random() < 0.3:
                past_start = today - dt.timedelta(days=rng.randint(4, days_back))
                db.add(models.LeaveRequest(
                    user_id=u.id, leave_type_id=rng.choice(leave_types).id,
                    start_date=past_start, end_date=past_start,
                    reason="Requested at short notice", status="REJECTED",
                    approver_id=u.manager_id or u.id, raw_prompt_text="[demo seed data]",
                ))

        # ---- Self-created tasks/pending actions spanning past 20 days through the next two weeks ----
        for _ in range(rng.choice([2, 3, 4])):
            due = today + dt.timedelta(days=rng.randint(-days_back, days_fwd))
            is_future = due >= today
            db.add(models.CalendarEvent(
                owner_id=u.id, event_type=rng.choice(["TASK", "PENDING_ACTION"]),
                title=rng.choice(TASK_TITLES if rng.random() < 0.7 else PENDING_TITLES),
                start_date=due, priority=rng.choice(["LOW", "MEDIUM", "HIGH", "URGENT"]),
                status=rng.choice(["OPEN", "IN_PROGRESS"]) if is_future else rng.choice(["OPEN", "IN_PROGRESS", "DONE"]),
                raw_prompt_text="[demo seed data]",
            ))
        # guarantee something due today for a live-looking dashboard
        db.add(models.CalendarEvent(
            owner_id=u.id, event_type="TASK", title=rng.choice(TASK_TITLES),
            start_date=today, priority=rng.choice(["MEDIUM", "HIGH"]), status="OPEN",
            raw_prompt_text="[demo seed data]",
        ))

        # ---- Meetings: a few in the past, and guaranteed upcoming ones (incl. client calls) ----
        for _ in range(rng.choice([1, 2])):
            mdate = today - dt.timedelta(days=rng.randint(1, 10))
            db.add(models.CalendarEvent(
                owner_id=u.id, event_type="MEETING", title=rng.choice(MEETING_TITLES),
                start_date=mdate, start_time=rng.choice(["09:30", "11:00", "14:00", "15:30", "17:00"]),
                priority="MEDIUM", status="DONE", raw_prompt_text="[demo seed data]",
            ))
        for _ in range(rng.choice([2, 3])):
            mdate = today + dt.timedelta(days=rng.randint(0, days_fwd))
            title = rng.choice(CLIENT_MEETING_TITLES) if rng.random() < 0.35 else rng.choice(MEETING_TITLES)
            db.add(models.CalendarEvent(
                owner_id=u.id, event_type="MEETING", title=title,
                start_date=mdate, start_time=rng.choice(["09:30", "11:00", "14:00", "15:30", "17:00"]),
                priority=rng.choice(["MEDIUM", "HIGH"]), status="OPEN", raw_prompt_text="[demo seed data]",
            ))

    db.flush()

    # ---- Manager-assigned tasks (past and upcoming), some with a query/reply thread ----
    for u in users:
        if not u.manager_id:
            continue
        for _ in range(rng.choice([1, 2, 2, 3])):
            due = today + dt.timedelta(days=rng.randint(-10, days_fwd))
            is_future = due >= today
            status = rng.choice(["OPEN", "IN_PROGRESS"]) if is_future else rng.choice(["OPEN", "IN_PROGRESS", "IN_PROGRESS", "DONE"])
            ev = models.CalendarEvent(
                owner_id=u.id, assigned_by_id=u.manager_id, event_type="TASK",
                title=rng.choice(TASK_TITLES), start_date=due,
                priority=rng.choice(["LOW", "MEDIUM", "HIGH", "URGENT"]), status=status,
                raw_prompt_text="[demo seed data - assigned]",
            )
            db.add(ev)
            db.flush()
            if rng.random() < 0.4:
                db.add(models.TaskComment(
                    event_id=ev.id, author_id=u.id, comment_type="QUERY",
                    message=rng.choice(QUERY_MESSAGES),
                    created_at=dt.datetime.utcnow() - dt.timedelta(days=rng.randint(0, 3)),
                ))
                if rng.random() < 0.6:
                    db.add(models.TaskComment(
                        event_id=ev.id, author_id=u.manager_id, comment_type="COMMENT",
                        message=rng.choice(REPLY_MESSAGES),
                        created_at=dt.datetime.utcnow() - dt.timedelta(hours=rng.randint(1, 48)),
                    ))

    # ---- A couple of company-wide/client meetings owned by the CEO, visible today and this week ----
    ceo = next((u for u in users if u.role == models.ROLE_CEO), None)
    if ceo:
        db.add(models.CalendarEvent(
            owner_id=ceo.id, event_type="MEETING", title="All-hands team meeting",
            start_date=today, start_time="16:00", priority="MEDIUM", status="OPEN",
            raw_prompt_text="[demo seed data]",
        ))
        for i, title in enumerate(rng.sample(CLIENT_MEETING_TITLES, 2)):
            db.add(models.CalendarEvent(
                owner_id=ceo.id, event_type="MEETING", title=title,
                start_date=today + dt.timedelta(days=1 + i * 2), start_time="15:00",
                priority="HIGH", status="OPEN", raw_prompt_text="[demo seed data]",
            ))

    db.commit()
