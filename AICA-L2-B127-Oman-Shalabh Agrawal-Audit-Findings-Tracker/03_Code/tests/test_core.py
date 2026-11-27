"""
Automatic tests for the core logic of the Audit Findings Tracker.

Run from the 03_Code folder:

    python tests/test_core.py

It uses a throw-away database file, sends no real e-mail, and needs no Streamlit.
At the end it prints PASS / FAIL for every test and a summary line.
Optional: add  --report results.txt  to also save the results in a text file.
"""

import os
import sys
import tempfile
import traceback
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["EMAIL_MODE"] = "log"
for _name in ("TEST_EMAIL_OVERRIDE", "DATABASE_URL", "ESCALATION_ENABLED"):
    os.environ.pop(_name, None)

import pandas as pd  # noqa: E402

import app  # noqa: E402

TODAY = date(2026, 11, 27)
ADMIN = {"username": "Audit Admin", "role": app.ROLE_ADMIN, "department": None, "email": "audit.admin@example.com"}
MGMT = {"username": "Management", "role": app.ROLE_MGMT, "department": None, "email": "management@example.com"}


def new_db():
    handle, path = tempfile.mkstemp(suffix=".db")
    os.close(handle)
    db = app.Database(url="", sqlite_path=path)
    app.init_db(db)
    return db


def owner(db, username):
    return app.authenticate(db, username, "Test@123")


def finding(serial, dept="Credit", risk="High", target=TODAY - timedelta(days=100), heading="Test finding"):
    return {"serial_no": str(serial), "year_reported": "2025", "source": "In-house", "quarter": "Q1",
            "report_name": "Test report", "department": dept, "observation_ref": f"OBS-{serial}",
            "heading": heading, "detailed_observation": "d", "risk_implication": "r", "recommendation": "rec",
            "initial_management_response": "ok", "risk_level": risk, "original_target_date": target}


def add(db, serial, **kw):
    return app.add_finding(db, ADMIN, finding(serial, **kw))


def expect_error(exc_type, func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except exc_type:
        return
    raise AssertionError(f"Expected {exc_type.__name__} but nothing was raised")


# --------------------------------------------------------------------------- tests

def test_users_are_created():
    db = new_db()
    users = db.fetch("SELECT * FROM users")
    assert len(users) == 30, len(users)
    names = {u["username"] for u in users}
    assert "Credit 1" in names and "Credit 2" in names and "Risk 1" in names and "Risk 2" in names
    assert "Compliance, Recovery and Legal 1" in names and "Branch 5 2" in names
    for dept in app.DEPARTMENTS:
        owners = [u for u in users if u["department"] == dept and u["role"] == app.ROLE_OWNER]
        assert len(owners) == 2, dept


def test_login():
    db = new_db()
    user = app.authenticate(db, "Credit 1", "Test@123")
    assert user and user["role"] == app.ROLE_OWNER and user["department"] == "Credit"
    assert app.authenticate(db, "credit 1", "Test@123")["username"] == "Credit 1"
    assert app.authenticate(db, "Compliance Recovery and Legal 2", "Test@123")["department"] == "Compliance, Recovery and Legal"
    assert app.authenticate(db, "Credit 1", "wrong") is None
    assert app.authenticate(db, "Nobody", "Test@123") is None
    assert app.authenticate(db, "", "") is None
    assert app.authenticate(db, "Audit Admin", "Test@123")["role"] == app.ROLE_ADMIN
    stored = db.fetch("SELECT password_hash FROM users WHERE username = 'Credit 1'")[0]["password_hash"]
    assert "Test@123" not in stored, "Passwords must be stored hashed"


def test_import_valid_and_invalid_rows():
    db = new_db()
    good = {c: "x" for c in app.MASTER_COLUMNS}

    def row(serial, **over):
        r = dict(good)
        r.update({"Serial number": serial, "Year reported": 2025, "In-house or external auditor": "In-house",
                  "Department": "Finance", "Heading of the observation": "Heading",
                  "Risk level": "high", "Original target date": "31/12/2026"})
        r.update(over)
        return r

    df = pd.DataFrame([
        row(1), row(2, **{"In-house or external auditor": "External"}),
        row(3, Department="Compliance, Recovery, and Legal"),     # comma variant must match
        row(4, Department="Space Department"),                      # bad department
        row(5, **{"Original target date": "not a date"}),            # bad date
        row(1),                                                      # duplicate serial
        row(7, **{"Risk level": "Extreme"}),                         # bad risk
    ], columns=app.MASTER_COLUMNS)
    result = app.import_findings(db, df, "Audit Admin")
    assert result["inserted"] == 3, result
    assert result["skipped"] == 4, result
    rows = {r["serial_no"]: r for r in db.fetch("SELECT * FROM findings")}
    assert rows["2"]["source"] == "External auditor"
    assert rows["3"]["department"] == "Compliance, Recovery and Legal"
    assert rows["1"]["risk_level"] == "High" and rows["1"]["original_target_date"] == "2026-12-31"
    error_rows = [e[0] for e in result["errors"]]
    assert error_rows == [5, 6, 7, 8], error_rows
    again = app.import_findings(db, df.iloc[[0]], "Audit Admin")
    assert again["inserted"] == 0 and again["skipped"] == 1, "importing the same serial twice must be refused"
    expect_error(ValueError, app.import_findings, db, df.drop(columns=["Risk level"]), "Audit Admin")


def test_ageing_buckets():
    cases = {-5: "Not yet due", 0: "Not yet due", 1: "1-30 days", 30: "1-30 days", 31: "31-60 days",
             60: "31-60 days", 61: "61-90 days", 90: "61-90 days", 91: "Over 90 days", 400: "Over 90 days"}
    for days, bucket in cases.items():
        assert app.ageing_bucket(days) == bucket, (days, bucket)


def test_status_logic_auditor_is_official():
    db = new_db()
    fid = add(db, 1, target=TODAY - timedelta(days=100))
    status = app.get_status_table(db, TODAY).iloc[0]
    assert status["current_auditor_status"] == "Open" and status["ageing_original"] == "Over 90 days"
    # round 1: management says Closed, auditor says Ongoing
    app.open_round(db, ADMIN, app.ROUND_QUARTERLY, TODAY - timedelta(days=60), TODAY - timedelta(days=46), False, TODAY)
    fu1 = db.fetch("SELECT id FROM followups")[0]["id"]
    app.submit_management_update(db, owner(db, "Credit 1"), fu1, "Closed", "Done", None, today=TODAY)
    status = app.get_status_table(db, TODAY).iloc[0]
    assert status["current_mgmt_status"] == "Closed" and status["current_auditor_status"] == "Open"
    assert bool(status["mgmt_closed_auditor_not_closed"]) is True
    app.submit_auditor_review(db, ADMIN, fu1, "Ongoing", "Evidence incomplete", TODAY)
    status = app.get_status_table(db, TODAY).iloc[0]
    assert status["current_auditor_status"] == "Ongoing"
    assert bool(status["mgmt_closed_auditor_not_closed"]) is True
    # round 2: revised target date given, then auditor closes
    app.open_round(db, ADMIN, app.ROUND_QUARTERLY, TODAY - timedelta(days=5), TODAY + timedelta(days=9), False, TODAY)
    fu2 = db.fetch("SELECT id FROM followups ORDER BY id")[1]["id"]
    app.submit_management_update(db, owner(db, "Credit 2"), fu2, "Ongoing", "Half done",
                                 TODAY + timedelta(days=30), today=TODAY)
    status = app.get_status_table(db, TODAY).iloc[0]
    assert status["effective_target_date"] == TODAY + timedelta(days=30)
    assert status["extensions"] == 1 and status["ageing_revised"] == "Not yet due"
    assert status["ageing_original"] == "Over 90 days"
    app.submit_auditor_review(db, ADMIN, fu2, "Closed", "Evidence verified", TODAY)
    status = app.get_status_table(db, TODAY).iloc[0]
    assert status["current_auditor_status"] == "Closed" and status["ageing_original"] == "Closed"
    assert bool(status["mgmt_closed_auditor_not_closed"]) is False
    assert app.ageing_counts(app.get_status_table(db, TODAY)).sum() == 0, "closed findings must not be in ageing"


def test_round_eligibility_quarterly_and_monthly():
    db = new_db()
    ids = {
        "high": add(db, 1, risk="High"), "med": add(db, 2, risk="Medium"),
        "low": add(db, 3, risk="Low"), "closed_high": add(db, 4, risk="High"),
    }
    app.open_round(db, ADMIN, app.ROUND_QUARTERLY, TODAY - timedelta(days=90), TODAY - timedelta(days=76), False, TODAY)
    first = {r["finding_id"]: r["id"] for r in db.fetch("SELECT * FROM followups")}
    assert len(first) == 4
    app.submit_auditor_review(db, ADMIN, first[ids["closed_high"]], "Closed", "Verified", TODAY)
    expect_error(ValueError, app.open_round, db, ADMIN, app.ROUND_QUARTERLY,
                 TODAY - timedelta(days=90), TODAY, False, TODAY)  # same date again: nothing new to add
    result = app.open_round(db, ADMIN, app.ROUND_MONTHLY, TODAY - timedelta(days=30), TODAY - timedelta(days=16), False, TODAY)
    assert result["findings"] == 1, "monthly round = only unclosed High-risk findings"
    result = app.open_round(db, ADMIN, app.ROUND_QUARTERLY, TODAY - timedelta(days=10), TODAY + timedelta(days=4), False, TODAY)
    assert result["findings"] == 3, "closed finding must drop out of later rounds"
    expect_error(ValueError, app.open_round, db, ADMIN, app.ROUND_QUARTERLY, TODAY, TODAY - timedelta(days=1), False, TODAY)


def test_permissions():
    db = new_db()
    add(db, 1, dept="Credit")
    add(db, 2, dept="Finance")
    app.open_round(db, ADMIN, app.ROUND_QUARTERLY, TODAY - timedelta(days=10), TODAY + timedelta(days=4), False, TODAY)
    fus = {r["finding_id"]: r["id"] for r in db.fetch("SELECT * FROM followups")}
    credit_fu = fus[db.fetch("SELECT id FROM findings WHERE department='Credit'")[0]["id"]]
    finance_fu = fus[db.fetch("SELECT id FROM findings WHERE department='Finance'")[0]["id"]]
    credit1 = owner(db, "Credit 1")
    # an owner cannot touch another department's item
    expect_error(PermissionError, app.submit_management_update, db, credit1, finance_fu, "Open", "x", None, today=TODAY)
    # admin and management cannot use the owner screen
    expect_error(PermissionError, app.submit_management_update, db, ADMIN, credit_fu, "Open", "x", None, today=TODAY)
    expect_error(PermissionError, app.submit_management_update, db, MGMT, credit_fu, "Open", "x", None, today=TODAY)
    # owners and management cannot do audit-only things
    expect_error(PermissionError, app.submit_auditor_review, db, credit1, credit_fu, "Closed", "x", TODAY)
    expect_error(PermissionError, app.open_round, db, credit1, app.ROUND_QUARTERLY, TODAY, TODAY, False, TODAY)
    expect_error(PermissionError, app.add_finding, db, credit1, finding(99))
    expect_error(PermissionError, app.update_finding, db, MGMT, 1, finding(1))
    expect_error(PermissionError, app.wipe_all_data, db, credit1)
    expect_error(PermissionError, app.send_due_reminders, db, credit1, TODAY)
    # validation
    expect_error(ValueError, app.submit_management_update, db, credit1, credit_fu, "Maybe", "x", None, today=TODAY)
    expect_error(ValueError, app.submit_management_update, db, credit1, credit_fu, "Open", "   ", None, today=TODAY)
    app.submit_management_update(db, credit1, credit_fu, "Ongoing", "Working on it", TODAY + timedelta(days=20), today=TODAY)
    # once the auditor has reviewed, the owner can no longer edit
    expect_error(ValueError, app.submit_auditor_review, db, ADMIN, credit_fu, "Closed", "", TODAY)  # remarks needed
    app.submit_auditor_review(db, ADMIN, credit_fu, "Ongoing", "Noted", TODAY)
    expect_error(PermissionError, app.submit_management_update, db, credit1, credit_fu, "Closed", "Done", None, today=TODAY)
    # evidence size limit
    big = ("big.pdf", b"x" * (app.MAX_EVIDENCE_BYTES + 1))
    expect_error(ValueError, app.submit_management_update, db, owner(db, "Finance 1"), finance_fu, "Open", "x",
                 TODAY + timedelta(days=5), big, TODAY)


def test_original_target_date_is_locked_and_revision_is_rule_checked():
    db = new_db()
    fid = add(db, 1, dept="Credit", target=TODAY - timedelta(days=30))
    app.open_round(db, ADMIN, app.ROUND_QUARTERLY, TODAY - timedelta(days=3), TODAY + timedelta(days=11), False, TODAY)
    fu = db.fetch("SELECT id FROM followups")[0]["id"]
    credit = owner(db, "Credit 1")
    # target date has passed and status is not Closed -> a revised date is compulsory
    expect_error(ValueError, app.submit_management_update, db, credit, fu, "Ongoing", "Working", None, today=TODAY)
    app.submit_management_update(db, credit, fu, "Ongoing", "Working", TODAY + timedelta(days=45), today=TODAY)
    row = db.fetch("SELECT * FROM findings WHERE id = ?", (fid,))[0]
    assert row["original_target_date"] == (TODAY - timedelta(days=30)).isoformat(), "original date must stay sealed"
    followup = db.fetch("SELECT * FROM followups WHERE id = ?", (fu,))[0]
    assert followup["revised_target_date"] == (TODAY + timedelta(days=45)).isoformat()
    assert followup["mgmt_updated_by"] == "Credit 1" and followup["mgmt_updated_on"] == TODAY.isoformat()
    trail = db.fetch("SELECT * FROM audit_trail WHERE field = 'revised_target_date'")
    assert trail and trail[0]["username"] == "Credit 1", "revised target date change must be in the audit trail"
    # Closed does not need a revised date
    app.submit_management_update(db, credit, fu, "Closed", "All done", None, ("proof.txt", b"evidence"), TODAY)
    assert app.get_evidence(db, fu)[0]["filename"] == "proof.txt"
    name, data = app.get_evidence_bytes(db, app.get_evidence(db, fu)[0]["id"])
    assert name == "proof.txt" and data == b"evidence"


def test_reminders_one_week_after_due_date():
    db = new_db()
    add(db, 1, dept="Credit")
    add(db, 2, dept="Credit")
    add(db, 3, dept="Finance")
    add(db, 4, dept="IT")
    ids = {r["serial_no"]: r["id"] for r in db.fetch("SELECT id, serial_no FROM findings")}
    # three rounds on different dates so that each finding has its own due date
    def round_for(serial, due):
        with db.session() as conn:
            rid = db.insert(conn, "INSERT INTO rounds (kind, follow_up_date, response_due_date, created_by, created_at) "
                                  "VALUES (?, ?, ?, ?, ?)", (app.ROUND_QUARTERLY, due.isoformat(), due.isoformat(), "t", "t"))
            db.execute(conn, "INSERT INTO followups (finding_id, round_id, follow_up_date, response_due_date) "
                             "VALUES (?, ?, ?, ?)", (ids[serial], rid, due.isoformat(), due.isoformat()))
    round_for("1", TODAY - timedelta(days=7))    # exactly 7 days after due: reminder due
    round_for("2", TODAY - timedelta(days=6))    # 6 days after due: NOT yet
    round_for("3", TODAY - timedelta(days=20))   # long overdue: due
    round_for("4", TODAY - timedelta(days=30))   # overdue, but management already answered
    it_fu = db.fetch("SELECT id FROM followups WHERE finding_id = ?", (ids["4"],))[0]["id"]
    app.submit_management_update(db, owner(db, "IT 1"), it_fu, "Closed", "Done", None, today=TODAY - timedelta(days=25))

    pending = app.pending_reminders(db, TODAY)
    assert sorted(pending["serial_no"]) == ["1", "3"], list(pending["serial_no"])
    results = app.send_due_reminders(db, ADMIN, TODAY)
    assert sorted(r["department"] for r in results) == ["Credit", "Finance"]
    assert all(r["ok"] for r in results)
    log = db.fetch("SELECT * FROM email_log")
    assert len(log) == 2
    credit_mail = [m for m in log if "Credit" in m["subject"]][0]
    assert "credit1@example.com" in credit_mail["to_addr"] and "credit2@example.com" in credit_mail["to_addr"]
    assert "audit.admin@example.com" in credit_mail["cc_addr"], "audit team must be copied"
    assert "REMINDER" in credit_mail["subject"]
    assert app.send_due_reminders(db, ADMIN, TODAY) == [], "a reminder must not be sent twice"
    # the next day the 6-day item becomes due
    pending = app.pending_reminders(db, TODAY + timedelta(days=1))
    assert list(pending["serial_no"]) == ["2"]


def test_email_redirect_and_failure_handling():
    db = new_db()
    os.environ["TEST_EMAIL_OVERRIDE"] = "tester@example.com"
    try:
        ok, detail = app.send_email(db, ["a@example.com"], ["b@example.com"], "Subject", "Body")
        row = db.fetch("SELECT * FROM email_log")[0]
        assert ok and row["to_addr"] == "tester@example.com" and row["cc_addr"] == ""
        assert "a@example.com" in row["detail"], "log must show the original recipient"
    finally:
        os.environ.pop("TEST_EMAIL_OVERRIDE")
    os.environ["EMAIL_MODE"] = "gmail"   # no credentials set: must fail politely, not crash
    try:
        ok, detail = app.send_email(db, ["a@example.com"], [], "Subject", "Body")
        assert ok is False and "GMAIL_USER" in detail
        ok, detail = app.send_email(db, [], [], "Subject", "Body")
        assert ok is False and "No recipient" in detail
    finally:
        os.environ["EMAIL_MODE"] = "log"
    assert db.fetch("SELECT status FROM email_log ORDER BY id DESC LIMIT 1")[0]["status"] == "failed"


def test_escalation_is_off_by_default_and_works_when_on():
    db = new_db()
    add(db, 1, dept="Credit")
    app.open_round(db, ADMIN, app.ROUND_QUARTERLY, TODAY - timedelta(days=30), TODAY - timedelta(days=20), False, TODAY)
    app.send_due_reminders(db, ADMIN, TODAY)
    assert app.send_escalations(db, ADMIN, TODAY) == [], "escalation must be off by default"
    os.environ["ESCALATION_ENABLED"] = "true"
    try:
        results = app.send_escalations(db, ADMIN, TODAY)
        assert len(results) == 1 and results[0]["ok"]
        assert "head.credit@example.com" in db.fetch("SELECT to_addr FROM email_log ORDER BY id DESC LIMIT 1")[0]["to_addr"]
        assert app.send_escalations(db, ADMIN, TODAY) == []
    finally:
        os.environ.pop("ESCALATION_ENABLED")


def test_open_round_sends_one_email_per_department():
    db = new_db()
    add(db, 1, dept="Credit")
    add(db, 2, dept="Credit")
    add(db, 3, dept="Risk")
    result = app.open_round(db, ADMIN, app.ROUND_QUARTERLY, TODAY, TODAY + timedelta(days=14), True, TODAY)
    assert result["findings"] == 3 and len(result["emails"]) == 2
    assert db.fetch("SELECT COUNT(*) AS n FROM email_log")[0]["n"] == 2


def test_sample_data():
    db = new_db()
    result = app.load_sample_data(db, ADMIN, today=TODAY)
    findings = db.fetch("SELECT department, COUNT(*) AS n FROM findings GROUP BY department")
    assert len(findings) == 14
    for r in findings:
        assert 30 <= r["n"] <= 50, (r["department"], r["n"])
    assert result["findings"] == sum(r["n"] for r in findings)
    assert db.fetch("SELECT COUNT(*) AS n FROM rounds")[0]["n"] == 4
    assert result["pending_in_current_round"] > 0
    status = app.get_status_table(db, TODAY)
    assert set(status["current_auditor_status"]) <= set(app.STATUSES)
    assert set(status["current_auditor_status"]) == set(app.STATUSES), "sample data should show all three statuses"
    assert bool(status["mgmt_closed_auditor_not_closed"].any()), "sample data should include disagreements"
    counts = app.ageing_counts(status)
    assert (counts > 0).all(), f"every ageing bucket should have items: {counts.to_dict()}"
    assert app.pending_reminders(db, TODAY).shape[0] > 0
    expect_error(ValueError, app.load_sample_data, db, ADMIN)  # cannot load twice
    app.wipe_all_data(db, ADMIN)
    assert db.fetch("SELECT COUNT(*) AS n FROM findings")[0]["n"] == 0
    assert db.fetch("SELECT COUNT(*) AS n FROM users")[0]["n"] == 30, "wipe must keep the users"


def test_wide_export_and_excel():
    db = new_db()
    app.load_sample_data(db, ADMIN, today=TODAY)
    wide = app.build_wide_export(db, TODAY)
    for col in app.MASTER_COLUMNS:
        assert col in wide.columns, col
    assert {"FU1 date", "FU1 management status", "FU1 management response", "FU1 auditor status"} <= set(wide.columns)
    assert "Current auditor status" in wide.columns
    data = app.to_excel_bytes({"Wide": wide})
    back = pd.read_excel(pd.io.common.BytesIO(data))
    assert len(back) == len(wide)


def test_edit_finding_is_logged():
    db = new_db()
    fid = add(db, 1)
    rec = finding(1, heading="New heading")
    assert app.update_finding(db, ADMIN, fid, rec) == 1
    assert app.update_finding(db, ADMIN, fid, rec) == 0
    trail = db.fetch("SELECT * FROM audit_trail WHERE action = 'edit'")
    assert len(trail) == 1 and trail[0]["old_value"] == "Test finding" and trail[0]["new_value"] == "New heading"
    add(db, 2)
    expect_error(ValueError, app.update_finding, db, ADMIN, fid, finding(2))   # serial clash
    expect_error(ValueError, app.add_finding, db, ADMIN, finding(2))            # duplicate serial


# --------------------------------------------------------------------------- runner

def main():
    report_path = None
    if "--report" in sys.argv:
        report_path = sys.argv[sys.argv.index("--report") + 1]
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    lines, failed = [], 0
    for name, func in tests:
        try:
            func()
            lines.append(f"PASS  {name}")
        except Exception:
            failed += 1
            lines.append(f"FAIL  {name}\n{traceback.format_exc()}")
    lines.append("")
    lines.append(f"{len(tests) - failed} of {len(tests)} tests passed" + ("" if not failed else f", {failed} FAILED"))
    text = "\n".join(lines)
    print(text)
    if report_path:
        with open(report_path, "w", encoding="utf-8") as handle:
            handle.write(f"Automatic test run on {date.today().isoformat()}\n\n" + text + "\n")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
