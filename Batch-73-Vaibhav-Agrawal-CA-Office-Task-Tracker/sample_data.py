"""
sample_data.py - Demonstration data for the Task Tracker.

Every name below is fictitious. One-time due dates are calculated from today's
date, and "done" markers are set for the CURRENT cycle, so whenever the demo
is run it shows a realistic mix of done, overdue, due-soon and open work.

Run  python sample_data.py --reset  to wipe the database and load this data again.
"""

import sys
import uuid
from datetime import date, datetime, timedelta

import cycles
import database as db

PEOPLE = ["Ritika", "Aman", "Pooja", "Deepak", "Sneha"]

SECTIONS = [
    # name, header colour, repeat setting for tasks typed into its quick-add box
    ("Daily Office Work", "navy", "Daily"),
    ("GST", "navy", "Monthly"),
    ("TDS & Income Tax", "navy", "Monthly"),
    ("PF / ESI & Payroll", "navy", "Monthly"),
    ("Audit", "ochre", "One-time"),
    ("ROC / MCA", "navy", "Annual"),
    ("Office & Admin", "navy", "One-time"),
]


def in_days(n):
    return (date.today() + timedelta(days=n)).isoformat()


# Each task: section name, then the task's fields. "done": True marks it as
# completed for the current cycle; "past": n also adds n earlier cycles to history.
TASKS = [
    ("Daily Office Work", dict(title="Check e-mail and income-tax / GST portal notices", frequency="Daily", owner="Sneha")),
    ("Daily Office Work", dict(title="Update cash book and petty cash", frequency="Daily", owner="Deepak", done=True)),
    ("Daily Office Work", dict(title="Bank reconciliation of office accounts", frequency="Weekly", dueWeekday=5, owner="Deepak")),
    ("Daily Office Work", dict(title="Back up Tally data to external drive", frequency="Weekly", dueWeekday=6, owner="Sneha")),

    ("GST", dict(title="GSTR-1 filing - all monthly clients", frequency="Monthly", dueDay=11, owner="Aman", done=True, past=3,
                 subtasks=[("Collect sales registers", True), ("Upload invoices", True), ("File and save ARN", True)])),
    ("GST", dict(title="GSTR-2B reconciliation with purchase registers", frequency="Monthly", dueFrom=14, dueDay=18, owner="Pooja", done=True, past=2)),
    ("GST", dict(title="GSTR-3B filing - all monthly clients", frequency="Monthly", dueDay=20, owner="Aman", past=3,
                 remarks="Balaji Steels ITC mismatch of 42,300 to be resolved first",
                 subtasks=[("Reconcile ITC with GSTR-2B", True), ("Compute tax liability", True), ("Get challan paid by client", False), ("File return", False)])),
    ("GST", dict(title="IFF / PMT-06 for QRMP clients", frequency="Monthly", dueDay=13, owner="Pooja", done=True)),
    ("GST", dict(title="GSTR-1 / 3B for quarterly clients", frequency="Quarterly", dueDay=22, dueQOffset=1, owner="Pooja")),
    ("GST", dict(title="GSTR-9 annual return", frequency="Annual", dueDate="2026-12-31", owner="Ritika", tag="Balaji Steels")),

    ("TDS & Income Tax", dict(title="TDS / TCS payment (challan 281)", frequency="Monthly", dueDay=7, owner="Deepak", done=True, past=4)),
    ("TDS & Income Tax", dict(title="TDS returns 24Q / 26Q", frequency="Quarterly", dueDay=31, dueQOffset=1, owner="Ritika",
                              subtasks=[("Collect deductee details", False), ("Verify challans on TRACES", False), ("Generate FVU and file", False)])),
    ("TDS & Income Tax", dict(title="Issue Form 16A to deductees", frequency="Quarterly", dueDay=15, dueQOffset=1, owner="Deepak")),
    ("TDS & Income Tax", dict(title="Advance tax computation and payment", frequency="Quarterly", dueDay=15, dueQOffset=0, owner="Ritika", done=True)),
    ("TDS & Income Tax", dict(title="Income-tax returns - non-audit clients", frequency="Annual", dueDate="2026-07-31", owner="Aman", done=True)),
    ("TDS & Income Tax", dict(title="Income-tax returns - audit clients", frequency="Annual", dueDate="2026-10-31", owner="Ritika")),
    ("TDS & Income Tax", dict(title="Reply to notice u/s 143(1)", dueDate=in_days(2), owner="Ritika", tag="Dr. Sharma", starred=True,
                              remarks="TDS credit mismatch - Form 26AS shows 18,400 less")),

    ("PF / ESI & Payroll", dict(title="Salary processing and payslips", frequency="Monthly", dueFrom=28, dueDay=5, owner="Sneha", done=True)),
    ("PF / ESI & Payroll", dict(title="PF and ESI payment", frequency="Monthly", dueDay=15, owner="Sneha", done=True, past=3)),
    ("PF / ESI & Payroll", dict(title="Professional tax payment", frequency="Monthly", dueDay=30, owner="Sneha")),

    ("Audit", dict(title="Tax audit report (Form 3CA / 3CD)", frequency="Annual", dueDate="2026-09-30", owner="Ritika", tag="Balaji Steels", starred=True,
                   remarks="Stock statement and debtor confirmations awaited",
                   subtasks=[("Vouching and verification", True), ("Draft Form 3CD", True), ("Partner review", False), ("Upload with UDIN", False)])),
    ("Audit", dict(title="Tax audit report (Form 3CB / 3CD)", frequency="Annual", dueDate="2026-09-30", owner="Aman", tag="Bhilai Engg Works")),
    ("Audit", dict(title="Stock audit for bank", dueDate=in_days(12), owner="Aman", tag="MB Traders")),
    ("Audit", dict(title="Collect bank statements and loan confirmations", dueDate=in_days(-3), owner="Pooja", tag="Bhilai Engg Works",
                   remarks="Reminder sent twice - call the accountant")),
    ("Audit", dict(title="Form 10B audit report - trust", dueDate=in_days(-20), owner="Ritika", tag="Sunrise Education", done=True)),

    ("ROC / MCA", dict(title="DIR-3 KYC of directors", frequency="Annual", dueDate="2026-09-30", owner="Pooja", remarks="OTP pending from one director")),
    ("ROC / MCA", dict(title="Form AOC-4 (financial statements)", frequency="Annual", dueDate="2026-10-29", owner="Ritika")),
    ("ROC / MCA", dict(title="Form MGT-7 (annual return)", frequency="Annual", dueDate="2026-11-28", owner="Ritika")),
    ("ROC / MCA", dict(title="Form 11 - LLP annual return", frequency="Annual", dueDate="2026-05-30", owner="Pooja", done=True)),
    ("ROC / MCA", dict(title="Form DPT-3 (return of deposits)", frequency="Annual", dueDate="2026-06-30", owner="Pooja", done=True)),

    ("Office & Admin", dict(title="Staff review meeting", frequency="Monthly", dueRule="2nd-sat", done=True)),
    ("Office & Admin", dict(title="Renew DSC of director", dueDate=in_days(6), owner="Sneha", tag="Balaji Steels")),
    ("Office & Admin", dict(title="Prepare CMA data for CC limit renewal", dueDate=in_days(25), owner="Aman", tag="MB Traders", later=True)),
    ("Office & Admin", dict(title="Update client KYC master file", owner="Sneha", later=True)),
    ("Office & Admin", dict(title="Raise professional fee bills for the quarter", frequency="Quarterly", dueDay=10, dueQOffset=1)),
]


def new_id():
    return uuid.uuid4().hex[:20]


def previous_cycle_keys(task, count):
    """Cycle keys of the `count` months before the current one (for the history)."""
    keys, day = [], date.today().replace(day=1)
    for _ in range(count):
        day = (day - timedelta(days=1)).replace(day=1)
        keys.append(cycles.cycle(task, day.replace(day=15))["key"])
    return keys


def load_sample_data():
    db.set_people(PEOPLE)

    section_ids = {}
    for position, (name, color, frequency) in enumerate(SECTIONS, start=1):
        section_ids[name] = new_id()
        db.save_section(section_ids[name], {"name": name, "color": color,
                                            "defaultFrequency": frequency, "order": position * 10})

    now = datetime.now().isoformat(timespec="seconds")
    for position, (section, fields) in enumerate(TASKS, start=1):
        task = dict(fields)
        done, past = task.pop("done", False), task.pop("past", 0)
        task.update(section=section_ids[section], order=position * 10, createdAt=now, status="open")
        task.setdefault("frequency", "One-time")
        task["subtasks"] = [{"text": text, "done": ok} for text, ok in task.get("subtasks", [])]

        history = {key: now for key in previous_cycle_keys(task, past)}
        if done and cycles.is_recurring(task):
            key = cycles.cycle(task)["key"]
            history[key] = now
            task.update(doneFor=key, doneAt=now)
        elif done:
            task.update(status="done", doneAt=now)
        task["history"] = history

        db.save_task(new_id(), task)


if __name__ == "__main__":
    db.init_db()
    if "--reset" in sys.argv:
        db.clear_all_data()
    if db.is_empty():
        load_sample_data()
        print("Sample data loaded.")
    else:
        print("The tracker already has data. Use  python sample_data.py --reset  to replace it.")
