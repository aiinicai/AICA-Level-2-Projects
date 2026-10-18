"""
My Work Diary - core logic (no UI code here).
Developed by CA Sapan

Everything is stored in a local SQLite file. Nothing is sent anywhere.
"""
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

CATEGORIES = ["Client work", "Internal", "Additional / ad-hoc", "Learning", "Admin"]
STATUSES = ["Not started", "In progress", "Done"]
KPI_TYPES = ["Tasks completed", "Hours logged", "Manual count"]
PERIODS = ["Monthly", "Yearly"]
CREDIT = "Developed by CA Sapan"

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT NOT NULL,
    category      TEXT NOT NULL,
    client        TEXT DEFAULT '',
    is_additional INTEGER DEFAULT 0,
    planned_min   INTEGER DEFAULT 0,
    status        TEXT DEFAULT 'Not started',
    original_date TEXT NOT NULL,
    scheduled_date TEXT NOT NULL,
    carried_count INTEGER DEFAULT 0,
    completed_on  TEXT,
    notes         TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS time_entries (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id    INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    entry_date TEXT NOT NULL,
    minutes    INTEGER NOT NULL CHECK (minutes > 0),
    note       TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS kpis (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL,
    period   TEXT NOT NULL,
    year     INTEGER NOT NULL,
    month    INTEGER,
    target   REAL NOT NULL CHECK (target > 0),
    kpi_type TEXT NOT NULL,
    category TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS kpi_manual (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    kpi_id     INTEGER NOT NULL REFERENCES kpis(id) ON DELETE CASCADE,
    entry_date TEXT NOT NULL,
    value      REAL NOT NULL,
    note       TEXT DEFAULT ''
);
"""


def iso(d) -> str:
    if isinstance(d, (date, datetime)):
        return d.strftime("%Y-%m-%d")
    return str(d)


def connect(path="work_diary.db") -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


# ---------------------------------------------------------------- tasks
def add_task(conn, title, category, task_date, client="", planned_min=0,
             additional=False, notes=""):
    title = (title or "").strip()
    if not title:
        raise ValueError("Task title is required.")
    if category not in CATEGORIES:
        raise ValueError(f"Unknown category: {category}")
    if planned_min < 0:
        raise ValueError("Planned minutes cannot be negative.")
    is_add = 1 if (additional or category == "Additional / ad-hoc") else 0
    cur = conn.execute(
        """INSERT INTO tasks (title, category, client, is_additional, planned_min,
           original_date, scheduled_date, notes) VALUES (?,?,?,?,?,?,?,?)""",
        (title, category, client.strip(), is_add, int(planned_min),
         iso(task_date), iso(task_date), notes.strip()))
    conn.commit()
    return cur.lastrowid


def set_status(conn, task_id, status, on_date=None):
    if status not in STATUSES:
        raise ValueError(f"Unknown status: {status}")
    done_on = iso(on_date or date.today()) if status == "Done" else None
    conn.execute("UPDATE tasks SET status=?, completed_on=? WHERE id=?",
                 (status, done_on, task_id))
    conn.commit()


def carry_forward(conn, task_id, new_date):
    """Move an open task to a new date. original_date is never changed."""
    row = conn.execute("SELECT status, scheduled_date FROM tasks WHERE id=?",
                       (task_id,)).fetchone()
    if row is None:
        raise ValueError("Task not found.")
    if row["status"] == "Done":
        raise ValueError("A completed task cannot be carried forward.")
    if iso(new_date) <= row["scheduled_date"]:
        raise ValueError("New date must be later than the current scheduled date.")
    conn.execute("UPDATE tasks SET scheduled_date=?, carried_count=carried_count+1 WHERE id=?",
                 (iso(new_date), task_id))
    conn.commit()


def rollover_overdue(conn, today=None):
    """Carry every open task scheduled before today onto today. Returns count."""
    today = iso(today or date.today())
    rows = conn.execute(
        "SELECT id FROM tasks WHERE status!='Done' AND scheduled_date < ?", (today,)).fetchall()
    for r in rows:
        conn.execute("UPDATE tasks SET scheduled_date=?, carried_count=carried_count+1 WHERE id=?",
                     (today, r["id"]))
    conn.commit()
    return len(rows)


def delete_task(conn, task_id):
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()


# ---------------------------------------------------------- time entries
def log_time(conn, task_id, entry_date, minutes, note=""):
    if int(minutes) <= 0:
        raise ValueError("Minutes must be greater than zero.")
    if conn.execute("SELECT 1 FROM tasks WHERE id=?", (task_id,)).fetchone() is None:
        raise ValueError("Task not found.")
    conn.execute("INSERT INTO time_entries (task_id, entry_date, minutes, note) VALUES (?,?,?,?)",
                 (task_id, iso(entry_date), int(minutes), note.strip()))
    conn.commit()


def delete_time_entry(conn, entry_id):
    conn.execute("DELETE FROM time_entries WHERE id=?", (entry_id,))
    conn.commit()


# ------------------------------------------------------------- dataframes
def tasks_df(conn) -> pd.DataFrame:
    df = pd.read_sql_query(
        """SELECT t.*, COALESCE(SUM(e.minutes),0) AS actual_min
           FROM tasks t LEFT JOIN time_entries e ON e.task_id=t.id
           GROUP BY t.id ORDER BY t.scheduled_date, t.id""", conn)
    if df.empty:
        return df
    od = pd.to_datetime(df["original_date"])
    end = pd.to_datetime(df["completed_on"]).fillna(pd.Timestamp(date.today()))
    df["age_days"] = (end - od).dt.days
    df["flag"] = df.apply(
        lambda r: "Carried forward" if (r["status"] != "Done" and r["carried_count"] > 0) else "", axis=1)
    return df


def time_df(conn, start=None, end=None) -> pd.DataFrame:
    q = """SELECT e.id, e.entry_date, e.minutes, e.note, t.id AS task_id, t.title,
                  t.category, t.client, t.is_additional
           FROM time_entries e JOIN tasks t ON t.id=e.task_id WHERE 1=1"""
    args = []
    if start:
        q += " AND e.entry_date >= ?"; args.append(iso(start))
    if end:
        q += " AND e.entry_date <= ?"; args.append(iso(end))
    return pd.read_sql_query(q + " ORDER BY e.entry_date, e.id", conn, params=args)


# -------------------------------------------------------------------- KPIs
def add_kpi(conn, name, period, year, month, target, kpi_type, category=""):
    if period not in PERIODS:
        raise ValueError("Period must be Monthly or Yearly.")
    if kpi_type not in KPI_TYPES:
        raise ValueError("Unknown KPI type.")
    if not (name or "").strip():
        raise ValueError("KPI name is required.")
    if float(target) <= 0:
        raise ValueError("Target must be greater than zero.")
    if period == "Monthly" and not (month and 1 <= int(month) <= 12):
        raise ValueError("Monthly KPI needs a month (1-12).")
    cur = conn.execute(
        "INSERT INTO kpis (name, period, year, month, target, kpi_type, category) VALUES (?,?,?,?,?,?,?)",
        (name.strip(), period, int(year), int(month) if period == "Monthly" else None,
         float(target), kpi_type, category or ""))
    conn.commit()
    return cur.lastrowid


def add_kpi_manual(conn, kpi_id, entry_date, value, note=""):
    k = conn.execute("SELECT kpi_type FROM kpis WHERE id=?", (kpi_id,)).fetchone()
    if k is None:
        raise ValueError("KPI not found.")
    if k["kpi_type"] != "Manual count":
        raise ValueError("Only 'Manual count' KPIs take manual entries.")
    conn.execute("INSERT INTO kpi_manual (kpi_id, entry_date, value, note) VALUES (?,?,?,?)",
                 (kpi_id, iso(entry_date), float(value), note.strip()))
    conn.commit()


def delete_kpi(conn, kpi_id):
    conn.execute("DELETE FROM kpis WHERE id=?", (kpi_id,))
    conn.commit()


def _period_range(period, year, month):
    if period == "Yearly":
        return date(year, 1, 1), date(year, 12, 31)
    first = date(year, month, 1)
    nxt = date(year + (month == 12), (month % 12) + 1, 1)
    return first, nxt - timedelta(days=1)


def kpi_progress(conn, year, month=None) -> pd.DataFrame:
    """All yearly KPIs of `year` plus monthly KPIs of (year, month) if month given."""
    rows = conn.execute("SELECT * FROM kpis WHERE year=? ORDER BY period DESC, month, id",
                        (year,)).fetchall()
    out = []
    for k in rows:
        if k["period"] == "Monthly" and month and k["month"] != month:
            continue
        s, e = _period_range(k["period"], k["year"], k["month"])
        s_iso, e_iso = iso(s), iso(e)
        cat = k["category"] or None
        if k["kpi_type"] == "Tasks completed":
            q = "SELECT COUNT(*) c FROM tasks WHERE status='Done' AND completed_on BETWEEN ? AND ?"
            a = [s_iso, e_iso]
            if cat:
                q += " AND category=?"; a.append(cat)
            actual = conn.execute(q, a).fetchone()["c"]
        elif k["kpi_type"] == "Hours logged":
            q = """SELECT COALESCE(SUM(e.minutes),0) m FROM time_entries e
                   JOIN tasks t ON t.id=e.task_id WHERE e.entry_date BETWEEN ? AND ?"""
            a = [s_iso, e_iso]
            if cat:
                q += " AND t.category=?"; a.append(cat)
            actual = conn.execute(q, a).fetchone()["m"] / 60.0
        else:
            actual = conn.execute(
                "SELECT COALESCE(SUM(value),0) v FROM kpi_manual WHERE kpi_id=? AND entry_date BETWEEN ? AND ?",
                (k["id"], s_iso, e_iso)).fetchone()["v"]
        out.append({
            "id": k["id"], "KPI": k["name"], "Period": k["period"],
            "Month": k["month"] if k["month"] else "", "Type": k["kpi_type"],
            "Category": k["category"] or "All", "Target": k["target"],
            "Actual": round(float(actual), 2),
            "Achievement %": round(100.0 * float(actual) / k["target"], 1)})
    return pd.DataFrame(out)


# --------------------------------------------------------------- analytics
def summary(conn, start, end) -> dict:
    t = time_df(conn, start, end)
    total_min = int(t["minutes"].sum()) if not t.empty else 0
    add_min = int(t.loc[t["is_additional"] == 1, "minutes"].sum()) if not t.empty else 0
    by_cat = (t.groupby("category")["minutes"].sum().div(60).round(2)
              if not t.empty else pd.Series(dtype=float))
    td = tasks_df(conn)
    done = pd.DataFrame()
    open_ = pd.DataFrame()
    if not td.empty:
        done = td[(td["status"] == "Done") & (td["completed_on"] >= iso(start)) & (td["completed_on"] <= iso(end))]
        open_ = td[td["status"] != "Done"]
    planned = int(done["planned_min"].sum()) if not done.empty else 0
    actual_on_done = int(done["actual_min"].sum()) if not done.empty else 0
    return {
        "total_hours": round(total_min / 60, 2),
        "additional_hours": round(add_min / 60, 2),
        "additional_pct": round(100 * add_min / total_min, 1) if total_min else 0.0,
        "by_category_hours": by_cat,
        "tasks_done": len(done),
        "tasks_open": len(open_),
        "carried_open": int((open_["carried_count"] > 0).sum()) if not open_.empty else 0,
        "planned_min_done": planned,
        "actual_min_done": actual_on_done,
        "hours_by_day": (t.groupby("entry_date")["minutes"].sum().div(60).round(2)
                         if not t.empty else pd.Series(dtype=float)),
        "done_df": done,
    }


# ------------------------------------------------------------------ exports
def export_excel(conn, path, start, end):
    s = summary(conn, start, end)
    td = tasks_df(conn)
    tm = time_df(conn, start, end)
    kp = kpi_progress(conn, start.year, start.month if start.month == end.month else None)
    overview = pd.DataFrame({
        "Metric": ["Period", "Total hours logged", "Additional / ad-hoc hours",
                   "Additional work % of time", "Tasks completed", "Tasks still open",
                   "Open tasks carried forward"],
        "Value": [f"{iso(start)} to {iso(end)}", s["total_hours"], s["additional_hours"],
                  s["additional_pct"], s["tasks_done"], s["tasks_open"], s["carried_open"]]})
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        overview.to_excel(xw, sheet_name="Summary", index=False)
        s["by_category_hours"].rename("Hours").reset_index().to_excel(xw, sheet_name="Hours by category", index=False)
        (kp.drop(columns=["id"]) if not kp.empty else pd.DataFrame({"Note": ["No KPIs set"]})
         ).to_excel(xw, sheet_name="KPIs", index=False)
        td.drop(columns=["is_additional"], errors="ignore").to_excel(xw, sheet_name="Tasks", index=False)
        tm.to_excel(xw, sheet_name="Time entries", index=False)
        pd.DataFrame({"": [CREDIT]}).to_excel(xw, sheet_name="About", index=False)
        for ws in xw.book.worksheets:
            for col in ws.columns:
                width = max(len(str(c.value)) if c.value is not None else 0 for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(max(12, width + 2), 60)
    return path


def export_word(conn, path, start, end, name="CA Sapan"):
    from docx import Document
    from docx.shared import Pt
    s = summary(conn, start, end)
    kp = kpi_progress(conn, start.year, start.month if start.month == end.month else None)
    d = Document()
    d.styles["Normal"].font.name = "Calibri"
    d.styles["Normal"].font.size = Pt(11)
    d.add_heading("Work Summary", 0)
    d.add_paragraph(f"{name}\nPeriod: {iso(start)} to {iso(end)}")

    d.add_heading("Highlights", 1)
    for line in [
        f"Total hours logged: {s['total_hours']}",
        f"Tasks completed: {s['tasks_done']}; still open: {s['tasks_open']} "
        f"(of which carried forward: {s['carried_open']})",
        f"Additional / ad-hoc work: {s['additional_hours']} hours "
        f"({s['additional_pct']}% of logged time)",
    ]:
        d.add_paragraph(line, style="List Bullet")

    d.add_heading("Hours by category", 1)
    t = d.add_table(rows=1, cols=2); t.style = "Light Grid Accent 1"
    t.rows[0].cells[0].text, t.rows[0].cells[1].text = "Category", "Hours"
    for cat, hrs in s["by_category_hours"].items():
        r = t.add_row().cells; r[0].text, r[1].text = str(cat), f"{hrs:.2f}"

    d.add_heading("KPI achievement", 1)
    if kp.empty:
        d.add_paragraph("No KPIs were set for this period.")
    else:
        t = d.add_table(rows=1, cols=5); t.style = "Light Grid Accent 1"
        for i, h in enumerate(["KPI", "Period", "Target", "Actual", "Achievement %"]):
            t.rows[0].cells[i].text = h
        for _, r in kp.iterrows():
            c = t.add_row().cells
            c[0].text, c[1].text = r["KPI"], str(r["Period"])
            c[2].text, c[3].text, c[4].text = f"{r['Target']:g}", f"{r['Actual']:g}", f"{r['Achievement %']}%"

    d.add_heading("Tasks completed", 1)
    done = s["done_df"]
    if done.empty:
        d.add_paragraph("None in this period.")
    else:
        t = d.add_table(rows=1, cols=5); t.style = "Light Grid Accent 1"
        for i, h in enumerate(["Task", "Category", "Planned (min)", "Actual (min)", "Days taken"]):
            t.rows[0].cells[i].text = h
        for _, r in done.iterrows():
            c = t.add_row().cells
            c[0].text, c[1].text = r["title"], r["category"]
            c[2].text, c[3].text, c[4].text = str(r["planned_min"]), str(r["actual_min"]), str(r["age_days"])

    d.add_paragraph()
    p = d.add_paragraph(CREDIT); p.runs[0].italic = True
    d.save(path)
    return path


# ------------------------------------------------------------- sample data
def seed_sample(conn, today=None):
    """Fills the database with fictional data so the dashboard has something to show."""
    today = today or date.today()
    if conn.execute("SELECT COUNT(*) c FROM tasks").fetchone()["c"]:
        return False
    plan = [
        ("GST return working - Client A", "Client work", "Client A", 90, 0, "Done", [(-12, 80)]),
        ("TDS reconciliation - Client B", "Client work", "Client B", 120, 0, "Done", [(-10, 70), (-9, 65)]),
        ("Bank reconciliation - Client C", "Client work", "Client C", 60, 0, "Done", [(-8, 75)]),
        ("Audit working paper - Client D", "Client work", "Client D", 180, 0, "In progress", [(-6, 100), (-5, 90)]),
        ("Update office compliance tracker", "Internal", "", 45, 0, "Done", [(-7, 40)]),
        ("Urgent notice reply - Client A", "Additional / ad-hoc", "Client A", 0, 1, "Done", [(-4, 150)]),
        ("Partner asked for MIS pack", "Additional / ad-hoc", "", 0, 1, "Done", [(-3, 110)]),
        ("Learn Streamlit basics", "Learning", "", 60, 0, "Done", [(-2, 55)]),
        ("Prepare engagement letters", "Admin", "", 60, 0, "Not started", []),
        ("Month-end review - Client B", "Client work", "Client B", 90, 0, "Not started", []),
    ]
    for i, (title, cat, client, pmin, add, status, entries) in enumerate(plan):
        d0 = today - timedelta(days=14 - i)
        tid = add_task(conn, title, cat, d0, client, pmin, bool(add))
        for off, mins in entries:
            log_time(conn, tid, today + timedelta(days=off), mins)
        if status == "Done":
            last = max((today + timedelta(days=o) for o, _ in entries), default=today)
            set_status(conn, tid, "Done", last)
        elif status == "In progress":
            set_status(conn, tid, "In progress")
    rollover_overdue(conn, today)
    y, m = today.year, today.month
    add_kpi(conn, "Tasks completed this month", "Monthly", y, m, 10, "Tasks completed")
    add_kpi(conn, "Billable hours this month", "Monthly", y, m, 20, "Hours logged", "Client work")
    add_kpi(conn, "Client calls this month", "Monthly", y, m, 8, "Manual count")
    add_kpi(conn, "Tasks completed this year", "Yearly", y, None, 120, "Tasks completed")
    k = conn.execute("SELECT id FROM kpis WHERE name='Client calls this month'").fetchone()["id"]
    add_kpi_manual(conn, k, today - timedelta(days=5), 3, "Sample")
    return True
