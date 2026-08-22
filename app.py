"""
app.py
------
H P M S & Associates - CA Firm Practice Management System

Run with:   streamlit run app.py

Screen map
----------
Admin    : Dashboard | Task Tracker | Delegate Task | Client 360 |
           Clients | Team | Task Master | Billing & Collection | Analytics
Employee : My Tasks | My Completed Tasks

Every database read for an employee is filtered inside database.py, so an
employee simply cannot fetch another employee's tasks or any billing data.
"""

from datetime import date, datetime, timedelta

import urllib.parse
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

import auth
import database as db

# --------------------------------------------------------------------------
# PAGE SETUP
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="H P M S & Associates - Practice Management",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Firm colour scheme: dark navy / white / light grey / blue accent
CSS = """
<style>
    .main .block-container { padding-top: 1.5rem; }

    .hpms-header {
        background: linear-gradient(90deg, #0B1F3A 0%, #14345C 100%);
        padding: 18px 26px; border-radius: 8px; margin-bottom: 18px;
    }
    .hpms-header h1 {
        color: #FFFFFF; font-size: 30px; letter-spacing: 4px;
        margin: 0; font-weight: 700;
    }
    .hpms-header p {
        color: #B9CBE4; font-size: 15px; margin: 4px 0 0 0; letter-spacing: 1px;
    }

    .kpi {
        background: #FFFFFF; border: 1px solid #E3E8EF; border-left: 6px solid #1F6FEB;
        border-radius: 8px; padding: 14px 16px; height: 100%;
        box-shadow: 0 1px 2px rgba(16,24,40,0.05);
    }
    .kpi .label { color: #5B6B82; font-size: 12.5px; text-transform: uppercase;
                  letter-spacing: .6px; margin-bottom: 6px; }
    .kpi .value { color: #0B1F3A; font-size: 26px; font-weight: 700; line-height: 1.1; }
    .kpi.red    { border-left-color: #D92D20; }
    .kpi.orange { border-left-color: #F79009; }
    .kpi.green  { border-left-color: #12A150; }
    .kpi.grey   { border-left-color: #98A2B3; }

    .section-title {
        color: #0B1F3A; font-size: 20px; font-weight: 700;
        border-bottom: 2px solid #E3E8EF; padding-bottom: 6px; margin: 8px 0 14px 0;
    }
    .client-card {
        background:#F7F9FC; border:1px solid #E3E8EF; border-radius:8px;
        padding:14px 18px; margin-bottom:12px;
    }
    .client-card b { color:#0B1F3A; }
    .stButton>button { border-radius: 6px; }
    div[data-testid="stSidebarNav"] { display: none; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# Make sure the database and the task master exist before anything else
db.init_db()


# --------------------------------------------------------------------------
# SMALL UI HELPERS
# --------------------------------------------------------------------------
def firm_header():
    st.markdown(
        """<div class="hpms-header">
               <h1>H P M S &amp; Associates</h1>
               <p>Practice Management System</p>
           </div>""",
        unsafe_allow_html=True,
    )


def kpi(col, label, value, tone="blue"):
    col.markdown(
        f"""<div class="kpi {tone}">
                <div class="label">{label}</div>
                <div class="value">{value}</div>
            </div>""",
        unsafe_allow_html=True,
    )


def section(title):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def rupees(amount):
    """Format a number in the Indian style, e.g. 1,25,000."""
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return "₹0"
    negative = amount < 0
    amount = abs(amount)
    whole = f"{amount:,.0f}"
    # Convert 1,250,000 -> 12,50,000
    parts = whole.replace(",", "")
    if len(parts) > 3:
        last3 = parts[-3:]
        rest = parts[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        whole = ",".join(groups + [last3])
    return ("-₹" if negative else "₹") + whole


def task_flag(status, due_date, priority="Normal"):
    """Colour dot for a task, as required by the specification."""
    if status == "Completed":
        return "🟢"
    try:
        due = datetime.strptime(str(due_date), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        due = None
    if due and due < date.today():
        return "🔴"                       # Overdue
    if priority == "Urgent" or (due and due == date.today()):
        return "🟠"                       # Urgent / due today
    if status in ("Waiting for Client", "Waiting for Information",
                  "Query Raised", "On Hold"):
        return "🟡"                       # Waiting
    if status in ("In Progress", "Under Review"):
        return "🔵"                       # In progress
    return "⚪"                            # Not started


def add_task_flags(df):
    """Add the helper columns used by every task table."""
    if df.empty:
        return df
    out = df.copy()
    out["due_dt"] = pd.to_datetime(out["due_date"], errors="coerce").dt.date
    today = date.today()
    out["is_overdue"] = (out["due_dt"] < today) & (out["status"] != "Completed")
    out["is_due_today"] = (out["due_dt"] == today) & (out["status"] != "Completed")
    out["is_upcoming"] = (
        (out["due_dt"] > today)
        & (out["due_dt"] <= today + timedelta(days=7))
        & (out["status"] != "Completed")
    )
    out["flag"] = out.apply(
        lambda r: task_flag(r["status"], r["due_date"], r["priority"]), axis=1)
    out["progress_txt"] = out["progress"].astype(int).astype(str) + "%"
    return out


def show_task_table(df, columns, height=None):
    """Display a task DataFrame with friendly column names."""
    if df.empty:
        st.info("No records found for the selected filters.")
        return
    view = df[list(columns.keys())].rename(columns=columns)
    if height is not None:
        st.dataframe(view, use_container_width=True, hide_index=True, height=height)
    else:
        st.dataframe(view, use_container_width=True, hide_index=True)



def date_input_safe(label, value=None, key=None):
    return st.date_input(label, value=value or date.today(), key=key,
                         format="DD/MM/YYYY")


def to_date(value):
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return date.today()


# --------------------------------------------------------------------------
# LOGIN / SIGNUP SCREEN
# --------------------------------------------------------------------------
def login_screen():
    firm_header()
    left, mid, right = st.columns([1, 1.4, 1])

    with mid:
        first_time = auth.signup_is_open()
        if first_time:
            st.warning("No account exists yet. The first account you create "
                       "will automatically become the **Admin**.")

        tab_login, tab_signup = st.tabs(["🔐 Login", "📝 Sign Up"])

        # ------------------------- LOGIN ------------------------------
        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="name@hpms.in")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login", use_container_width=True,
                                                  type="primary")
            if submitted:
                user, error = auth.login(email, password)
                if error:
                    st.error(error)
                else:
                    st.session_state.user = user
                    st.session_state.page = ("Dashboard" if user["is_admin"]
                                             else "My Tasks")
                    st.rerun()

        # ------------------------- SIGN UP ----------------------------
        with tab_signup:
            if not first_time:
                st.caption("Only email addresses added by the Admin in the "
                           "Employee Master can register.")
            with st.form("signup_form"):
                s_name = st.text_input("Full Name")
                s_email = st.text_input("Email ")
                s_pass = st.text_input("Password ", type="password",
                                       help="Minimum 6 characters")
                s_pass2 = st.text_input("Confirm Password", type="password")
                created = st.form_submit_button("Sign Up", use_container_width=True)
            if created:
                if s_pass != s_pass2:
                    st.error("The two passwords do not match.")
                else:
                    ok, message = auth.signup(s_name, s_email, s_pass)
                    (st.success if ok else st.error)(message)

        # --------------- First-run convenience: demo data --------------
        if first_time:
            st.divider()
            st.caption("For demonstration purposes you may load fictional sample data.")
            if st.button("Load Demo Data", use_container_width=True):
                ok, message = db.load_demo_data()
                if ok:
                    st.success(message)
                else:
                    st.warning(message)


# --------------------------------------------------------------------------
# EMPLOYEE SCREENS
# --------------------------------------------------------------------------
def page_my_tasks(user, completed=False):
    section("My Completed Tasks" if completed else "My Tasks")

    df = add_task_flags(db.get_tasks_df(user))     # already restricted by SQL
    if df.empty:
        st.info("No tasks have been assigned to you yet.")
        return

    df = df[df["status"] == "Completed"] if completed else df[df["status"] != "Completed"]
    if df.empty:
        st.info("Nothing to show here at the moment.")
        return

    if not completed:
        c1, c2, c3 = st.columns(3)
        kpi(c1, "Pending Tasks", len(df))
        kpi(c2, "Overdue", int(df["is_overdue"].sum()), "red")
        kpi(c3, "Due Today", int(df["is_due_today"].sum()), "orange")
        st.write("")

    show_task_table(df, {
        "flag": " ", "client_name": "Client", "task_name": "Task",
        "due_date": "Due Date", "priority": "Priority",
        "progress_txt": "Progress", "status": "Status",
        "latest_remark": "Latest Remark",
    })

    if completed:
        return

    st.divider()
    section("Update a Task")

    options = {
        f"#{r.id} · {r.client_name} · {r.task_name} (due {r.due_date})": r.id
        for r in df.itertuples()
    }
    chosen = st.selectbox("Select your task", list(options.keys()))
    task_id = options[chosen]
    task = db.get_task(user, task_id)
    if task is None:
        st.error("You are not authorised to view this task.")
        return

    a, b = st.columns([1, 1])
    with a:
        st.markdown(
            f"""<div class="client-card">
            <b>Client:</b> {task['client_name']}<br>
            <b>Task:</b> {task['task_name']} ({task['category']})<br>
            <b>Financial Year:</b> {task['financial_year'] or '-'}<br>
            <b>Assigned On:</b> {task['assigned_date']}<br>
            <b>Due Date:</b> {task['due_date']} &nbsp;|&nbsp;
            <b>Priority:</b> {task['priority']}<br>
            <b>Instructions:</b> {task['instructions'] or '-'}
            </div>""", unsafe_allow_html=True)

    with b:
        with st.form("update_task_form"):
            new_status = st.selectbox(
                "Status", db.STATUSES, index=db.STATUSES.index(task["status"]))
            current_progress = int(task["progress"])
            new_progress = st.select_slider(
                "Progress", options=db.PROGRESS_OPTIONS,
                value=current_progress if current_progress in db.PROGRESS_OPTIONS else 0)
            remark = st.text_area(
                "Remark", placeholder="e.g. Data received from client.")
            saved = st.form_submit_button("Save Update", type="primary",
                                          use_container_width=True)
        if saved:
            if not remark.strip():
                st.error("Please write a short remark describing the update.")
            else:
                ok = db.update_task_progress(user, task_id, new_status,
                                             new_progress, remark)
                if ok:
                    st.success("Task updated and saved in the history.")
                    st.rerun()
                else:
                    st.error("You are not authorised to update this task.")

    section("Task History")
    hist = db.get_task_history_df(user, task_id)
    if hist.empty:
        st.info("No history yet.")
    else:
        st.dataframe(hist.rename(columns={
            "updated_at": "Date / Time", "user_name": "By",
            "old_status": "From", "new_status": "To",
            "progress": "Progress %", "remark": "Remark"}),
            use_container_width=True, hide_index=True)


# --------------------------------------------------------------------------
# ADMIN - DASHBOARD
# --------------------------------------------------------------------------
def page_dashboard(user):
    section("Admin Dashboard")

    tasks = add_task_flags(db.get_tasks_df(user))
    bills = db.get_bills_df()
    not_billed = db.get_completed_not_billed_df()

    # ---------------- Work KPI cards ----------------
    st.markdown("**Work Position**")
    c = st.columns(7)
    total_active = 0 if tasks.empty else int((tasks["status"] != "Completed").sum())
    completed = 0 if tasks.empty else int((tasks["status"] == "Completed").sum())
    in_progress = 0 if tasks.empty else int((tasks["status"] == "In Progress").sum())
    waiting = 0 if tasks.empty else int(tasks["status"].isin(
        ["Waiting for Client", "Waiting for Information", "Query Raised"]).sum())
    due_today = 0 if tasks.empty else int(tasks["is_due_today"].sum())
    overdue = 0 if tasks.empty else int(tasks["is_overdue"].sum())

    kpi(c[0], "Active Tasks", total_active)
    kpi(c[1], "Completed", completed, "green")
    kpi(c[2], "In Progress", in_progress)
    kpi(c[3], "Waiting for Client", waiting, "orange")
    kpi(c[4], "Due Today", due_today, "orange")
    kpi(c[5], "Overdue", overdue, "red")
    kpi(c[6], "Completed – Not Billed", len(not_billed), "orange")

    # ---------------- Financial KPI cards ----------------
    st.write("")
    st.markdown("**Billing & Collection Position**")
    f = st.columns(5)
    total_billed = 0 if bills.empty else float(bills["total_amount"].sum())
    total_received = 0 if bills.empty else float(bills["received"].sum())
    outstanding = total_billed - total_received
    part_paid = 0 if bills.empty else int((bills["payment_status"] == "Partially Paid").sum())

    if bills.empty:
        overdue_recv = 0.0
    else:
        b = bills.copy()
        b["due_dt"] = pd.to_datetime(b["due_date"], errors="coerce").dt.date
        overdue_recv = float(b[(b["due_dt"] < date.today()) &
                               (b["outstanding"] > 0)]["outstanding"].sum())

    kpi(f[0], "Total Billed", rupees(total_billed))
    kpi(f[1], "Total Collection", rupees(total_received), "green")
    kpi(f[2], "Total Outstanding", rupees(outstanding), "red")
    kpi(f[3], "Partially Paid Bills", part_paid, "orange")
    kpi(f[4], "Overdue Receivables", rupees(overdue_recv), "red")

    st.divider()

    # ---------------- The four business exceptions ----------------
    section("Business Controls – Points needing attention")
    t1, t2, t3, t4 = st.tabs([
        f"🔴 Overdue Work ({overdue})",
        f"🟠 Completed but Not Billed ({len(not_billed)})",
        "🔴 Payment Overdue",
        f"🟡 Waiting for Client ({waiting})",
    ])

    with t1:
        show_task_table(tasks[tasks["is_overdue"]] if not tasks.empty else tasks, {
            "flag": " ", "client_name": "Client", "task_name": "Task",
            "employee_name": "Delegated To", "due_date": "Due Date",
            "priority": "Priority", "status": "Status", "latest_remark": "Latest Remark"})

    with t2:
        if not_billed.empty:
            st.success("No completed work is pending for billing.")
        else:
            st.dataframe(not_billed.rename(columns={
                "client_name": "Client", "task_name": "Task",
                "employee_name": "Completed By", "due_date": "Due Date",
                "updated_at": "Completed On"})[
                ["Client", "Task", "Completed By", "Due Date", "Completed On"]],
                use_container_width=True, hide_index=True)

    with t3:
        if bills.empty:
            st.info("No bills recorded yet.")
        else:
            b = bills.copy()
            b["due_dt"] = pd.to_datetime(b["due_date"], errors="coerce").dt.date
            od = b[(b["due_dt"] < date.today()) & (b["outstanding"] > 0)]
            if od.empty:
                st.success("No overdue receivables.")
            else:
                st.dataframe(od[["client_name", "bill_number", "bill_date",
                                 "total_amount", "received", "outstanding",
                                 "due_date", "payment_status"]].rename(columns={
                    "client_name": "Client", "bill_number": "Bill No.",
                    "bill_date": "Bill Date", "total_amount": "Bill Amount",
                    "received": "Received", "outstanding": "Outstanding",
                    "due_date": "Payment Due", "payment_status": "Status"}),
                    use_container_width=True, hide_index=True)

    with t4:
        if tasks.empty:
            st.info("No tasks yet.")
        else:
            w = tasks[tasks["status"].isin(
                ["Waiting for Client", "Waiting for Information", "Query Raised"])]
            show_task_table(w, {
                "flag": " ", "client_name": "Client", "task_name": "Task",
                "employee_name": "Delegated To", "due_date": "Due Date",
                "status": "Status", "latest_remark": "Latest Remark"})

    st.divider()

    # ---------------- Team-wise and client-wise views ----------------
    left, right = st.columns(2)

    with left:
        section("Team-wise Position")
        if tasks.empty:
            st.info("No tasks yet.")
        else:
            st.dataframe(team_summary(tasks), use_container_width=True,
                         hide_index=True)

    with right:
        section("Client-wise Position")
        st.dataframe(client_summary(tasks, bills, not_billed),
                     use_container_width=True, hide_index=True)


def team_summary(tasks):
    """Employee-wise workload table (works on every pandas version)."""
    rows = []
    if tasks.empty:
        return pd.DataFrame(columns=["Employee", "Total Tasks", "Pending",
                                     "Completed", "Overdue"])
    for employee, g in tasks.groupby("employee_name"):
        rows.append({
            "Employee": employee,
            "Total Tasks": len(g),
            "Pending": int((g["status"] != "Completed").sum()),
            "Completed": int((g["status"] == "Completed").sum()),
            "Overdue": int(g["is_overdue"].sum()),
        })
    return pd.DataFrame(rows).sort_values("Pending", ascending=False)


def client_summary(tasks, bills, not_billed):
    """Client-wise management view used on the dashboard."""
    clients = db.get_clients_df()
    rows = []
    for _, cl in clients.iterrows():
        ct = tasks[tasks["client_id"] == cl["id"]] if not tasks.empty else pd.DataFrame()
        cb = bills[bills["client_id"] == cl["id"]] if not bills.empty else pd.DataFrame()
        nb = (not_billed[not_billed["client_name"] == cl["client_name"]]
              if not not_billed.empty else pd.DataFrame())
        rows.append({
            "Client": cl["client_name"],
            "Total Tasks": len(ct),
            "Pending": 0 if ct.empty else int((ct["status"] != "Completed").sum()),
            "Completed": 0 if ct.empty else int((ct["status"] == "Completed").sum()),
            "Billing Pending": len(nb),
            "Outstanding": 0.0 if cb.empty else float(cb["outstanding"].sum()),
        })
    out = pd.DataFrame(rows)
    if not out.empty:
        out["Outstanding"] = out["Outstanding"].map(rupees)
    return out


# --------------------------------------------------------------------------
# ADMIN - MASTER TASK TRACKER
# --------------------------------------------------------------------------
def page_task_tracker(user):
    section("Task Tracker")

    tasks = add_task_flags(db.get_tasks_df(user))
    if tasks.empty:
        st.info("No tasks have been created yet. Use **Delegate Task** to begin.")
        return

    f1, f2, f3 = st.columns(3)
    client_f = f1.multiselect("Client", sorted(tasks["client_name"].unique()))
    emp_f = f2.multiselect("Employee", sorted(tasks["employee_name"].unique()))
    task_f = f3.multiselect("Task", sorted(tasks["task_name"].unique()))

    f4, f5, f6 = st.columns(3)
    status_f = f4.multiselect("Status", db.STATUSES)
    prio_f = f5.multiselect("Priority", db.PRIORITIES)
    quick = f6.radio("Quick View",
                     ["All", "Pending Only", "Overdue Only", "Due Today",
                      "Upcoming (7 days)", "Completed Only"],
                     horizontal=False)

    f7, f8, f9 = st.columns([1, 1, 1])
    use_date = f7.checkbox("Filter by due-date range")
    from_date = f8.date_input("From", value=date.today() - timedelta(days=30),
                              format="DD/MM/YYYY", disabled=not use_date,
                              key="tt_from")
    to_date_ = f9.date_input("To", value=date.today() + timedelta(days=30),
                             format="DD/MM/YYYY", disabled=not use_date,
                             key="tt_to")

    df = tasks.copy()
    if client_f:
        df = df[df["client_name"].isin(client_f)]
    if emp_f:
        df = df[df["employee_name"].isin(emp_f)]
    if task_f:
        df = df[df["task_name"].isin(task_f)]
    if status_f:
        df = df[df["status"].isin(status_f)]
    if prio_f:
        df = df[df["priority"].isin(prio_f)]
    if quick == "Pending Only":
        df = df[df["status"] != "Completed"]
    elif quick == "Overdue Only":
        df = df[df["is_overdue"]]
    elif quick == "Due Today":
        df = df[df["is_due_today"]]
    elif quick == "Upcoming (7 days)":
        df = df[df["is_upcoming"]]
    elif quick == "Completed Only":
        df = df[df["status"] == "Completed"]
    if use_date:
        df = df[(df["due_dt"] >= from_date) & (df["due_dt"] <= to_date_)]

    k = st.columns(4)
    kpi(k[0], "Tasks Shown", len(df))
    kpi(k[1], "Pending", int((df["status"] != "Completed").sum()))
    kpi(k[2], "Overdue", int(df["is_overdue"].sum()), "red")
    kpi(k[3], "Completed", int((df["status"] == "Completed").sum()), "green")
    st.write("")

    show_task_table(df, {
        "flag": " ", "id": "Task ID", "client_name": "Client", "task_name": "Task",
        "employee_name": "Delegated Staff", "due_date": "Due Date",
        "priority": "Priority", "progress_txt": "Progress",
        "status": "Current Status", "latest_remark": "Latest Remark"})

    st.caption("🔴 Overdue  🟠 Urgent / Due today  🟡 Waiting  "
               "🔵 In Progress  🟢 Completed  ⚪ Not Started")

    if df.empty:
        return

    st.divider()
    section("Open a Task – History, Update & Reassign")

    options = {f"#{r.id} · {r.client_name} · {r.task_name} · {r.employee_name}": r.id
               for r in df.itertuples()}
    chosen = st.selectbox("Select a task", list(options.keys()))
    task_id = options[chosen]
    task = db.get_task(user, task_id)

    a, b, c = st.columns([1.2, 1, 1])
    with a:
        st.markdown(
            f"""<div class="client-card">
            <b>Client:</b> {task['client_name']}<br>
            <b>Task:</b> {task['task_name']}<br>
            <b>Delegated To:</b> {task['employee_name']}<br>
            <b>Due Date:</b> {task['due_date']} &nbsp;|&nbsp;
            <b>Priority:</b> {task['priority']}<br>
            <b>Status:</b> {task['status']} ({int(task['progress'])}%)<br>
            <b>Instructions:</b> {task['instructions'] or '-'}
            </div>""", unsafe_allow_html=True)

    with b:
        st.markdown("**Update Status / Remark**")
        with st.form("admin_update_task"):
            ns = st.selectbox("Status", db.STATUSES,
                              index=db.STATUSES.index(task["status"]))
            cp = int(task["progress"])
            np_ = st.select_slider("Progress", options=db.PROGRESS_OPTIONS,
                                   value=cp if cp in db.PROGRESS_OPTIONS else 0)
            rm = st.text_area("Remark", key="admin_remark")
            if st.form_submit_button("Save Update", type="primary",
                                     use_container_width=True):
                if not rm.strip():
                    st.error("Please write a remark.")
                else:
                    db.update_task_progress(user, task_id, ns, np_, rm)
                    st.success("Updated.")
                    st.rerun()

    with c:
        st.markdown("**Reassign Task**")
        emps = db.get_employees_df(only_active=True)
        emap = {r["name"]: r["id"] for _, r in emps.iterrows()}
        with st.form("reassign_form"):
            new_emp = st.selectbox("Assign To", list(emap.keys()))
            note = st.text_input("Reason (optional)")
            if st.form_submit_button("Reassign", use_container_width=True):
                db.reassign_task(task_id, emap[new_emp], user, note)
                st.success(f"Task reassigned to {new_emp}.")
                st.rerun()

    section("Task History")
    hist = db.get_task_history_df(user, task_id)
    st.dataframe(hist.rename(columns={
        "updated_at": "Date / Time", "user_name": "By", "old_status": "From",
        "new_status": "To", "progress": "Progress %", "remark": "Remark"}),
        use_container_width=True, hide_index=True)


# --------------------------------------------------------------------------
# ADMIN - DELEGATE TASK
# --------------------------------------------------------------------------
def page_delegate_task(user):
    section("Delegate Task")

    clients = db.get_clients_df(only_active=True)
    task_types = db.get_task_types_df()
    employees = db.get_employees_df(only_active=True)

    if clients.empty or employees.empty:
        st.warning("Please add at least one client and one employee before "
                   "delegating a task.")
        return

    cmap = {f"{r['client_code']} – {r['client_name']}": r["id"]
            for _, r in clients.iterrows()}
    tmap = {f"{r['category']} → {r['task_name']}": r["id"]
            for _, r in task_types.iterrows()}
    emap = {f"{r['name']} ({r['role']})": r["id"] for _, r in employees.iterrows()}

    with st.form("delegate_form"):
        c1, c2 = st.columns(2)
        client = c1.selectbox("Client", list(cmap.keys()))
        task_type = c2.selectbox("Task", list(tmap.keys()))

        c3, c4, c5 = st.columns(3)
        assignee = c3.selectbox("Assigned To", list(emap.keys()))
        priority = c4.selectbox("Priority", db.PRIORITIES, index=1)
        fy = c5.selectbox("Financial Year", db.FINANCIAL_YEARS,
                          index=db.FINANCIAL_YEARS.index("2026-27"))

        c6, c7 = st.columns(2)
        assigned_date = c6.date_input("Assignment Date", value=date.today(),
                                      format="DD/MM/YYYY")
        due = c7.date_input("Due Date", value=date.today() + timedelta(days=7),
                            format="DD/MM/YYYY")

        instructions = st.text_area("Instructions / Notes",
                                    placeholder="Any specific instruction for the staff...")
        submitted = st.form_submit_button("Delegate Task", type="primary",
                                          use_container_width=True)

    if submitted:
        if due < assigned_date:
            st.error("Due date cannot be earlier than the assignment date.")
        else:
            db.create_task(cmap[client], tmap[task_type], emap[assignee], user["id"],
                           assigned_date.isoformat(), due.isoformat(),
                           priority, fy, instructions)
            st.success(f"Task delegated to {assignee} successfully.")

    st.divider()
    section("Recently Delegated Tasks")
    recent = add_task_flags(db.get_tasks_df(user)).sort_values("id", ascending=False).head(10)
    show_task_table(recent, {
        "flag": " ", "client_name": "Client", "task_name": "Task",
        "employee_name": "Delegated To", "due_date": "Due Date",
        "priority": "Priority", "status": "Status"})


# --------------------------------------------------------------------------
# ADMIN - CLIENT 360
# --------------------------------------------------------------------------
def page_client_360(user):
    section("Client 360°")

    clients = db.get_clients_df()
    if clients.empty:
        st.info("No clients added yet.")
        return

    cmap = {f"{r['client_code']} – {r['client_name']}": r["id"]
            for _, r in clients.iterrows()}
    chosen = st.selectbox("Select Client", list(cmap.keys()))
    cid = cmap[chosen]
    cl = clients[clients["id"] == cid].iloc[0]

    st.markdown(
        f"""<div class="client-card">
        <b style="font-size:18px">{cl['client_name']}</b> &nbsp;
        <span style="color:#5B6B82">({cl['client_type']} · {cl['client_code']})</span><br><br>
        <b>Contact Person:</b> {cl['contact_person'] or '-'} &nbsp;&nbsp;|&nbsp;&nbsp;
        <b>Mobile:</b> {cl['mobile'] or '-'} &nbsp;&nbsp;|&nbsp;&nbsp;
        <b>Email:</b> {cl['email'] or '-'}<br>
        <b>PAN:</b> {cl['pan'] or '-'} &nbsp;&nbsp;|&nbsp;&nbsp;
        <b>GSTIN:</b> {cl['gstin'] or '-'} &nbsp;&nbsp;|&nbsp;&nbsp;
        <b>Status:</b> {'Active' if cl['active'] else 'Inactive'}
        </div>""", unsafe_allow_html=True)

    # ------------------------- Work status -------------------------
    section("Work Status")
    tasks = add_task_flags(db.get_tasks_df(user))
    ct = tasks[tasks["client_id"] == cid] if not tasks.empty else tasks

    k = st.columns(4)
    kpi(k[0], "Total Tasks", len(ct))
    kpi(k[1], "Pending", 0 if ct.empty else int((ct["status"] != "Completed").sum()))
    kpi(k[2], "Completed", 0 if ct.empty else int((ct["status"] == "Completed").sum()),
        "green")
    kpi(k[3], "Overdue", 0 if ct.empty else int(ct["is_overdue"].sum()), "red")
    st.write("")

    show_task_table(ct, {
        "flag": " ", "task_name": "Task", "employee_name": "Delegated To",
        "due_date": "Due Date", "progress_txt": "Progress", "status": "Status",
        "latest_remark": "Latest Remark"})

    # ------------------------- Billing -------------------------
    st.divider()
    section("Billing & Collection")
    bills = db.get_bills_df(client_id=cid)

    total_billed = 0 if bills.empty else float(bills["total_amount"].sum())
    total_recv = 0 if bills.empty else float(bills["received"].sum())
    k = st.columns(3)
    kpi(k[0], "Total Billed", rupees(total_billed))
    kpi(k[1], "Total Received", rupees(total_recv), "green")
    kpi(k[2], "Total Outstanding", rupees(total_billed - total_recv), "red")
    st.write("")

    if bills.empty:
        st.info("No bills raised for this client yet.")
    else:
        st.dataframe(bills[["bill_number", "task_name", "bill_date", "total_amount",
                            "received", "outstanding", "payment_status"]].rename(columns={
            "bill_number": "Bill No.", "task_name": "Task", "bill_date": "Bill Date",
            "total_amount": "Bill Amount", "received": "Received",
            "outstanding": "Outstanding", "payment_status": "Payment Status"}),
            use_container_width=True, hide_index=True)

    nb = db.get_completed_not_billed_df()
    nb = nb[nb["client_name"] == cl["client_name"]]
    if not nb.empty:
        st.warning(f"**Completed – Billing Pending:** {len(nb)} task(s) → "
                   + ", ".join(nb["task_name"].tolist()))


# --------------------------------------------------------------------------
# ADMIN - CLIENT MASTER
# --------------------------------------------------------------------------
def page_clients(user):
    section("Client Master")
    tab_list, tab_add, tab_edit = st.tabs(["📋 View / Search", "➕ Add Client",
                                           "✏️ Edit Client"])

    with tab_list:
        clients = db.get_clients_df()
        if clients.empty:
            st.info("No clients added yet.")
        else:
            search = st.text_input("Search (name, code, PAN, GSTIN, contact)")
            view = clients.copy()
            if search:
                s = search.lower()
                mask = view.apply(
                    lambda r: s in " ".join(str(v).lower() for v in r.values), axis=1)
                view = view[mask]
            view["Status"] = view["active"].map({1: "Active", 0: "Inactive"})
            st.dataframe(view[["client_code", "client_name", "client_type", "pan",
                               "gstin", "contact_person", "mobile", "email", "Status"]
                              ].rename(columns={
                "client_code": "Code", "client_name": "Client Name",
                "client_type": "Type", "pan": "PAN", "gstin": "GSTIN",
                "contact_person": "Contact Person", "mobile": "Mobile",
                "email": "Email"}), use_container_width=True, hide_index=True)

    with tab_add:
        with st.form("add_client_form"):
            c1, c2 = st.columns(2)
            code = c1.text_input("Client Code *", placeholder="C011", key="ac_code")
            name = c2.text_input("Client Name *", key="ac_name")
            c3, c4 = st.columns(2)
            pan = c3.text_input("PAN (optional)", key="ac_pan")
            gstin = c4.text_input("GSTIN (optional)", key="ac_gstin")
            c5, c6, c7 = st.columns(3)
            contact = c5.text_input("Contact Person", key="ac_contact")
            mobile = c6.text_input("Mobile", key="ac_mobile")
            email = c7.text_input("Email", key="ac_email")
            c8, c9 = st.columns(2)
            ctype = c8.selectbox("Client Type", db.CLIENT_TYPES, key="ac_type")
            active = c9.selectbox("Status", ["Active", "Inactive"], key="ac_active")
            if st.form_submit_button("Add Client", type="primary",
                                     use_container_width=True):
                if not code.strip() or not name.strip():
                    st.error("Client Code and Client Name are compulsory.")
                elif db.fetch_one("SELECT id FROM clients WHERE client_code = ?",
                                  (code.strip().upper(),)):
                    st.error("This client code already exists.")
                else:
                    db.add_client(code, name, pan, gstin, contact, mobile, email,
                                  ctype, 1 if active == "Active" else 0)
                    st.success(f"Client '{name}' added successfully.")
                    st.rerun()

    with tab_edit:
        clients = db.get_clients_df()
        if clients.empty:
            st.info("No clients to edit.")
            return
        cmap = {f"{r['client_code']} – {r['client_name']}": r["id"]
                for _, r in clients.iterrows()}
        chosen = st.selectbox("Select Client to edit", list(cmap.keys()),
                              key="edit_client_pick")
        row = clients[clients["id"] == cmap[chosen]].iloc[0]
        with st.form("edit_client_form"):
            c1, c2 = st.columns(2)
            code = c1.text_input("Client Code", value=row["client_code"], key="ec_code")
            name = c2.text_input("Client Name", value=row["client_name"], key="ec_name")
            c3, c4 = st.columns(2)
            pan = c3.text_input("PAN", value=row["pan"] or "", key="ec_pan")
            gstin = c4.text_input("GSTIN", value=row["gstin"] or "", key="ec_gstin")
            c5, c6, c7 = st.columns(3)
            contact = c5.text_input("Contact Person", value=row["contact_person"] or "",
                                    key="ec_contact")
            mobile = c6.text_input("Mobile", value=row["mobile"] or "", key="ec_mobile")
            email = c7.text_input("Email", value=row["email"] or "", key="ec_email")
            c8, c9 = st.columns(2)
            ctype = c8.selectbox("Client Type", db.CLIENT_TYPES,
                                 index=db.CLIENT_TYPES.index(row["client_type"])
                                 if row["client_type"] in db.CLIENT_TYPES else 0,
                                 key="ec_type")
            active = c9.selectbox("Status", ["Active", "Inactive"],
                                  index=0 if row["active"] else 1, key="ec_active")
            if st.form_submit_button("Save Changes", type="primary",
                                     use_container_width=True):
                db.update_client(int(row["id"]), code, name, pan, gstin, contact,
                                 mobile, email, ctype, 1 if active == "Active" else 0)
                st.success("Client details updated.")
                st.rerun()


# --------------------------------------------------------------------------
# ADMIN - TEAM / EMPLOYEE MASTER
# --------------------------------------------------------------------------
def page_team(user):
    section("Team – Employee Master")
    st.caption("Only the email addresses listed here are allowed to sign up.")

    tab_list, tab_add, tab_edit = st.tabs(["📋 Team List", "➕ Add Employee",
                                           "✏️ Edit Employee"])

    with tab_list:
        emps = db.get_employees_df()
        if emps.empty:
            st.info("No employees added yet.")
        else:
            registered = db.run_query("SELECT LOWER(email) AS email FROM users")
            reg = set(registered["email"].tolist())
            view = emps.copy()
            view["Status"] = view["active"].map({1: "Active", 0: "Inactive"})
            view["Account"] = view["email"].str.lower().map(
                lambda e: "Registered" if e in reg else "Not registered")
            st.dataframe(view[["name", "email", "role", "mobile", "Status", "Account"]
                              ].rename(columns={
                "name": "Employee Name", "email": "Email", "role": "Role",
                "mobile": "Mobile"}), use_container_width=True, hide_index=True)

            st.divider()
            section("Workload Summary")
            tasks = add_task_flags(db.get_tasks_df(user))
            if tasks.empty:
                st.info("No tasks delegated yet.")
            else:
                st.dataframe(team_summary(tasks), use_container_width=True,
                             hide_index=True)

    with tab_add:
        with st.form("add_emp_form"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Employee Name *", key="ae_name")
            email = c2.text_input("Email *", key="ae_email")
            c3, c4, c5 = st.columns(3)
            role = c3.selectbox("Role", db.EMPLOYEE_ROLES, key="ae_role")
            mobile = c4.text_input("Mobile Number", key="ae_mobile")
            active = c5.selectbox("Status", ["Active", "Inactive"], key="ae_active")
            if st.form_submit_button("Add Employee", type="primary",
                                     use_container_width=True):
                if not name.strip():
                    st.error("Employee name is compulsory.")
                elif not auth.is_valid_email(email):
                    st.error("Please enter a valid email address.")
                elif db.fetch_one(
                        "SELECT id FROM authorised_employees WHERE LOWER(email)=LOWER(?)",
                        (email.strip(),)):
                    st.error("This email address is already in the employee master.")
                else:
                    db.add_employee(name, email, role, mobile,
                                    1 if active == "Active" else 0)
                    st.success(f"{name} added. They may now sign up using {email}.")
                    st.rerun()

    with tab_edit:
        emps = db.get_employees_df()
        if emps.empty:
            st.info("No employees to edit.")
            return
        emap = {f"{r['name']} ({r['email']})": r["id"] for _, r in emps.iterrows()}
        chosen = st.selectbox("Select Employee", list(emap.keys()), key="edit_emp_pick")
        row = emps[emps["id"] == emap[chosen]].iloc[0]
        with st.form("edit_emp_form"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Employee Name", value=row["name"], key="ee_name")
            email = c2.text_input("Email", value=row["email"], key="ee_email")
            c3, c4, c5 = st.columns(3)
            role = c3.selectbox("Role", db.EMPLOYEE_ROLES,
                                index=db.EMPLOYEE_ROLES.index(row["role"])
                                if row["role"] in db.EMPLOYEE_ROLES else 0,
                                key="ee_role")
            mobile = c4.text_input("Mobile Number", value=row["mobile"] or "",
                                   key="ee_mobile")
            active = c5.selectbox("Status", ["Active", "Inactive"],
                                  index=0 if row["active"] else 1, key="ee_active")
            if st.form_submit_button("Save Changes", type="primary",
                                     use_container_width=True):
                db.update_employee(int(row["id"]), name, email, role, mobile,
                                   1 if active == "Active" else 0)
                st.success("Employee details updated.")
                st.rerun()


# --------------------------------------------------------------------------
# ADMIN - TASK MASTER
# --------------------------------------------------------------------------
def page_task_master(user):
    section("Task Master")
    types = db.get_task_types_df()

    left, right = st.columns([2, 1])
    with left:
        for category in types["category"].unique():
            with st.expander(f"{category}  ({len(types[types['category']==category])})",
                             expanded=False):
                st.write(", ".join(types[types["category"] == category]["task_name"]))

    with right:
        st.markdown("**➕ Add New Task Type**")
        with st.form("add_task_type"):
            existing = sorted(types["category"].unique().tolist())
            category = st.selectbox("Category", existing + ["+ New Category"])
            new_cat = ""
            if category == "+ New Category":
                new_cat = st.text_input("New Category Name")
            task_name = st.text_input("Task Name")
            if st.form_submit_button("Add Task Type", type="primary",
                                     use_container_width=True):
                final_cat = new_cat.strip() if category == "+ New Category" else category
                if not final_cat or not task_name.strip():
                    st.error("Please fill in both the category and the task name.")
                elif db.fetch_one("SELECT id FROM task_types WHERE task_name = ?",
                                  (task_name.strip(),)):
                    st.error("This task already exists in the master.")
                else:
                    db.add_task_type(final_cat, task_name)
                    st.success(f"'{task_name}' added under {final_cat}.")
                    st.rerun()

    st.divider()
    st.dataframe(types[["category", "task_name"]].rename(columns={
        "category": "Category", "task_name": "Task Name"}),
        use_container_width=True, hide_index=True, height=360)


def generate_invoice_html(bill, client):
    """Generate professional printable HTML Invoice with CA logo, firm address and HPMS branding."""
    prof_fees = float(bill.get("professional_fees") or 0)
    gst_amt = float(bill.get("gst_amount") or 0)
    other_chg = float(bill.get("other_charges") or 0)
    total_amt = float(bill.get("total_amount") or 0)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Invoice_{bill.get('bill_number')}</title>
<style>
    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; color: #1e293b; margin: 0; padding: 20px; }}
    .invoice-box {{ max-width: 800px; margin: auto; padding: 35px; border: 1px solid #cbd5e1; background: #ffffff; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
    .header-table {{ width: 100%; border-bottom: 2px solid #0B1F3A; padding-bottom: 15px; margin-bottom: 25px; }}
    .firm-name {{ font-size: 24px; font-weight: 800; color: #0B1F3A; letter-spacing: 1.5px; text-transform: uppercase; }}
    .firm-sub {{ font-size: 13px; color: #1F6FEB; font-weight: 700; letter-spacing: 1px; margin-top: 2px; text-transform: uppercase; }}
    .address-line {{ font-size: 12px; color: #475569; margin-top: 4px; font-weight: 500; }}
    .contact-line {{ font-size: 12px; color: #0B1F3A; margin-top: 2px; font-weight: 600; }}
    .inv-heading {{ font-size: 22px; font-weight: 800; color: #0B1F3A; text-align: right; text-transform: uppercase; letter-spacing: 1px; }}
    .meta-details {{ font-size: 13px; color: #475569; text-align: right; margin-top: 6px; line-height: 1.5; }}
    .client-card {{ background: #f1f5f9; border-radius: 6px; padding: 16px; margin-bottom: 25px; border-left: 4px solid #0B1F3A; }}
    .client-title {{ font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 700; letter-spacing: 0.5px; margin-bottom: 4px; }}
    .client-name {{ font-size: 18px; font-weight: 700; color: #0B1F3A; margin-bottom: 6px; }}
    .info-line {{ font-size: 13px; color: #334155; line-height: 1.6; }}
    .items-table {{ width: 100%; border-collapse: collapse; margin-bottom: 25px; }}
    .items-table th {{ background-color: #0B1F3A; color: #ffffff; padding: 10px 12px; text-align: left; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }}
    .items-table td {{ padding: 12px; border-bottom: 1px solid #e2e8f0; font-size: 14px; color: #334155; }}
    .total-row td {{ background-color: #EBF3FE; font-weight: 700; font-size: 16px; color: #0B1F3A; border-top: 2px solid #0B1F3A; border-bottom: 2px solid #0B1F3A; }}
    .signatory-box {{ margin-top: 50px; text-align: right; clear: both; page-break-inside: avoid; }}
    .sign-firm {{ font-size: 15px; font-weight: 800; color: #0B1F3A; text-transform: uppercase; }}
    .sign-title {{ font-size: 13px; color: #64748b; font-weight: 600; margin-bottom: 40px; }}
    .sign-auth {{ font-size: 14px; font-weight: 800; color: #0B1F3A; border-top: 1px solid #0B1F3A; display: inline-block; padding-top: 4px; width: 260px; text-align: center; }}
</style>
</head>
<body>
<div class="invoice-box">
    <table class="header-table">
        <tr>
            <td style="border:none; padding:0; vertical-align:middle; width: 68%;">
                <div style="display:flex; align-items:center;">
                    <svg width="65" height="65" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style="vertical-align: middle; margin-right: 15px; flex-shrink:0;">
                        <rect width="100" height="100" rx="12" fill="#0B1F3A"/>
                        <text x="50" y="58" font-family="'Segoe UI', Arial, sans-serif" font-weight="bold" font-size="42" fill="#FFFFFF" text-anchor="middle">CA</text>
                        <path d="M 20 62 L 40 82 L 85 30" fill="none" stroke="#22c55e" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    <div>
                        <div class="firm-name">H P M S &amp; ASSOCIATES</div>
                        <div class="firm-sub">Chartered Accountants</div>
                        <div class="address-line">A-27, COMMERCIAL MARKET, GOVINDPURAM, GHAZIABAD, UP-201013</div>
                        <div class="contact-line">Contact: 7290009815, 7290009816</div>
                    </div>
                </div>
            </td>
            <td style="border:none; padding:0; vertical-align:top; width: 32%;">
                <div class="inv-heading">TAX INVOICE</div>
                <div class="meta-details">
                    <b>Invoice No:</b> {bill.get('bill_number')}<br>
                    <b>Invoice Date:</b> {bill.get('bill_date')}<br>
                    <b>Payment Due Date:</b> {bill.get('due_date') or '-'}
                </div>
            </td>
        </tr>
    </table>

    <div class="client-card">
        <div class="client-title">Billed To Client</div>
        <div class="client-name">{client.get('client_name')}</div>
        <div class="info-line">
            <b>Code:</b> {client.get('client_code')} ({client.get('client_type')}) &nbsp;&nbsp;|&nbsp;&nbsp;
            <b>Contact Person:</b> {client.get('contact_person') or '-'}<br>
            <b>Mobile:</b> {client.get('mobile') or '-'} &nbsp;&nbsp;|&nbsp;&nbsp;
            <b>Email:</b> {client.get('email') or '-'}<br>
            <b>PAN:</b> {client.get('pan') or '-'} &nbsp;&nbsp;|&nbsp;&nbsp;
            <b>GSTIN:</b> {client.get('gstin') or '-'}
        </div>
    </div>

    <table class="items-table">
        <thead>
            <tr>
                <th style="width: 70%;">Particulars / Description of Services</th>
                <th style="text-align: right; width: 30%;">Amount (₹)</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>
                    <b>{bill.get('task_name')}</b>
                    <br><span style="font-size:12px; color:#64748b;">{bill.get('remarks') or 'Professional Fee Charges'}</span>
                </td>
                <td style="text-align: right;">{rupees(prof_fees)}</td>
            </tr>
            <tr>
                <td>GST Amount (18% / Statutory Rate)</td>
                <td style="text-align: right;">{rupees(gst_amt)}</td>
            </tr>
            <tr>
                <td>Other Charges / Out-of-pocket Expenses</td>
                <td style="text-align: right;">{rupees(other_chg)}</td>
            </tr>
            <tr class="total-row">
                <td>TOTAL BILL AMOUNT</td>
                <td style="text-align: right;">{rupees(total_amt)}</td>
            </tr>
        </tbody>
    </table>

    <div style="font-size: 12px; color: #64748b; margin-top: 15px;">
        <b>Note / Payment Terms:</b> Payment is requested on or before the due date ({bill.get('due_date') or '-'}).
    </div>

    <div class="signatory-box">
        <div class="sign-firm">For H P M S &amp; ASSOCIATES</div>
        <div class="sign-title">Chartered Accountants</div>
        <div class="sign-auth">HPMS &amp; ASSOCIATES - AUTHORISED SIGNATORY</div>
    </div>
</div>
</body>
</html>"""


def generate_invoice_text(bill, client):
    """Generate WhatsApp/Email message text with address and Authorised Signatory footer."""
    prof_fees = float(bill.get("professional_fees") or 0)
    gst_amt = float(bill.get("gst_amount") or 0)
    other_chg = float(bill.get("other_charges") or 0)
    total_amt = float(bill.get("total_amount") or 0)

    return (
        f"H P M S & ASSOCIATES\n"
        f"Chartered Accountants\n"
        f"A-27, Commercial Market, Govindpuram, Ghaziabad, UP-201013\n"
        f"Contact: 7290009815, 7290009816\n\n"
        f"TAX INVOICE\n\n"
        f"Dear {client.get('client_name')},\n\n"
        f"Please find below the bill details from H P M S & ASSOCIATES:\n\n"
        f"Invoice No: {bill.get('bill_number')}\n"
        f"Invoice Date: {bill.get('bill_date')}\n"
        f"Service / Task: {bill.get('task_name')}\n\n"
        f"Professional Fees: {rupees(prof_fees)}\n"
        f"GST Amount (18%): {rupees(gst_amt)}\n"
        f"Other Charges: {rupees(other_chg)}\n"
        f"----------------------------------------\n"
        f"Total Bill Amount: {rupees(total_amt)}\n"
        f"Payment Due Date: {bill.get('due_date') or '-'}\n"
        f"----------------------------------------\n\n"
        f"Thank you,\n\n"
        f"H P M S & ASSOCIATES\n"
        f"Chartered Accountants\n"
        f"HPMS & ASSOCIATES - AUTHORISED SIGNATORY"
    )


# --------------------------------------------------------------------------
# ADMIN - BILLING & COLLECTION
# --------------------------------------------------------------------------
def page_billing(user):
    section("Billing & Collection")

    bills = db.get_bills_df()
    tab_track, tab_bill, tab_send, tab_pay, tab_follow = st.tabs([
        "📑 Tracker", "🧾 Create Bill", "📄 Print / Send Invoice", "💰 Add Payment", "📞 Collection Follow-up"])

    # ------------------------- TRACKER -------------------------
    with tab_track:
        not_billed = db.get_completed_not_billed_df()
        k = st.columns(4)
        total_billed = 0 if bills.empty else float(bills["total_amount"].sum())
        total_recv = 0 if bills.empty else float(bills["received"].sum())
        kpi(k[0], "Total Billed", rupees(total_billed))
        kpi(k[1], "Total Received", rupees(total_recv), "green")
        kpi(k[2], "Total Outstanding", rupees(total_billed - total_recv), "red")
        kpi(k[3], "Completed – Not Billed", len(not_billed), "orange")
        st.write("")

        if bills.empty:
            st.info("No bills recorded yet.")
        else:
            b = bills.copy()
            b["due_dt"] = pd.to_datetime(b["due_date"], errors="coerce").dt.date
            b["overdue"] = (b["due_dt"] < date.today()) & (b["outstanding"] > 0)

            c1, c2 = st.columns([2, 3])
            client_f = c1.multiselect("Client", sorted(b["client_name"].unique()))
            view_f = c2.radio("View", ["All", "Unpaid", "Partially Paid", "Paid",
                                       "Overdue Outstanding"], horizontal=True)
            if client_f:
                b = b[b["client_name"].isin(client_f)]
            if view_f == "Overdue Outstanding":
                b = b[b["overdue"]]
            elif view_f != "All":
                b = b[b["payment_status"] == view_f]

            b["flag"] = b.apply(
                lambda r: "🔴" if r["overdue"] else
                ("🟢" if r["payment_status"] == "Paid" else "🟠"), axis=1)

            st.dataframe(b[["flag", "client_name", "bill_number", "bill_date",
                            "total_amount", "received", "outstanding", "due_date",
                            "payment_status"]].rename(columns={
                "flag": " ", "client_name": "Client", "bill_number": "Bill No.",
                "bill_date": "Bill Date", "total_amount": "Bill Amount",
                "received": "Received", "outstanding": "Outstanding",
                "due_date": "Due Date", "payment_status": "Payment Status"}),
                use_container_width=True, hide_index=True)
            st.caption("🔴 Payment overdue   🟠 Amount still outstanding   🟢 Fully paid")

        if not not_billed.empty:
            st.warning("**Completed but Not Billed** – bills yet to be raised:")
            st.dataframe(not_billed[["client_name", "task_name", "employee_name",
                                     "updated_at"]].rename(columns={
                "client_name": "Client", "task_name": "Task",
                "employee_name": "Completed By", "updated_at": "Completed On"}),
                use_container_width=True, hide_index=True)

    # ------------------------- CREATE BILL -------------------------
    with tab_bill:
        clients = db.get_clients_df(only_active=True)
        if clients.empty:
            st.info("Please add a client first.")
        else:
            cmap = {f"{r['client_code']} – {r['client_name']}": r["id"]
                    for _, r in clients.iterrows()}
            client_choice = st.selectbox("Client", list(cmap.keys()),
                                         key="bill_client")
            cid = cmap[client_choice]

            # Tasks of this client that are not yet billed
            ctasks = db.get_tasks_df(user)
            ctasks = ctasks[ctasks["client_id"] == cid] if not ctasks.empty else ctasks
            billed_ids = db.run_query(
                "SELECT task_id FROM bills WHERE task_id IS NOT NULL")["task_id"].tolist()
            tmap = {"(No specific task)": None}
            for r in ctasks.itertuples():
                if r.id not in billed_ids:
                    label = f"#{r.id} · {r.task_name} · {r.status}"
                    tmap[label] = r.id

            task_choice = st.selectbox("Related Task", list(tmap.keys()), key="bill_task")
            c1, c2 = st.columns(2)
            next_bno = f"HPMS/26-27/{db.run_query('SELECT COUNT(*) c FROM bills')['c'][0]+1:03d}"
            bill_no = c1.text_input("Bill Number *", value=next_bno, key="bill_no_input")
            bill_date = c2.date_input("Bill Date", value=date.today(), format="DD/MM/YYYY", key="bill_date_input")

            st.write("")
            c3, c4 = st.columns(2)
            fees = c3.number_input("Professional Fees (₹) *", min_value=0.0, value=0.0, step=500.0, key="bill_fees")
            
            gst_options = ["18% (Standard CA Services)", "12%", "5%", "0% (Exempted)", "Custom Amount"]
            gst_rate_choice = c4.selectbox("GST Rate / Option", gst_options, index=0, key="bill_gst_opt")

            c5, c6 = st.columns(2)
            if gst_rate_choice == "18% (Standard CA Services)":
                calc_gst = round(fees * 0.18, 2)
                gst = c5.number_input("GST Amount (₹) [18% Auto]", min_value=0.0, value=float(calc_gst), step=100.0, key="bill_gst_18")
            elif gst_rate_choice == "12%":
                calc_gst = round(fees * 0.12, 2)
                gst = c5.number_input("GST Amount (₹) [12% Auto]", min_value=0.0, value=float(calc_gst), step=100.0, key="bill_gst_12")
            elif gst_rate_choice == "5%":
                calc_gst = round(fees * 0.05, 2)
                gst = c5.number_input("GST Amount (₹) [5% Auto]", min_value=0.0, value=float(calc_gst), step=100.0, key="bill_gst_5")
            elif gst_rate_choice == "0% (Exempted)":
                gst = c5.number_input("GST Amount (₹) [0%]", min_value=0.0, value=0.0, step=0.0, key="bill_gst_0", disabled=True)
            else:
                gst = c5.number_input("GST Amount (₹) [Custom]", min_value=0.0, value=0.0, step=100.0, key="bill_gst_custom")

            other = c6.number_input("Other Charges (₹)", min_value=0.0, value=0.0, step=100.0, key="bill_other")

            total_bill = round(fees + gst + other, 2)

            st.markdown(
                f"""<div style="background-color:#EBF3FE; border:1px solid #1F6FEB; padding:12px 16px; border-radius:8px; margin: 12px 0;">
                    <span style="font-size:15px; color:#0B1F3A;"><b>Total Bill Amount:</b></span>
                    <span style="font-size:24px; color:#1F6FEB; font-weight:700; margin-left:10px;">{rupees(total_bill)}</span>
                    <br><span style="font-size:13px; color:#5B6B82;">(Professional Fees: {rupees(fees)} + GST: {rupees(gst)} + Other Charges: {rupees(other)})</span>
                </div>""",
                unsafe_allow_html=True
            )

            c7, c8 = st.columns(2)
            due = c7.date_input("Payment Due Date", value=date.today() + timedelta(days=30), format="DD/MM/YYYY", key="bill_due_date")
            remarks = c8.text_input("Billing Remarks", key="bill_remarks")

            if st.button("Save Bill", type="primary", use_container_width=True, key="save_bill_btn"):
                if not bill_no.strip():
                    st.error("Bill number is compulsory.")
                elif total_bill <= 0:
                    st.error("Total bill amount must be greater than zero.")
                elif db.fetch_one("SELECT id FROM bills WHERE bill_number = ?", (bill_no.strip(),)):
                    st.error("This bill number already exists.")
                else:
                    db.add_bill(cid, tmap[task_choice], bill_no,
                                bill_date.isoformat(), fees, gst, other,
                                due.isoformat(), remarks, user["id"])
                    st.success(f"Bill {bill_no} saved. Total Amount: {rupees(total_bill)}.")
                    st.rerun()

    # ------------------------- PRINT / SEND INVOICE -------------------------
    with tab_send:
        if bills.empty:
            st.info("No bills recorded yet.")
        else:
            bmap = {f"{r['bill_number']} · {r['client_name']} · Total {rupees(r['total_amount'])}": r["id"]
                    for _, r in bills.iterrows()}
            
            chosen = st.selectbox("Select Invoice to View / Print / Send", list(bmap.keys()), key="send_invoice_select")
            bid = bmap[chosen]
            bill = bills[bills["id"] == bid].iloc[0].to_dict()

            clients_all = db.get_clients_df()
            client_matches = clients_all[clients_all["id"] == bill["client_id"]]
            client = client_matches.iloc[0].to_dict() if not client_matches.empty else {}

            inv_html = generate_invoice_html(bill, client)
            inv_text = generate_invoice_text(bill, client)

            st.write("")
            c_act1, c_act2, c_act3 = st.columns(3)

            # Download Printable HTML/PDF button
            c_act1.download_button(
                label="📥 Download Invoice (HTML/PDF)",
                data=inv_html,
                file_name=f"Invoice_{str(bill.get('bill_number', 'bill')).replace('/', '_')}.html",
                mime="text/html",
                use_container_width=True
            )

            # WhatsApp Share
            mobile_digits = "".join(filter(str.isdigit, str(client.get("mobile") or "")))
            if len(mobile_digits) == 10:
                mobile_digits = "91" + mobile_digits
            wa_encoded = urllib.parse.quote(inv_text)
            wa_url = f"https://api.whatsapp.com/send?phone={mobile_digits}&text={wa_encoded}" if mobile_digits else f"https://api.whatsapp.com/send?text={wa_encoded}"
            
            c_act2.markdown(
                f'<a href="{wa_url}" target="_blank" style="text-decoration:none;"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:9px 12px; border-radius:6px; font-weight:bold; cursor:pointer;">📲 Send via WhatsApp</button></a>',
                unsafe_allow_html=True
            )

            # Email Share
            email_target = client.get("email") or ""
            subj_encoded = urllib.parse.quote(f"Tax Invoice {bill.get('bill_number')} from H P M S & ASSOCIATES")
            email_url = f"mailto:{email_target}?subject={subj_encoded}&body={wa_encoded}"
            
            c_act3.markdown(
                f'<a href="{email_url}" style="text-decoration:none;"><button style="width:100%; background-color:#0B1F3A; color:white; border:none; padding:9px 12px; border-radius:6px; font-weight:bold; cursor:pointer;">📧 Send via Email</button></a>',
                unsafe_allow_html=True
            )

            st.write("")
            st.markdown("### Invoice Preview (H P M S & ASSOCIATES - AUTHORISED SIGNATORY)")
            components.html(inv_html, height=720, scrolling=True)

    # ------------------------- ADD PAYMENT -------------------------
    with tab_pay:
        if bills.empty:
            st.info("No bills available. Please create a bill first.")
        else:
            bmap = {f"{r['bill_number']} · {r['client_name']} · "
                    f"Outstanding {rupees(r['outstanding'])}": r["id"]
                    for _, r in bills.iterrows()}
            chosen = st.selectbox("Bill Number", list(bmap.keys()))
            bill = bills[bills["id"] == bmap[chosen]].iloc[0]

            k = st.columns(4)
            kpi(k[0], "Bill Amount", rupees(bill["total_amount"]))
            kpi(k[1], "Received", rupees(bill["received"]), "green")
            kpi(k[2], "Outstanding", rupees(bill["outstanding"]), "red")
            kpi(k[3], "Status", bill["payment_status"],
                "green" if bill["payment_status"] == "Paid" else "orange")
            st.write("")

            with st.form("add_payment_form"):
                c1, c2, c3 = st.columns(3)
                pay_date = c1.date_input("Payment Date", value=date.today(),
                                         format="DD/MM/YYYY")
                amount = c2.number_input("Amount Received (₹)", min_value=0.0,
                                         step=1000.0)
                mode = c3.selectbox("Payment Mode", db.PAYMENT_MODES)
                c4, c5 = st.columns(2)
                ref = c4.text_input("Reference Number (optional)")
                rmk = c5.text_input("Remarks")
                if st.form_submit_button("Save Payment", type="primary",
                                         use_container_width=True):
                    if amount <= 0:
                        st.error("Amount received must be greater than zero.")
                    else:
                        db.add_payment(int(bill["id"]), pay_date.isoformat(), amount,
                                       mode, ref, rmk, user["id"])
                        st.success(f"Payment of {rupees(amount)} recorded.")
                        st.rerun()

            section("Payment History of this Bill")
            pays = db.get_payments_df(int(bill["id"]))
            if pays.empty:
                st.info("No payment received against this bill so far.")
            else:
                st.dataframe(pays[["payment_date", "amount_received", "payment_mode",
                                   "reference_number", "remarks"]].rename(columns={
                    "payment_date": "Date", "amount_received": "Amount",
                    "payment_mode": "Mode", "reference_number": "Reference",
                    "remarks": "Remarks"}), use_container_width=True, hide_index=True)

    # ------------------------- FOLLOW-UP -------------------------
    with tab_follow:
        pending = bills[bills["outstanding"] > 0] if not bills.empty else bills
        if pending.empty:
            st.success("There are no unpaid or part-paid bills to follow up.")
        else:
            bmap = {f"{r['bill_number']} · {r['client_name']} · "
                    f"Outstanding {rupees(r['outstanding'])}": r["id"]
                    for _, r in pending.iterrows()}
            chosen = st.selectbox("Select Bill", list(bmap.keys()), key="follow_pick")
            bid = bmap[chosen]

            with st.form("followup_form"):
                c1, c2 = st.columns([1, 3])
                f_date = c1.date_input("Follow-up Date", value=date.today(),
                                       format="DD/MM/YYYY")
                remark = c2.text_input(
                    "Follow-up Remark",
                    placeholder="e.g. Called client – payment expected Monday.")
                if st.form_submit_button("Add Follow-up", type="primary",
                                         use_container_width=True):
                    if not remark.strip():
                        st.error("Please write a remark.")
                    else:
                        db.add_followup(bid, f_date.isoformat(), user["id"], remark)
                        st.success("Follow-up recorded.")
                        st.rerun()

            section("Collection Follow-up History")
            fdf = db.get_followups_df(bid)
            if fdf.empty:
                st.info("No follow-up recorded for this bill yet.")
            else:
                st.dataframe(fdf[["followup_date", "user_name", "remark"]].rename(
                    columns={"followup_date": "Date", "user_name": "By",
                             "remark": "Remark"}),
                    use_container_width=True, hide_index=True)


# --------------------------------------------------------------------------
# ADMIN - ANALYTICS
# --------------------------------------------------------------------------
def page_analytics(user):
    section("Analytics")

    tasks = add_task_flags(db.get_tasks_df(user))
    bills = db.get_bills_df()

    if tasks.empty:
        st.info("No data to analyse yet.")
        return

    c1, c2 = st.columns(2)

    # ---- Task status chart ----
    with c1:
        st.markdown("**Task Status**")
        buckets = {
            "Not Started": int((tasks["status"] == "Not Started").sum()),
            "In Progress": int(tasks["status"].isin(["In Progress", "Under Review"]).sum()),
            "Waiting": int(tasks["status"].isin(
                ["Waiting for Client", "Waiting for Information",
                 "Query Raised", "On Hold"]).sum()),
            "Completed": int((tasks["status"] == "Completed").sum()),
            "Overdue": int(tasks["is_overdue"].sum()),
        }
        sdf = pd.DataFrame({"Status": list(buckets.keys()),
                            "Tasks": list(buckets.values())})
        fig = px.bar(sdf, x="Status", y="Tasks", text="Tasks",
                     color="Status",
                     color_discrete_map={"Not Started": "#98A2B3",
                                         "In Progress": "#1F6FEB",
                                         "Waiting": "#F79009",
                                         "Completed": "#12A150",
                                         "Overdue": "#D92D20"})
        fig.update_layout(showlegend=False, height=380,
                          margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig, use_container_width=True)

    # ---- Employee workload chart ----
    with c2:
        st.markdown("**Employee Workload (pending tasks)**")
        pend = tasks[tasks["status"] != "Completed"]
        if pend.empty:
            st.success("No pending tasks with any employee.")
        else:
            wdf = (pend.groupby("employee_name").size()
                   .reset_index(name="Pending Tasks")
                   .rename(columns={"employee_name": "Employee"})
                   .sort_values("Pending Tasks", ascending=True))
            fig = px.bar(wdf, x="Pending Tasks", y="Employee", orientation="h",
                         text="Pending Tasks")
            fig.update_traces(marker_color="#1F6FEB")
            fig.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)

    # ---- Collection status pie ----
    with c3:
        st.markdown("**Collection Status**")
        if bills.empty:
            st.info("No bills recorded yet.")
        else:
            cdf = (bills.groupby("payment_status").size()
                   .reset_index(name="Bills")
                   .rename(columns={"payment_status": "Status"}))
            fig = px.pie(cdf, names="Status", values="Bills", hole=0.45,
                         color="Status",
                         color_discrete_map={"Paid": "#12A150",
                                             "Partially Paid": "#F79009",
                                             "Unpaid": "#D92D20"})
            fig.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)

    # ---- Client-wise outstanding ----
    with c4:
        st.markdown("**Client-wise Outstanding**")
        if bills.empty or bills["outstanding"].sum() == 0:
            st.success("No outstanding amount.")
        else:
            odf = (bills.groupby("client_name")["outstanding"].sum()
                   .reset_index().rename(columns={"client_name": "Client",
                                                  "outstanding": "Outstanding"}))
            odf = odf[odf["Outstanding"] > 0].sort_values("Outstanding")
            fig = px.bar(odf, x="Outstanding", y="Client", orientation="h",
                         text="Outstanding")
            fig.update_traces(marker_color="#D92D20")
            fig.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------------------------------
# SETTINGS (available to everybody)
# --------------------------------------------------------------------------
def page_settings(user):
    section("Settings")
    left, right = st.columns(2)

    with left:
        st.markdown("**Change Password**")
        with st.form("change_pw"):
            old = st.text_input("Current Password", type="password")
            new1 = st.text_input("New Password", type="password")
            new2 = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("Change Password", use_container_width=True):
                if new1 != new2:
                    st.error("The two new passwords do not match.")
                else:
                    ok, msg = auth.change_password(user["id"], old, new1)
                    (st.success if ok else st.error)(msg)

    if user["is_admin"]:
        with right:
            st.markdown("**Demo Data**")
            st.caption("Loads fictional clients, employees, tasks, bills and "
                       "payments for demonstration. It refuses to run if the "
                       "database already contains clients.")
            if st.button("Load Demo Data", use_container_width=True):
                ok, msg = db.load_demo_data()
                (st.success if ok else st.warning)(msg)


# --------------------------------------------------------------------------
# SIDEBAR + ROUTER
# --------------------------------------------------------------------------
ADMIN_PAGES = {
    "Dashboard": page_dashboard,
    "Task Tracker": page_task_tracker,
    "Delegate Task": page_delegate_task,
    "Client 360°": page_client_360,
    "Clients": page_clients,
    "Team": page_team,
    "Task Master": page_task_master,
    "Billing & Collection": page_billing,
    "Analytics": page_analytics,
    "Settings": page_settings,
}

EMPLOYEE_PAGES = {
    "My Tasks": lambda u: page_my_tasks(u, completed=False),
    "My Completed Tasks": lambda u: page_my_tasks(u, completed=True),
    "Settings": page_settings,
}


def sidebar(user):
    with st.sidebar:
        st.markdown(
            f"""<div style="padding:6px 0 12px 0">
                  <div style="color:#0B1F3A;font-weight:700;letter-spacing:2px">
                    H P M S &amp; ASSOCIATES</div>
                  <div style="color:#5B6B82;font-size:12px">Practice Management</div>
                </div>""", unsafe_allow_html=True)
        st.markdown(f"**{user['name']}**")
        st.caption(f"{'Admin' if user['is_admin'] else user['role']} · {user['email']}")
        st.divider()

        pages = ADMIN_PAGES if user["is_admin"] else EMPLOYEE_PAGES
        names = list(pages.keys())
        current = st.session_state.get("page", names[0])
        if current not in names:
            current = names[0]

        choice = st.radio("Menu", names, index=names.index(current),
                          label_visibility="collapsed")
        st.session_state.page = choice

        st.divider()
        if st.button("Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

        return pages[choice]


def main():
    if "user" not in st.session_state:
        login_screen()
        return

    user = st.session_state.user
    page_function = sidebar(user)
    firm_header()

    # A second safety net: an employee can never reach an admin page,
    # even if the page name is forced into the session.
    if not user["is_admin"] and st.session_state.page in ADMIN_PAGES \
            and st.session_state.page not in EMPLOYEE_PAGES:
        st.error("You are not authorised to view this screen.")
        return

    page_function(user)


main()
