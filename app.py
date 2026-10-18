"""
My Work Diary - personal performance and time tracker (Phase 1)
Developed by CA Sapan

Run:  streamlit run app.py
All data stays in work_diary.db on this computer.
"""
import os
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

import core

DB_PATH = os.environ.get("WORK_DIARY_DB", str(Path(__file__).parent / "work_diary.db"))

st.set_page_config(page_title="My Work Diary", page_icon="📒", layout="wide")
conn = core.connect(DB_PATH)
today = date.today()


def fmt_task(tid, tdf):
    r = tdf.set_index("id").loc[tid]
    return f"#{tid} · {r['title']} ({r['status']})"


def safe(action, success_msg=None):
    """Run an action; show validation errors instead of a crash."""
    try:
        action()
        if success_msg:
            st.success(success_msg)
        return True
    except ValueError as ex:
        st.error(str(ex))
        return False


# ------------------------------------------------------------------ sidebar
st.sidebar.title("📒 My Work Diary")
page = st.sidebar.radio("Go to", ["Today", "All tasks", "KPIs", "Dashboard", "Report"])
st.sidebar.divider()
if st.sidebar.button("Load sample data"):
    if core.seed_sample(conn, today):
        st.sidebar.success("Sample data loaded (fictional).")
    else:
        st.sidebar.info("Sample data is only loaded into an empty diary.")
st.sidebar.caption("Data is stored only in a local file on this computer.")
st.sidebar.caption(core.CREDIT)


# -------------------------------------------------------------------- Today
if page == "Today":
    st.title("Today")
    day = st.date_input("Date", today)

    overdue = conn.execute(
        "SELECT COUNT(*) c FROM tasks WHERE status!='Done' AND scheduled_date < ?",
        (core.iso(today),)).fetchone()["c"]
    if overdue:
        st.warning(f"{overdue} open task(s) are scheduled before today.")
        if st.button("Carry all of them forward to today"):
            n = core.rollover_overdue(conn, today)
            st.success(f"{n} task(s) carried forward. Original dates are kept.")

    with st.expander("➕ Add a task", expanded=False):
        with st.form("add_task", clear_on_submit=True):
            title = st.text_input("Task")
            c1, c2, c3 = st.columns(3)
            category = c1.selectbox("Category", core.CATEGORIES)
            client = c2.text_input("Client / person (optional)")
            planned = c3.number_input("Planned minutes", min_value=0, value=60, step=15)
            additional = st.checkbox("This was an additional / unplanned task")
            notes = st.text_area("Notes (optional)", height=70)
            if st.form_submit_button("Add task"):
                safe(lambda: core.add_task(conn, title, category, day, client,
                                           planned, additional, notes), "Task added.")

    tdf = core.tasks_df(conn)
    st.subheader("Open and due")
    if tdf.empty:
        st.info("No tasks yet. Add one above, or load sample data from the sidebar.")
    else:
        due = tdf[(tdf["status"] != "Done") & (tdf["scheduled_date"] <= core.iso(day))]
        done_today = tdf[(tdf["status"] == "Done") & (tdf["completed_on"] == core.iso(day))]
        if due.empty:
            st.write("Nothing open for this date.")
        else:
            st.dataframe(due[["id", "title", "category", "client", "status", "planned_min",
                              "actual_min", "original_date", "carried_count", "flag"]],
                         hide_index=True)

        if not tdf[tdf["status"] != "Done"].empty:
            open_ids = tdf[tdf["status"] != "Done"]["id"].tolist()
            st.subheader("Log time or update a task")
            pick = st.selectbox("Task", open_ids, format_func=lambda i: fmt_task(i, tdf))
            c1, c2 = st.columns(2)
            with c1.form("log_time", clear_on_submit=True):
                mins = st.number_input("Minutes spent", min_value=1, value=30, step=5)
                note = st.text_input("Note (optional)")
                if st.form_submit_button("Log time"):
                    safe(lambda: core.log_time(conn, pick, day, mins, note), "Time logged.")
            with c2.form("set_status"):
                status = st.selectbox("New status", core.STATUSES, index=1)
                if st.form_submit_button("Update status"):
                    safe(lambda: core.set_status(conn, pick, status, day), "Status updated.")

        st.subheader("Completed on this date")
        if done_today.empty:
            st.write("Nothing completed on this date.")
        else:
            st.dataframe(done_today[["id", "title", "category", "planned_min", "actual_min", "age_days"]],
                         hide_index=True)

    t = core.time_df(conn, day, day)
    st.metric("Time logged on this date (hours)", round(t["minutes"].sum() / 60, 2) if not t.empty else 0)


# ---------------------------------------------------------------- All tasks
elif page == "All tasks":
    st.title("All tasks")
    tdf = core.tasks_df(conn)
    if tdf.empty:
        st.info("No tasks yet.")
    else:
        c1, c2, c3 = st.columns(3)
        f_status = c1.multiselect("Status", core.STATUSES, default=core.STATUSES)
        f_cat = c2.multiselect("Category", core.CATEGORIES, default=core.CATEGORIES)
        f_client = c3.text_input("Client / person contains")
        view = tdf[tdf["status"].isin(f_status) & tdf["category"].isin(f_cat)]
        if f_client.strip():
            view = view[view["client"].str.contains(f_client.strip(), case=False, na=False)]
        st.dataframe(view[["id", "title", "category", "client", "status", "planned_min", "actual_min",
                           "original_date", "scheduled_date", "carried_count", "age_days", "flag"]],
                     hide_index=True)

        st.subheader("Carry a task forward")
        open_df = tdf[tdf["status"] != "Done"]
        if open_df.empty:
            st.write("No open tasks.")
        else:
            with st.form("carry"):
                tid = st.selectbox("Task", open_df["id"].tolist(), format_func=lambda i: fmt_task(i, tdf))
                new_date = st.date_input("New date", today + timedelta(days=1))
                if st.form_submit_button("Carry forward"):
                    safe(lambda: core.carry_forward(conn, tid, new_date), "Task moved. Original date kept.")

        st.subheader("Delete a task")
        with st.form("delete"):
            tid_d = st.selectbox("Task to delete", tdf["id"].tolist(), format_func=lambda i: fmt_task(i, tdf))
            sure = st.checkbox("Yes, delete this task and its time entries")
            if st.form_submit_button("Delete"):
                if sure:
                    core.delete_task(conn, tid_d)
                    st.success("Deleted. Refresh the page to update the table.")
                else:
                    st.error("Tick the box to confirm.")


# --------------------------------------------------------------------- KPIs
elif page == "KPIs":
    st.title("KPIs")
    c1, c2 = st.columns(2)
    year = c1.number_input("Year", min_value=2020, max_value=2100, value=today.year, step=1)
    month = c2.selectbox("Month", list(range(1, 13)), index=today.month - 1)

    with st.expander("➕ Add a KPI"):
        with st.form("add_kpi", clear_on_submit=True):
            name = st.text_input("KPI name (e.g. Returns filed)")
            a, b, c = st.columns(3)
            period = a.selectbox("Period", core.PERIODS)
            ktype = b.selectbox("Measured by", core.KPI_TYPES,
                                help="Tasks completed and Hours logged are calculated automatically. "
                                     "Manual count is for things you add yourself, such as client calls.")
            target = c.number_input("Target", min_value=0.0, value=10.0, step=1.0)
            cat = st.selectbox("Only count this category (optional)", [""] + core.CATEGORIES)
            if st.form_submit_button("Save KPI"):
                safe(lambda: core.add_kpi(conn, name, period, int(year), month, target, ktype, cat),
                     "KPI saved for the selected year (and month, if monthly).")

    prog = core.kpi_progress(conn, int(year), month)
    if prog.empty:
        st.info("No KPIs for this selection yet.")
    else:
        for _, r in prog.iterrows():
            pct = r["Achievement %"]
            st.write(f"**{r['KPI']}** · {r['Period']} · {r['Type']} · {r['Category']}")
            st.progress(min(max(pct / 100.0, 0.0), 1.0))
            st.caption(f"{r['Actual']:g} of {r['Target']:g} ({pct}%)")
        st.dataframe(prog.drop(columns=["id"]), hide_index=True)

        manual = prog[prog["Type"] == "Manual count"]
        if not manual.empty:
            st.subheader("Add to a manual-count KPI")
            with st.form("manual"):
                kid = st.selectbox("KPI", manual["id"].tolist(),
                                   format_func=lambda i: manual.set_index("id").loc[i, "KPI"])
                d = st.date_input("Date", today)
                v = st.number_input("Count to add", value=1.0, step=1.0)
                n = st.text_input("Note (optional)")
                if st.form_submit_button("Add"):
                    safe(lambda: core.add_kpi_manual(conn, kid, d, v, n), "Added.")

        st.subheader("Delete a KPI")
        with st.form("del_kpi"):
            kd = st.selectbox("KPI", prog["id"].tolist(),
                              format_func=lambda i: prog.set_index("id").loc[i, "KPI"])
            ok = st.checkbox("Yes, delete this KPI")
            if st.form_submit_button("Delete KPI"):
                if ok:
                    core.delete_kpi(conn, kd)
                    st.success("Deleted. Refresh the page to update the list.")
                else:
                    st.error("Tick the box to confirm.")


# ---------------------------------------------------------------- Dashboard
elif page == "Dashboard":
    st.title("Dashboard")
    choice = st.radio("Period", ["This month", "Last 30 days", "This year", "Custom"], horizontal=True)
    if choice == "This month":
        start, end = today.replace(day=1), today
    elif choice == "Last 30 days":
        start, end = today - timedelta(days=29), today
    elif choice == "This year":
        start, end = date(today.year, 1, 1), today
    else:
        c1, c2 = st.columns(2)
        start = c1.date_input("From", today - timedelta(days=29))
        end = c2.date_input("To", today)
    if start > end:
        st.error("'From' date must not be after 'To' date.")
        st.stop()

    s = core.summary(conn, start, end)
    m = st.columns(5)
    m[0].metric("Hours logged", s["total_hours"])
    m[1].metric("Tasks completed", s["tasks_done"])
    m[2].metric("Tasks open", s["tasks_open"])
    m[3].metric("Carried forward (open)", s["carried_open"])
    m[4].metric("Additional work %", f"{s['additional_pct']}%")

    if s["total_hours"] == 0:
        st.info("No time logged in this period.")
    else:
        l, r = st.columns(2)
        with l:
            st.subheader("Hours by category")
            st.bar_chart(s["by_category_hours"])
        with r:
            st.subheader("Hours per day")
            st.bar_chart(s["hours_by_day"])

    st.subheader("Planned vs actual (tasks completed in period)")
    done = s["done_df"]
    if done.empty or done["planned_min"].sum() == 0:
        st.write("No completed tasks with a planned time in this period.")
    else:
        comp = done[done["planned_min"] > 0][["title", "planned_min", "actual_min"]].copy()
        comp["variance_min"] = comp["actual_min"] - comp["planned_min"]
        st.dataframe(comp, hide_index=True)
        st.caption("Positive variance means the task took longer than planned. Additional (unplanned) "
                   "tasks have no plan and are left out of this comparison.")

    st.subheader("Longest-running open tasks")
    tdf = core.tasks_df(conn)
    if tdf.empty or tdf[tdf["status"] != "Done"].empty:
        st.write("No open tasks.")
    else:
        st.dataframe(tdf[tdf["status"] != "Done"].sort_values("age_days", ascending=False)
                     [["title", "client", "original_date", "age_days", "carried_count", "actual_min"]].head(10),
                     hide_index=True)

    st.subheader("KPI achievement")
    kp = core.kpi_progress(conn, end.year, end.month)
    if kp.empty:
        st.write("No KPIs set.")
    else:
        st.dataframe(kp.drop(columns=["id"]), hide_index=True)


# ------------------------------------------------------------------- Report
elif page == "Report":
    st.title("Report")
    st.write("Create a summary you can keep for an appraisal or a discussion with your partner.")
    c1, c2 = st.columns(2)
    first = today.replace(day=1)
    start = c1.date_input("From", first)
    end = c2.date_input("To", today)
    who = st.text_input("Name on report", "CA Sapan")
    if start > end:
        st.error("'From' date must not be after 'To' date.")
    else:
        tag = f"{core.iso(start)}_to_{core.iso(end)}"
        with tempfile.TemporaryDirectory() as tmp:
            xp = core.export_excel(conn, os.path.join(tmp, "r.xlsx"), start, end)
            wp = core.export_word(conn, os.path.join(tmp, "r.docx"), start, end, who)
            xb, wb = Path(xp).read_bytes(), Path(wp).read_bytes()
        d1, d2 = st.columns(2)
        d1.download_button("⬇ Download Excel", xb, file_name=f"work_summary_{tag}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        d2.download_button("⬇ Download Word", wb, file_name=f"work_summary_{tag}.docx",
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        s = core.summary(conn, start, end)
        st.caption(f"Preview: {s['total_hours']} hours logged · {s['tasks_done']} tasks completed · "
                   f"{s['additional_pct']}% additional work")

st.divider()
st.caption(core.CREDIT)
