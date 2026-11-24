from datetime import date, timedelta

import pandas as pd
import streamlit as st

from core import auth, db, ui
from core.constants import CATEGORIES, CATEGORY_TONE, PRIORITIES, STATUS_TONE, STATUSES

from . import common

HORIZONS = {"Overdue + next 30 days": 30, "Overdue + next 90 days": 90, "Everything": None}


def allowed_statuses(user, current):
    """Maker-checker: staff can send work for review, only partners/managers can mark it Done."""
    if auth.sees_all_work(user):
        return STATUSES
    return [s for s in STATUSES if s != "Done"] + (["Done"] if current == "Done" else [])


def render():
    u = common.me()
    managers = auth.sees_all_work(u)
    ui.header("Task Board" if managers else "My Work",
              "Drag work forward with ▶ · Under Review means it's waiting for a partner/manager check")
    if not common.clients():
        common.no_clients_yet()
        return

    if st.session_state.get("open_task"):
        task_dialog(st.session_state.pop("open_task"))

    staff = common.users()
    cm = common.clients()
    f1, f2, f3, f4, f5 = st.columns([1.4, 1.2, 1, 1.2, 1.3])
    search = f1.text_input("Search", placeholder="Client or task…", label_visibility="collapsed")
    client = f2.selectbox("Client", [0] + list(cm), format_func=lambda i: "All clients" if i == 0 else cm[i],
                          label_visibility="collapsed")
    cat = f3.selectbox("Area", ["All areas"] + CATEGORIES, label_visibility="collapsed")
    if managers:
        who = f4.selectbox("Person", [0, -1] + list(staff), label_visibility="collapsed",
                           format_func=lambda i: "Everyone" if i == 0 else "Unassigned" if i == -1 else staff[i])
    else:
        who = u["id"]
        f4.markdown(ui.pill("Assigned to me", "teal"), unsafe_allow_html=True)
    horizon = f5.selectbox("Horizon", list(HORIZONS), label_visibility="collapsed")

    a, b, _ = st.columns([1.1, 1.3, 4])
    view = a.segmented_control("View", ["Board", "List"], default="Board", label_visibility="collapsed") or "Board"
    if b.button("New task", icon=":material/add:", type="primary"):
        new_task_dialog()

    filters = dict(search=search.strip(), client=client, cat=cat, who=who, days=HORIZONS[horizon])
    if view == "Board":
        board(filters)
    else:
        list_view(filters)


def load_tasks(f) -> list[dict]:
    sql = ("SELECT t.*, c.name AS client, us.name AS assignee FROM tasks t JOIN clients c ON c.id=t.client_id "
           "LEFT JOIN users us ON us.id=t.assigned_to WHERE c.active=1")
    p = {}
    if f["client"]:
        sql += " AND t.client_id=:c"; p["c"] = f["client"]
    if f["cat"] != "All areas":
        sql += " AND t.category=:cat"; p["cat"] = f["cat"]
    if f["who"] == -1:
        sql += " AND t.assigned_to IS NULL"
    elif f["who"]:
        sql += " AND t.assigned_to=:w"; p["w"] = f["who"]
    if f["days"]:
        sql += " AND t.due_date<=:h"; p["h"] = (common.today() + timedelta(days=f["days"])).isoformat()
    sql += " ORDER BY t.due_date, c.name"
    rows = db.query(sql, **p)
    if f["search"]:
        s = f["search"].lower()
        rows = [r for r in rows if s in r["client"].lower() or s in r["title"].lower() or s in (r["period"] or "").lower()]
    return rows


@st.fragment(run_every=common.REFRESH)
def board(f):
    u = common.me()
    today = common.today()
    rows = load_tasks(f)
    st.markdown(f'<div style="text-align:right;margin:-2.6rem 0 0.6rem 0">{ui.live()}</div>', unsafe_allow_html=True)
    cols = st.columns(4, gap="small")
    for col, status in zip(cols, STATUSES):
        items = [t for t in rows if t["status"] == status]
        if status == "Done":
            items = sorted(items, key=lambda t: t["completed_on"] or "", reverse=True)[:12]
        bg, fg = ui.TONES[STATUS_TONE[status]]
        with col:
            st.markdown(f'<div class="pm-col-head"><span>{status}</span>'
                        f'<span class="pm-pill" style="background:{bg};color:{fg}">{len(items)}</span></div>',
                        unsafe_allow_html=True)
            for t in items[:30]:
                kanban_card(t, u, today)
            if len(items) > 30:
                st.caption(f"+ {len(items) - 30} more · narrow the filters or use List view")
            if not items:
                st.markdown(ui.empty("Nothing here"), unsafe_allow_html=True)


def kanban_card(t, u, today):
    due = date.fromisoformat(t["due_date"])
    tone, label = ui.due_tone(due, t["status"], today)
    border = "green" if t["status"] == "Done" else tone if tone in ("red", "amber") else "plain"
    with st.container(border=True, key=f"card-{border}-{t['id']}"):
        period = t["period"] if t["rule_code"] else ""
        st.markdown(
            f'<div class="pm-k-client">{ui.esc(t["client"])}</div>'
            f'<div class="pm-k-title">{ui.esc(t["title"])}{" · " + ui.esc(period) if period else ""}</div>'
            f'<div class="pm-k-meta">{ui.pill(label, tone)}{ui.pill(t["category"], CATEGORY_TONE.get(t["category"]))}'
            f'{ui.pill("High", "rose") if t["priority"] == "High" and t["status"] != "Done" else ""}'
            f'<span style="margin-left:auto">{ui.avatar(t["assignee"] or "?", 24)}</span></div>',
            unsafe_allow_html=True)
        i = STATUSES.index(t["status"])
        allowed = allowed_statuses(u, t["status"])
        b1, b2, b3 = st.columns(3)
        if i > 0 and STATUSES[i - 1] in allowed and b1.button("◀", key=f"l{t['id']}", help=f"Back to {STATUSES[i - 1]}"):
            common.set_status(t, STATUSES[i - 1])
            st.rerun(scope="fragment")
        if i < 3 and STATUSES[i + 1] in allowed and b2.button("▶", key=f"r{t['id']}", help=f"Move to {STATUSES[i + 1]}"):
            common.set_status(t, STATUSES[i + 1])
            st.rerun(scope="fragment")
        if b3.button("⋯", key=f"o{t['id']}", help="Details, notes & history"):
            st.session_state.open_task = t["id"]
            st.rerun()


def list_view(f):
    u = common.me()
    rows = load_tasks(f)
    if not rows:
        st.markdown(ui.empty("No tasks match these filters"), unsafe_allow_html=True)
        return
    today = common.today()
    df = pd.DataFrame(rows)
    df["due"] = pd.to_datetime(df["due_date"]).dt.date
    df["days_left"] = df["due"].map(lambda d: (d - today).days)
    df["assignee"] = df["assignee"].fillna("Unassigned")
    show = df[["id", "client", "title", "period", "category", "due", "days_left", "status", "priority", "assignee"]]
    ev = st.dataframe(
        show, hide_index=True, width="stretch", height=480, on_select="rerun", selection_mode="multi-row",
        column_config={"id": None, "client": "Client", "title": "Task", "period": "Period", "category": "Area",
                       "due": st.column_config.DateColumn("Due", format="DD MMM YYYY"),
                       "days_left": st.column_config.NumberColumn("Days left", help="Negative = overdue"),
                       "status": "Status", "priority": "Priority", "assignee": "Assigned to"})
    picked = [rows[i] for i in ev.selection.rows]
    if not picked:
        st.caption("Tip: tick rows to update several tasks at once.")
        return
    st.markdown(f"**{len(picked)} task(s) selected**")
    c1, c2, c3, c4 = st.columns([1.2, 1.2, 1, 1])
    new_status = c1.selectbox("Set status", ["—"] + allowed_statuses(u, ""))
    staff = common.users()
    new_who = c2.selectbox("Assign to", ["—"] + list(staff), format_func=lambda i: i if i == "—" else staff[i],
                           disabled=not auth.sees_all_work(u))
    c3.write("")
    if c3.button("Apply", type="primary", width="stretch"):
        for t in picked:
            if new_status != "—":
                common.set_status(t, new_status)
            if new_who != "—":
                common.reassign(t, new_who)
        st.toast(f"Updated {len(picked)} task(s)")
        st.rerun()
    if len(picked) == 1:
        c4.write("")
        if c4.button("Open details", width="stretch"):
            st.session_state.open_task = picked[0]["id"]
            st.rerun()


@st.dialog("New task", width="large")
def new_task_dialog():
    u = common.me()
    cm = common.clients()
    staff = common.users()
    with st.form("new_task"):
        client = st.selectbox("Client", list(cm), format_func=lambda i: cm[i])
        title = st.text_input("Task", placeholder="e.g. Reply to GST notice ASMT-10")
        a, b, c = st.columns(3)
        cat = a.selectbox("Area", CATEGORIES)
        due = b.date_input("Due date", common.today() + timedelta(days=7), format="DD/MM/YYYY")
        prio = c.selectbox("Priority", PRIORITIES, index=1)
        if auth.sees_all_work(u):
            who = st.selectbox("Assign to", [None] + list(staff), format_func=lambda i: staff.get(i, "Unassigned"))
        else:
            who = u["id"]
        notes = st.text_area("Notes", height=80)
        if st.form_submit_button("Create task", type="primary"):
            if not title.strip():
                st.error("Please enter the task.")
                return
            tid = db.insert("INSERT INTO tasks(client_id,title,category,period,due_date,priority,assigned_to,notes,"
                            "updated_on) VALUES (:c,:t,:cat,:p,:d,:pr,:w,:n,:u) RETURNING id",
                            c=client, t=title.strip(), cat=cat, p=due.strftime("%b-%Y"), d=due.isoformat(),
                            pr=prio, w=who, n=notes, u=db.now())
            db.log(tid, u["id"], "Created", title.strip())
            st.rerun()


@st.dialog("Task details", width="large")
def task_dialog(task_id: int):
    u = common.me()
    t = db.one("SELECT t.*, c.name AS client FROM tasks t JOIN clients c ON c.id=t.client_id WHERE t.id=:i", i=task_id)
    if not t:
        st.warning("This task no longer exists.")
        return
    managers = auth.sees_all_work(u)
    st.markdown(f"#### {t['client']}")
    st.markdown(f"{ui.pill(t['category'], CATEGORY_TONE.get(t['category']))} {ui.pill(t['status'], STATUS_TONE[t['status']])} "
                f"&nbsp;**{ui.esc(t['title'])}** · {ui.esc(t['period'] or '')}", unsafe_allow_html=True)
    staff = common.users()
    with st.form(f"edit_{task_id}"):
        a, b = st.columns(2)
        statuses = allowed_statuses(u, t["status"])
        status = a.selectbox("Status", statuses, index=statuses.index(t["status"]))
        ids = [None] + list(staff)
        who = b.selectbox("Assigned to", ids, index=ids.index(t["assigned_to"]) if t["assigned_to"] in ids else 0,
                          format_func=lambda i: staff.get(i, "Unassigned"), disabled=not managers)
        c, d = st.columns(2)
        due = c.date_input("Due date", date.fromisoformat(t["due_date"]), disabled=not managers, format="DD/MM/YYYY")
        prio = d.selectbox("Priority", PRIORITIES, index=PRIORITIES.index(t["priority"] or "Medium"))
        notes = st.text_area("Notes / working papers reference", t["notes"] or "", height=100)
        if st.form_submit_button("Save changes", type="primary"):
            common.set_status(t, status)
            if managers:
                common.reassign(t, who)
                if due.isoformat() != t["due_date"]:
                    db.execute("UPDATE tasks SET due_date=:d WHERE id=:i", d=due.isoformat(), i=task_id)
                    db.log(task_id, u["id"], "Due date changed", f"{t['due_date']} → {due.isoformat()}")
            if notes != (t["notes"] or "") or prio != t["priority"]:
                db.execute("UPDATE tasks SET notes=:n, priority=:p, updated_on=:u WHERE id=:i",
                           n=notes, p=prio, u=db.now(), i=task_id)
                if notes != (t["notes"] or ""):
                    db.log(task_id, u["id"], "Note", notes[:120])
            st.rerun()
    hist = db.query("SELECT l.at, l.action, l.detail, us.name AS who FROM task_log l LEFT JOIN users us "
                    "ON us.id=l.user_id WHERE l.task_id=:i ORDER BY l.at DESC LIMIT 15", i=task_id)
    st.markdown("**History**")
    if hist:
        st.markdown("".join(f'<div class="pm-row">{ui.avatar(h["who"] or "System", 26)}<div class="main">'
                            f'<div class="t1">{ui.esc(h["action"])}: <span style="font-weight:500">{ui.esc(h["detail"])}'
                            f'</span></div><div class="t2">{ui.esc(h["who"] or "System")} · {h["at"]}</div></div></div>'
                            for h in hist), unsafe_allow_html=True)
    else:
        st.caption("No changes recorded yet.")
    if managers and not t["rule_code"]:
        if st.button("Delete this task", icon=":material/delete:"):
            db.execute("DELETE FROM tasks WHERE id=:i", i=task_id)
            st.rerun()
