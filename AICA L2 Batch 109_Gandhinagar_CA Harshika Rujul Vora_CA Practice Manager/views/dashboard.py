from collections import defaultdict
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from core import auth, clock, db, duedates, ui
from core.constants import CATEGORY_TONE, STATUSES

from . import common


def render():
    u = common.me()
    hour = clock.now().hour
    greet = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
    first = next((w for w in u['name'].split() if w.rstrip('.').upper() not in ('CA', 'CS', 'DR', 'MR', 'MS', 'MRS', 'CMA')), u['name'])
    ui.header(f"{greet}, {first}",
              f"{clock.today().strftime('%A, %d %B %Y')} · FY {duedates.fy_label(duedates.current_fy_start())}")
    live_panel()


@st.fragment(run_every=common.REFRESH)
def live_panel():
    u = common.me()
    today = common.today()
    t0 = today.isoformat()
    scope, params = common.scope_sql()
    all_view = auth.sees_all_work(u)

    rows = db.query(
        "SELECT t.id, t.title, t.category, t.period, t.due_date, t.status, t.rule_code, t.completed_on, "
        "t.assigned_to, c.name AS client, us.name AS assignee FROM tasks t "
        "JOIN clients c ON c.id=t.client_id LEFT JOIN users us ON us.id=t.assigned_to "
        "WHERE c.active=1 AND (t.status <> 'Done' OR t.completed_on >= :m0)" + scope,
        m0=today.replace(day=1).isoformat(), **params)
    open_t = [r for r in rows if r["status"] != "Done"]
    overdue = [r for r in open_t if r["due_date"] < t0]
    week = [r for r in open_t if t0 <= r["due_date"] <= (today + timedelta(days=7)).isoformat()]
    done_month = [r for r in rows if r["status"] == "Done"]
    review = [r for r in open_t if r["status"] == "Under Review"]

    st.markdown(f'<div style="text-align:right;margin-top:-3.2rem;margin-bottom:1rem">{ui.live()}</div>',
                unsafe_allow_html=True)
    cards = []
    if all_view:
        n_clients = db.scalar("SELECT COUNT(*) FROM clients WHERE active=1")
        cards.append(ui.kpi_html("Active clients", n_clients, "on the books", ui.NAVY, "👥"))
    cards += [
        ui.kpi_html("Open tasks", len(open_t), f"{len(review)} awaiting review", ui.TEAL, "📋"),
        ui.kpi_html("Overdue", len(overdue), "need attention now" if overdue else "all on time",
                    "#DC2626" if overdue else "#16A34A", "⏰"),
        ui.kpi_html("Due in 7 days", len(week), "this week's filings", "#F59E0B", "📅"),
        ui.kpi_html("Done this month", len(done_month), today.strftime("%B"), "#16A34A", "✅"),
    ]
    if all_view:
        due_fees = db.scalar("SELECT COALESCE(SUM(total),0) FROM invoices WHERE status='Unpaid'") or 0
        cards.append(ui.kpi_html("Fees outstanding", ui.inr(due_fees, short=True), "unpaid invoices", "#6366F1", "💰"))
    ui.kpis(cards)

    left, right = st.columns([1.05, 1], gap="medium")
    with left:
        upcoming_deadlines(open_t, rows, today)
    with right:
        overdue_list(overdue, today)

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        with st.container(border=True):
            st.markdown("**Open work by compliance area**")
            if open_t:
                df = pd.DataFrame(open_t)
                df["when"] = df["due_date"].apply(lambda d: "Overdue" if d < t0 else "Upcoming")
                g = df.groupby(["category", "when"]).size().reset_index(name="tasks")
                fig = px.bar(g, y="category", x="tasks", color="when", orientation="h",
                             color_discrete_map={"Overdue": "#DC2626", "Upcoming": "#0B1F3A"})
                st.plotly_chart(ui.style_fig(fig, 260), width="stretch", config={"displayModeBar": False})
            else:
                st.markdown(ui.empty("No open work"), unsafe_allow_html=True)
    with c2:
        with st.container(border=True):
            if all_view:
                st.markdown("**Team workload (open tasks by status)**")
                df = pd.DataFrame(open_t)
                if not df.empty:
                    df["assignee"] = df["assignee"].fillna("Unassigned")
                    g = df.groupby(["assignee", "status"]).size().reset_index(name="tasks")
                    fig = px.bar(g, x="assignee", y="tasks", color="status", category_orders={"status": STATUSES},
                                 color_discrete_map={"To Do": "#94A3B8", "In Progress": "#3B82F6",
                                                     "Under Review": "#F59E0B", "Done": "#16A34A"})
                    st.plotly_chart(ui.style_fig(fig, 260), width="stretch", config={"displayModeBar": False})
            else:
                st.markdown("**My work by status**")
                df = pd.DataFrame(rows)
                if not df.empty:
                    g = df.groupby("status").size().reindex(STATUSES, fill_value=0).reset_index(name="tasks")
                    fig = px.pie(g, names="status", values="tasks", hole=0.6, color="status",
                                 color_discrete_map={"To Do": "#94A3B8", "In Progress": "#3B82F6",
                                                     "Under Review": "#F59E0B", "Done": "#16A34A"})
                    st.plotly_chart(ui.style_fig(fig, 260), width="stretch", config={"displayModeBar": False})

    if all_view:
        activity_feed(8)


def upcoming_deadlines(open_t, rows, today):
    horizon = (today + timedelta(days=14)).isoformat()
    groups = defaultdict(lambda: {"open": 0, "clients": set(), "cat": ""})
    for r in rows:
        if r["rule_code"] and today.isoformat() <= r["due_date"] <= horizon:
            g = groups[(r["due_date"], r["title"], r["period"])]
            g["cat"] = r["category"]
            g["clients"].add(r["client"])
            if r["status"] != "Done":
                g["open"] += 1
    body = ""
    for (due, title, period), g in sorted(groups.items())[:7]:
        total = len(g["clients"])
        done = total - g["open"]
        pct = 100 * done / total if total else 0
        d = date.fromisoformat(due)
        tone, label = ui.due_tone(d, "Done" if g["open"] == 0 else "To Do", today)
        body += (f'<div class="pm-row">{ui.date_chip(d)}<div class="main"><div class="t1">{ui.esc(title)}</div>'
                 f'<div class="t2">{ui.esc(period)} · {done}/{total} clients done</div>'
                 f'{ui.bar(pct, "#16A34A" if pct == 100 else ui.TEAL)}</div>'
                 f'{ui.pill(g["cat"], CATEGORY_TONE.get(g["cat"], "slate"))}{ui.pill(label, tone)}</div>')
    ui.card("Upcoming statutory deadlines · next 14 days", body or ui.empty("No statutory deadlines in the next 14 days"))


def overdue_list(overdue, today):
    body = ""
    for r in sorted(overdue, key=lambda x: x["due_date"])[:7]:
        d = date.fromisoformat(r["due_date"])
        body += (f'<div class="pm-row">{ui.avatar(r["assignee"] or "?", 30)}<div class="main">'
                 f'<div class="t1">{ui.esc(r["client"])}</div><div class="t2">{ui.esc(r["title"])} · '
                 f'{ui.esc(r["period"] or "")}</div></div>{ui.pill(ui.due_tone(d, r["status"], today)[1], "red")}</div>')
    more = f'<div class="t2" style="padding-top:8px;color:#64748B">+ {len(overdue) - 7} more on the Task Board</div>' \
        if len(overdue) > 7 else ""
    ui.card("Overdue work", (body + more) or ui.empty("Nothing overdue. Great work! 🎉"),
            ui.pill(f"{len(overdue)} overdue", "red" if overdue else "green"))


def activity_feed(limit=8):
    log = db.query(
        "SELECT l.at, l.action, l.detail, u.name AS who, t.title, t.period, c.name AS client FROM task_log l "
        "LEFT JOIN users u ON u.id=l.user_id LEFT JOIN tasks t ON t.id=l.task_id "
        "LEFT JOIN clients c ON c.id=t.client_id ORDER BY l.at DESC LIMIT :n", n=limit)
    body = ""
    for e in log:
        detail = e["detail"] or ""
        tone = "green" if detail.endswith("Done") else "amber" if "Review" in detail else "blue"
        body += (f'<div class="pm-row">{ui.avatar(e["who"] or "System", 30)}<div class="main"><div class="t1">'
                 f'{ui.esc(e["who"] or "System")} · <span style="font-weight:500">{ui.esc(e["client"] or "")} — '
                 f'{ui.esc(e["title"] or "")} {ui.esc(e["period"] or "")}</span></div>'
                 f'<div class="t2">{ui.esc(e["action"])}: {ui.esc(detail)}</div></div>'
                 f'{ui.pill(ui.ago(e["at"]), tone)}</div>')
    ui.card("Recent team activity", body or ui.empty("No activity yet"))
