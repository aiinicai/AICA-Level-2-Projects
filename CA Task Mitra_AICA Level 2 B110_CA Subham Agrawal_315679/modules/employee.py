from core import framework as F
from core.framework import Router, BOSS

MANIFEST = dict(key="employee", name="Employee Management", core=False, status="ready",
    desc="Personal dashboard, workload, attendance and timesheets.",
    subs=[("my_dashboard", "My work dashboard", "ready"), ("workload", "Workload view", "ready"),
          ("attendance", "Attendance", "ready"), ("timesheet", "Timesheet", "ready"),
          ("leave", "Leave management", "planned"), ("payroll", "Salary & incentives", "planned")])
R = Router()
TABLES = ["timesheet", "attendance"]
SCHEMA = """
create table if not exists attendance(id integer primary key, user_id int not null, day text not null, in_time text, out_time text, unique(user_id,day));
create table if not exists timesheet(id integer primary key, user_id int not null, assignment_id int, day text default (date('now','localtime')), hours real, note text);
"""


@R.get("/my", sub="my_dashboard")
def my(c):
    db, uid = c.db, c.user["id"]
    rows = db.q("select a.id,a.title,a.status,a.due_date,c.name client,(a.due_date<date('now','localtime')) overdue from assignments a "
                "join clients c on c.id=a.client_id where a.assigned_to=? and a.status not in ('Approved','Closed') order by a.due_date", (uid,))
    done = db.one("select count(*) n from assignments where assigned_to=? and status in ('Approved','Closed')", (uid,))["n"]
    return {"open": rows, "done": done, "overdue": sum(1 for r in rows if r["overdue"]),
            "hours_month": db.one("select coalesce(sum(hours),0) h from timesheet where user_id=? and day>=date('now','localtime','start of month')", (uid,))["h"]}


@R.get("/today", roles=BOSS, sub="attendance")
def today(c):
    """Who has reached the office today and who is yet to come."""
    return c.db.q("""select u.id, u.name, u.designation, a.in_time, a.out_time,
        case when a.in_time is null then 'Yet to come' when a.out_time is not null then 'Left' else 'In office' end state
        from users u left join attendance a on a.user_id=u.id and a.day=date('now','localtime') where u.active=1 and u.role!='ca' order by (a.in_time is null), u.name""")


@R.get("/workload", roles=BOSS, sub="workload")
def workload(c):
    return c.db.q("""select u.id,u.name,u.role,u.designation,
      (select count(*) from assignments a where a.assigned_to=u.id and a.status not in ('Approved','Closed')) open_tasks,
      (select count(*) from assignments a where a.assigned_to=u.id and a.status not in ('Approved','Closed') and a.due_date<date('now','localtime')) overdue,
      (select count(*) from assignments a where a.assigned_to=u.id and a.status='In Review') in_review,
      (select coalesce(sum(hours),0) from timesheet t where t.user_id=u.id and t.day>=date('now','localtime','start of month')) hours_month
      from users u where u.active=1 and u.role!='ca' order by open_tasks desc""")


@R.get("/attendance", sub="attendance")
def att(c):
    if c.is_boss:
        return c.db.q("select u.name, a.day, a.in_time, a.out_time from attendance a join users u on u.id=a.user_id order by a.day desc, u.name limit 200")
    return c.db.q("select u.name, a.day, a.in_time, a.out_time from attendance a join users u on u.id=a.user_id where a.user_id=? order by a.day desc limit 60", (c.user["id"],))


@R.post("/attendance/in", sub="attendance")
def att_in(c):
    c.db.x("insert or ignore into attendance(user_id,day,in_time) values(?,date('now','localtime'),time('now','localtime'))", (c.user["id"],))
    return {"ok": True}


@R.post("/attendance/out", sub="attendance")
def att_out(c):
    c.db.x("update attendance set out_time=time('now','localtime') where user_id=? and day=date('now','localtime')", (c.user["id"],))
    return {"ok": True}


@R.get("/timesheet", sub="timesheet")
def ts(c):
    sql = "select t.*, u.name employee, a.title from timesheet t join users u on u.id=t.user_id left join assignments a on a.id=t.assignment_id"
    if c.is_boss:
        return c.db.q(sql + " order by t.day desc, t.id desc limit 200")
    return c.db.q(sql + " where t.user_id=? order by t.day desc, t.id desc limit 100", (c.user["id"],))


@R.post("/timesheet", sub="timesheet")
def ts_add(c):
    hrs, = c.need("hours")
    c.db.x("insert into timesheet(user_id,assignment_id,hours,note,day) values(?,?,?,?,coalesce(?,date('now','localtime')))",
           (c.user["id"], c.body.get("assignment_id") or None, float(hrs), c.body.get("note"), c.body.get("day") or None))
    return {"ok": True}


def demo(db):
    users = db.q("select id from users where demo=1 and role='employee'")
    asg = db.q("select id,assigned_to from assignments where assigned_to is not null limit 12")
    for i, a in enumerate(asg):
        db.x("insert into timesheet(user_id,assignment_id,hours,note,day) values(?,?,?,?,date('now','localtime','-%d day'))" % (i % 6),
             (a["assigned_to"], a["id"], 1 + (i % 4) * 0.75, "Working papers"))
    for u in users:
        for d in range(1, 4):
            db.x("insert or ignore into attendance(user_id,day,in_time,out_time) values(?,date('now','localtime','-%d day'),'09:55','18:10')" % d, (u["id"],))
